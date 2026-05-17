"""L0: Raw conversation recorder - captures complete dialogs for pipeline processing."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from backend.memory.pg_repo import MemoryRepo

_repo: MemoryRepo | None = None

def init(repo: MemoryRepo):
    global _repo
    _repo = repo

async def record_conversation(team_id: str, session_id: str, messages: list[dict], agent_id: str = "default") -> str | None:
    if _repo is None: return None
    msg_json = json.dumps(messages, ensure_ascii=False)
    result = await _repo.pool.fetchrow(
        """INSERT INTO pipeline_conversations (team_id, session_id, agent_id, messages)
           VALUES ($1, $2, $3, $4::jsonb) RETURNING id""",
        team_id, session_id, agent_id, msg_json
    )
    return str(result["id"]) if result else None
