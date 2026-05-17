"""L1: Atomic fact extraction - uses user's LLM via ModelRegistry."""
from __future__ import annotations
import json
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo
from backend.pipeline.llm_client import call_llm

_repo: MemoryRepo | None = None
PROMPT = (Path(__file__).parent / "prompts" / "l1_extract.txt").read_text(encoding="utf-8")

def init(repo: MemoryRepo): global _repo; _repo = repo

async def extract_from_conversation(conv_id: str, team_id: str) -> list[str]:
    if _repo is None: return []
    row = await _repo.pool.fetchrow(
        "SELECT messages FROM pipeline_conversations WHERE id=$1 AND team_id=$2", conv_id, team_id)
    if not row: return []
    msgs = json.loads(row["messages"]) if isinstance(row["messages"], str) else row["messages"]
    text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs[-10:])
    
    prompt = PROMPT + "\n\n" + text
    result = await call_llm(prompt, team_id, "classifier")
    
    facts = [line.strip("- ").strip() for line in result.split("\n") if line.strip().startswith("-")]
    return [f for f in facts if len(f) > 5]

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
