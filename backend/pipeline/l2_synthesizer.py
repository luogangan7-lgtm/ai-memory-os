"""L2: Scene synthesis - uses user's LLM via ModelRegistry."""
from __future__ import annotations
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo
from backend.pipeline.llm_client import call_llm

_repo: MemoryRepo | None = None
PROMPT = (Path(__file__).parent / "prompts" / "l2_synthesize.txt").read_text(encoding="utf-8")

def init(repo: MemoryRepo): global _repo; _repo = repo

async def synthesize(team_id: str, atom_ids: list[str] | None = None) -> str | None:
    if _repo is None: return None
    rows = await _repo.pool.fetch(
        "SELECT title, content FROM memories WHERE team_id=$1 AND layer='L1' ORDER BY created_at DESC LIMIT 30",
        team_id)
    if not rows: return None
    facts = "\n".join(f"- {r['title']}: {r['content'][:200]}" for r in rows)
    prompt = PROMPT + "\n\n" + facts
    
    result = await call_llm(prompt, team_id, "reflection")
    import uuid
    scenario_id = str(uuid.uuid4())
    await _repo.pool.execute(
        """INSERT INTO memory_scenarios (team_id, scenario_id, title, content_md, atom_ids)
           VALUES ($1, $2, $3, $4, $5)""",
        team_id, scenario_id, result[:100], result, atom_ids or [])
    return result
