"""Skill Evolver: Manage skill effectiveness updates, similar skill merges, and content auto-classification."""
from __future__ import annotations
import json
import uuid
import httpx
import structlog
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = structlog.get_logger()

# Predefined categories for auto_classify
CATEGORIES = {
    "开发/代码": ["code", "coding", "python", "typescript", "javascript", "rust", "c++", "java", "golang", "function", "class", "import", "package", "代码", "开发", "编写", "逻辑", "实现"],
    "架构/设计": ["architecture", "design", "structure", "neo4j", "postgres", "redis", "database", "schema", "flow", "pattern", "架构", "设计", "数据流", "模块", "选型", "定义"],
    "诊断/修复": ["fix", "bug", "error", "exception", "crash", "diagnose", "troubleshoot", "traceback", "mypy", "lint", "修复", "诊断", "报错", "异常", "问题", "排查"],
    "部署/运维": ["deploy", "docker", "gcp", "aws", "nginx", "k8s", "ci/cd", "webhook", "cron", "monitor", "运维", "部署", "重启", "配置", "上线", "备份"],
    "测试/验证": ["test", "pytest", "playwright", "e2e", "coverage", "benchmark", "perf", "测试", "验证", "跑测", "覆盖率", "基准"]
}

def auto_classify(title: str, content: str) -> str:
    """Classify memory layer based on title and content keywords."""
    text = f"{title} {content}".lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in text for kw in keywords):
            return cat
    return "其他"

async def update_skill_effectiveness(
    pool: Any,
    skill_id: str,
    outcome: str,
    agent_id: str,
    team_id: str,
    memory_ids: Optional[List[str]] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Record skill execution feedback and adjust effectiveness score in database."""
    if outcome not in ("success", "failure", "partial"):
        raise ValueError("Invalid outcome value")
    
    m_ids = memory_ids or []
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Insert feedback record
            feedback_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO skill_feedback (id, team_id, skill_id, memory_ids, outcome, agent_id, context, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """, feedback_id, team_id, skill_id, m_ids, outcome, agent_id, context)
            
            # 2. Get current skill stats
            row = await conn.fetchrow("""
                SELECT usage_count, fail_count, source_agents, verified_by, effectiveness
                FROM memory_skills
                WHERE id = $1 AND team_id = $2
            """, skill_id, team_id)
            
            if not row:
                raise ValueError("Skill not found or team mismatch")
                
            curr_usage = row["usage_count"] or 0
            curr_fail = row["fail_count"] or 0
            source_agents = row["source_agents"] or []
            verified_by = row["verified_by"] or []
            
            # Update metrics
            new_usage = curr_usage + 1
            new_fail = curr_fail + (1 if outcome == "failure" else 0)
            
            # Recalculate effectiveness (success or partial counts positively, failure negatively)
            # effectiveness = (new_usage - new_fail) / new_usage
            new_effectiveness = max(0.0, min(1.0, float(new_usage - new_fail) / float(new_usage)))
            
            # Update agent listings
            if agent_id and agent_id != "unknown":
                if agent_id not in source_agents:
                    source_agents.append(agent_id)
                if outcome == "success" and agent_id not in verified_by:
                    verified_by.append(agent_id)
            
            await conn.execute("""
                UPDATE memory_skills
                SET usage_count = $1,
                    fail_count = $2,
                    effectiveness = $3,
                    source_agents = $4,
                    verified_by = $5,
                    last_used_at = NOW(),
                    updated_at = NOW()
                WHERE id = $6 AND team_id = $7
            """, new_usage, new_fail, new_effectiveness, source_agents, verified_by, skill_id, team_id)
            
            return {
                "feedback_id": feedback_id,
                "usage_count": new_usage,
                "fail_count": new_fail,
                "effectiveness": new_effectiveness
            }

