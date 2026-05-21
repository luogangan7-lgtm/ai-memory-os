"""L3: User persona generation - uses user's LLM via ModelRegistry."""
from __future__ import annotations
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo
from backend.pipeline.llm_client import call_llm

_repo: MemoryRepo | None = None
PROMPT = (Path(__file__).parent / "prompts" / "l3_persona.txt").read_text(encoding="utf-8")

def init(repo: MemoryRepo): global _repo; _repo = repo

async def generate(team_id: str) -> tuple[str | None, int]:
    """Generate user persona. Returns (result_text, total_tokens)."""
    if _repo is None: return None, 0
    rows = await _repo.pool.fetch(
        "SELECT content_md FROM memory_scenarios WHERE team_id=$1 ORDER BY created_at DESC LIMIT 10",
        team_id)
    if not rows: return None, 0
    scenarios = "\n\n---\n\n".join(r["content_md"] for r in rows)
    prompt = PROMPT + "\n\n" + scenarios

    result, tokens = await call_llm(prompt, team_id, "reflection")
    if not result:
        return None, tokens

    await _repo.pool.execute(
        """INSERT INTO user_persona (team_id, persona_md, scenario_count)
           VALUES ($1, $2, 1)
           ON CONFLICT (team_id) DO UPDATE SET persona_md=$2, scenario_count=user_persona.scenario_count+1, version=user_persona.version+1, updated_at=NOW()""",
        team_id, result)
    return result, tokens
