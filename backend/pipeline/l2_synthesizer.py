"""L2: Scene synthesis - aggregates L1 atoms into coherent scenario blocks."""
from __future__ import annotations
import httpx, os
from pathlib import Path
from backend.memory.pg_repo import MemoryRepo

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

    api_key = os.getenv("PIPELINE_LLM_KEY", "")
    api_base = os.getenv("PIPELINE_LLM_BASE", "https://api.deepseek.com/v1")
    model = os.getenv("PIPELINE_LLM_MODEL", "deepseek-v4-pro")
    
    if not api_key: return f"## 场景归纳\n\n## 原子事实\n{facts}"
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{api_base}/chat/completions", json={
                "model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4
            }, headers={"Authorization": f"Bearer {api_key}"})
            data = resp.json()
            result = data["choices"][0]["message"]["content"]

        await _repo.pool.execute(
            """INSERT INTO memory_scenarios (team_id, title, content_md, atom_ids)
               VALUES ($1, $2, $3, $4)""",
            team_id, f"场景归纳 {result[:100]}", result, atom_ids or [])
        return result
    except: return None
