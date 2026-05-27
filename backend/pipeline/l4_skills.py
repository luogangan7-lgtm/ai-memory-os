"""L4: Procedural memory crystallization — auto-extract reusable skills."""
from __future__ import annotations
import json, httpx
from backend.memory.pg_repo import MemoryRepo

L4_PROMPT = """You are a skill extraction assistant. Based on recurring patterns in the user's memories, extract a reusable skill.

Output ONLY JSON:
{"skill_name": "Clear, actionable skill name (max 15 chars)", "skill_content": "Markdown description: what, when, how (100-200 chars)", "trigger_pattern": "When to use this skill (30 chars)"}"""

async def crystallize_skills(repo: MemoryRepo, team_id: str) -> int:
    """Scan L1 atoms for patterns, crystallize into L4 skills."""
    provider = await repo.get_active_user_provider_config(team_id)
    if not provider: return 0
    
    async with repo.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT COALESCE(NULLIF(category,''), title) as norm_title, COUNT(*) as freq,
                   array_agg(id ORDER BY created_at) as atom_ids,
                   array_agg(content ORDER BY created_at) as contents
            FROM memories WHERE team_id=$1 AND layer='L1'
            AND created_at > NOW() - INTERVAL '60 days'
            GROUP BY COALESCE(NULLIF(category,''), title) HAVING COUNT(*) >= 2
        """, team_id)
    
    new_skills = 0
    for row in rows[:5]:
        sample = "\n---\n".join(c[:300] for c in row['contents'][:5])
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{provider['api_base_url'].rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {provider['api_key']}"},
                    json={"model": provider["model_name"], "messages": [
                        {"role": "system", "content": L4_PROMPT},
                        {"role": "user", "content": f"Recurring pattern '{row['norm_title']}' ({row['freq']} times):\n{sample}"}
                    ], "max_tokens": 500, "temperature": 0.3})
            if resp.status_code != 200: continue
            skill = json.loads(resp.json()["choices"][0]["message"]["content"].strip().lstrip("```json").rstrip("```"))
            
            async with repo.pool.acquire() as conn2:
                await conn2.execute("""
                INSERT INTO memory_skills (team_id, skill_name, skill_content, trigger_pattern, source_atom_ids)
                VALUES ($1,$2,$3,$4,$5)""",
                    team_id, skill.get("skill_name", row['norm_title']),
                    skill.get("skill_content", ""), skill.get("trigger_pattern", ""),
                    [str(a) for a in row['atom_ids'][:10]])
            
                import uuid
                await conn2.execute("""
                INSERT INTO memories (id, team_id, title, content, source_type, layer, category, importance)
                VALUES ($1,$2,$3,$4,'agent','L4','skill',0.9)""",
                str(uuid.uuid4()), team_id,
                    f"[L4 Skill] {skill.get('skill_name','')}",
                    skill.get("skill_content", ""))
                
                new_skills += 1
        except Exception as e:
            print(f"[L4] crystallize failed: {e}")
    
    if new_skills:
        print(f"[L4] Crystallized {new_skills} skills for {team_id}")
    return new_skills
