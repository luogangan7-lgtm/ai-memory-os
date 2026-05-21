"""Backfill: re-enqueue every memory with source_type='human' through the memory pipeline.

Use case: after a pipeline fix or a fresh deployment, you want existing human-authored
memories to flow through the L1/L2/L3 reflection stages again. The script inserts one
pipeline_conversations row per memory and queues a 'memory_pipeline' task pointing at it.

Run from the project root with the backend Python env active:
    python -m scripts.backfill_human_pipeline
or:
    PYTHONPATH=. python scripts/backfill_human_pipeline.py
"""

import asyncio
import json

from backend.api.db_helper import get_db_conn


async def main():
    conn = await get_db_conn()
    rows = await conn.fetch("SELECT id, team_id, agent_id, content FROM memories WHERE source_type='human'")
    print(f"Found {len(rows)} human memories.")
    for r in rows:
        team_id = r["team_id"]
        agent_id = r["agent_id"] or "default"
        messages = [{"role": "user", "content": r["content"]}]

        msg_json = json.dumps(messages, ensure_ascii=False)
        conv_row = await conn.fetchrow(
            """INSERT INTO pipeline_conversations (team_id, conversation_id, messages)
               VALUES ($1, $2, $3::jsonb) RETURNING id""",
            team_id, agent_id, msg_json
        )
        conv_id = conv_row["id"]

        payload_json = json.dumps({"session_id": agent_id, "conv_id": conv_id}, ensure_ascii=False)
        await conn.execute(
            """INSERT INTO pipeline_queue (team_id, task_type, payload_json, status, created_at)
               VALUES ($1, 'memory_pipeline', $2::jsonb, 'pending', NOW())""",
            team_id, payload_json
        )
    print("Done queuing!")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
