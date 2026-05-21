"""L1: Atomic fact extraction - uses user's LLM via ModelRegistry."""
from __future__ import annotations
import json
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo
from backend.pipeline.llm_client import call_llm

_repo: MemoryRepo | None = None
PROMPT = (Path(__file__).parent / "prompts" / "l1_extract.txt").read_text(encoding="utf-8")

def init(repo: MemoryRepo): global _repo; _repo = repo

async def extract_from_conversation(conv_id: str, team_id: str) -> tuple[list[dict], int]:
    if _repo is None: return [], 0
    try:
        c_id = int(conv_id)
    except ValueError:
        return [], 0
    row = await _repo.pool.fetchrow(
        "SELECT messages FROM pipeline_conversations WHERE id=$1 AND team_id=$2", c_id, team_id)
    if not row: return [], 0
    msgs = json.loads(row["messages"]) if isinstance(row["messages"], str) else row["messages"]
    text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs[-10:])

    prompt = PROMPT + "\n\n" + text
    result, tokens = await call_llm(prompt, team_id, "classifier")
    if not result: return [], 0

    # Try parsing as JSON array
    try:
        clean_res = result.strip()
        if clean_res.startswith("```json"):
            clean_res = clean_res[7:]
        if clean_res.endswith("```"):
            clean_res = clean_res[:-3]
        clean_res = clean_res.strip()

        data = json.loads(clean_res)
        if isinstance(data, list):
            return data, tokens
    except Exception:
        pass

    # Fallback to bullet points if JSON parsing fails
    facts = []
    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            content = line.strip("- ").strip()
            if len(content) > 5:
                facts.append({
                    "title": content[:50],
                    "content": content,
                    "tags": ["general"],
                    "importance": "normal"
                })
    return facts, tokens


async def store_facts(team_id: str, facts: list[dict], session_id: str = "") -> list[str]:
    if _repo is None: return []
    import uuid
    ids = []
    
    importance_map = {
        "low": 0.2,
        "normal": 0.5,
        "high": 0.8,
        "critical": 1.0
    }
    
    for fact in facts:
        mid = str(uuid.uuid4())
        title = fact.get("title", "")
        content = fact.get("content", "")
        if not title and not content:
            continue
        if not title:
            title = content[:50]
        if not content:
            content = title
            
        tags = fact.get("tags", ["general"])
        imp_str = str(fact.get("importance", "normal")).lower()
        importance = importance_map.get(imp_str, 0.5)
        
        try:
            await _repo.pool.execute(
                """INSERT INTO memories (id, team_id, title, content, source_type, layer, source_session_id, importance, confidence, tags)
                   VALUES ($1, $2, $3, $4, 'agent', 'L1', $5, $6, $7, $8)""",
                mid, team_id, title, content, session_id, importance, 0.9, tags
            )
            ids.append(mid)
        except Exception as e:
            import logging
            logging.getLogger("pipeline").error(f"Failed to store L1 fact manually: {e}", exc_info=True)
            
    return ids
