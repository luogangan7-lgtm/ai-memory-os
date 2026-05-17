"""L3: User persona generation - aggregates scenarios into persistent user profile."""
from __future__ import annotations
import httpx, os
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo

_repo: MemoryRepo | None = None
PROMPT = (Path(__file__).parent / "prompts" / "l3_persona.txt").read_text(encoding="utf-8")

def init(repo: MemoryRepo): global _repo; _repo = repo

async def generate(team_id: str) -> str | None:
    if _repo is None: return None
    rows = await _repo.pool.fetch(
        "SELECT content_md FROM memory_scenarios WHERE team_id=$1 ORDER BY created_at DESC LIMIT 10",
        team_id)
    if not rows: return None
    scenarios = "\n\n---\n\n".join(r["content_md"] for r in rows)
    prompt = PROMPT + "\n\n" + scenarios

    api_key = os.getenv("PIPELINE_LLM_KEY", "")
    api_base = os.getenv("PIPELINE_LLM_BASE", "https://api.deepseek.com/v1")
    model = os.getenv("PIPELINE_LLM_MODEL", "deepseek-v4-pro")
    if not api_key: return f"## 用户画像\n{scenarios[:500]}"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{api_base}/chat/completions", json={
                "model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3
            }, headers={"Authorization": f"Bearer {api_key}"})
            data = resp.json()
            result = data["choices"][0]["message"]["content"]

        await _repo.pool.execute(
            """INSERT INTO user_persona (team_id, persona_md, scenario_count)
               VALUES ($1, $2, 1)
               ON CONFLICT (team_id) DO UPDATE SET persona_md=$2, scenario_count=user_persona.scenario_count+1, version=user_persona.version+1, updated_at=NOW()""",
            team_id, result)
        return result
    except: return None
