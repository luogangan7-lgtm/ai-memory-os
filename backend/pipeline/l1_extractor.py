"""L1: Atomic fact extraction - uses LLM to extract structured facts from conversations."""
from __future__ import annotations
import json, httpx, os
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo

_repo: MemoryRepo | None = None
PROMPT = (Path(__file__).parent / "prompts" / "l1_extract.txt").read_text(encoding="utf-8")

def init(repo: MemoryRepo):
    global _repo
    _repo = repo

async def extract_from_conversation(conv_id: str, team_id: str) -> list[str]:
    if _repo is None: return []
    row = await _repo.pool.fetchrow(
        "SELECT messages FROM pipeline_conversations WHERE id=$1 AND team_id=$2", conv_id, team_id)
    if not row: return []
    msgs = json.loads(row["messages"]) if isinstance(row["messages"], str) else row["messages"]
    text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs[-10:])
    
    prompt = PROMPT + "\n\n" + text
    
    api_key = os.getenv("PIPELINE_LLM_KEY", "")
    api_base = os.getenv("PIPELINE_LLM_BASE", "https://api.deepseek.com/v1")
    model = os.getenv("PIPELINE_LLM_MODEL", "deepseek-v4-flash")
    
    if not api_key:
        return [line.strip("- ") for line in text.split("\n") if len(line) > 20][:5]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{api_base}/chat/completions", json={
                "model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3
            }, headers={"Authorization": f"Bearer {api_key}"})
            data = resp.json()
            result = data["choices"][0]["message"]["content"]
        
        facts = [line.strip("- ").strip() for line in result.split("\n") if line.strip().startswith("-")]
        return [f for f in facts if len(f) > 5]
    except Exception:
        return [line.strip("- ") for line in text.split("\n") if len(line) > 20][:3]

async def store_facts(team_id: str, facts: list[str], session_id: str = "") -> list[str]:
    if _repo is None: return []
    ids = []
    for fact in facts:
        row = await _repo.pool.fetchrow(
            """INSERT INTO memories (team_id, title, content, source_type, layer, source_session_id)
               VALUES ($1, $2, $3, 'agent', 'L1', $4) RETURNING id""",
            team_id, fact[:200], fact, session_id)
        ids.append(str(row["id"]))
    return ids