async def evolve_similar_skills(pool: Any, team_id: str, repo: Any) -> int:
    """Find similar skills for a team, cluster/merge redundant ones using LLM."""
    # 1. Retrieve active model config
    provider = await repo.get_active_user_provider_config(team_id)
    if not provider:
        logger.warning("No active LLM provider configured for team", team_id=team_id)
        return 0
        
    async with pool.acquire() as conn:
        skills = await conn.fetch("""
            SELECT id, skill_name, skill_content, trigger_pattern, source_atom_ids,
                   usage_count, fail_count, source_agents, verified_by, evolved_count
            FROM memory_skills
            WHERE team_id = $1
        """, team_id)
        
        if len(skills) < 2:
            return 0
            
        # Serialize existing skills for LLM analysis
        skills_list = []
        for s in skills:
            skills_list.append({
                "id": str(s["id"]),
                "skill_name": s["skill_name"],
                "skill_content": s["skill_content"],
                "trigger_pattern": s["trigger_pattern"] or ""
            })
            
        prompt = """You are a Skill Evolution Engine. Compare the following list of skills and identify clusters of skills that are redundant or highly similar.
For each cluster, propose a merged skill definition (clear name, consolidated markdown description, unified trigger pattern).

List of skills:
""" + json.dumps(skills_list, indent=2, ensure_ascii=False) + """

Output ONLY JSON in the following schema:
{
  "merges": [
    {
      "source_ids": ["uuid-1", "uuid-2"],
      "merged_skill": {
        "skill_name": "Merged Name (max 15 chars)",
        "skill_content": "Consolidated markdown description (100-200 chars)",
        "trigger_pattern": "Unified trigger pattern (max 50 chars)"
      }
    }
  ]
}
If no redundant skills are found, output {"merges": []}.
Do not include any wrapper tags, conversational text or markdown code blocks."""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{provider['api_base_url'].rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {provider['api_key']}"},
                    json={
                        "model": provider["model_name"],
                        "messages": [
                            {"role": "system", "content": "You are a precise JSON response generator."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.2
                    }
                )
                
            if resp.status_code != 200:
                logger.error("LLM call failed for skill evolution", status_code=resp.status_code, body=resp.text)
                return 0
                
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Handle possible markdown wrapping
            if content.startswith("```"):
                content = content.lstrip("```json").lstrip("```").rstrip("```").strip()
            
            result = json.loads(content)
            merges = result.get("merges", [])
            if not merges:
                return 0
                
            merged_count = 0
            for merge in merges:
                source_ids = merge.get("source_ids", [])
                merged_info = merge.get("merged_skill", {})
                if len(source_ids) < 2 or not merged_info.get("skill_name"):
                    continue
                    
                # Fetch matching skill rows to consolidate metrics
                matched_rows = [s for s in skills if str(s["id"]) in source_ids]
                if len(matched_rows) < 2:
                    continue
                    
                # Compute consolidated metrics
                tot_usage = sum(s["usage_count"] or 0 for s in matched_rows)
                tot_fail = sum(s["fail_count"] or 0 for s in matched_rows)
                eff = max(0.0, min(1.0, float(tot_usage - tot_fail) / float(tot_usage))) if tot_usage > 0 else 1.0
                
                # Merge lists
                atoms = []
                for s in matched_rows:
                    atoms.extend([str(x) for x in (s["source_atom_ids"] or [])])
                atoms = list(set(atoms))
                
                agents: list[str] = []
                for s in matched_rows:
                    agents.extend(s["source_agents"] or [])
                agents = list(set(agents))
                
                verified: list[str] = []
                for s in matched_rows:
                    verified.extend(s["verified_by"] or [])
                verified = list(set(verified))

                
                max_evolved = max(s["evolved_count"] or 0 for s in matched_rows)
                
                # We will keep the first skill ID, overwrite it, and delete the rest
                primary_id = uuid.UUID(source_ids[0])
                other_ids = [uuid.UUID(sid) for sid in source_ids[1:]]
                
                async with conn.transaction():
                    # 1. Update primary skill
                    await conn.execute("""
                        UPDATE memory_skills
                        SET skill_name = $1,
                            skill_content = $2,
                            trigger_pattern = $3,
                            source_atom_ids = $4,
                            usage_count = $5,
                            fail_count = $6,
                            effectiveness = $7,
                            source_agents = $8,
                            verified_by = $9,
                            evolved_count = $10,
                            updated_at = NOW()
                        WHERE id = $11 AND team_id = $12
                    """, merged_info["skill_name"], merged_info["skill_content"], merged_info["trigger_pattern"],
                        atoms, tot_usage, tot_fail, eff, agents, verified, max_evolved + 1, primary_id, team_id)
                    
                    # 2. Update foreign key references in skill_feedback
                    await conn.execute("""
                        UPDATE skill_feedback
                        SET skill_id = $1
                        WHERE skill_id = ANY($2) AND team_id = $3
                    """, primary_id, other_ids, team_id)
                    
                    # 3. Delete secondary skills
                    await conn.execute("""
                        DELETE FROM memory_skills
                        WHERE id = ANY($1) AND team_id = $2
                    """, other_ids, team_id)
                    
                    merged_count += len(other_ids)
            
            return merged_count
            
        except Exception as e:
            logger.error("Skill evolution transaction failed", error=str(e))
            return 0
