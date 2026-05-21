import sys
sys.path.append("/Volumes/data/ai-memory-os")
import asyncio
import asyncpg
from backend.memory.pg_repo import safe_uuid

DATABASE_URL = "postgresql://memoryos:memoryos@localhost:5432/memory_os"

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        username = "luolimoa"
        user_uuid = safe_uuid(username)
        print(f"Username: {username} -> UUID: {user_uuid}")
        
        # Group by status
        rows = await conn.fetch("""
            SELECT status, count(*) 
            FROM pipeline_queue 
            WHERE team_id = $1 OR team_id = $2 
            GROUP BY status
        """, username, str(user_uuid))
        print("\nPipeline Queue status breakdown:")
        for r in rows:
            print(f"  {r['status']}: {r['count']}")

        # Group by task_type
        trows = await conn.fetch("""
            SELECT task_type, status, count(*)
            FROM pipeline_queue
            WHERE team_id = $1 OR team_id = $2
            GROUP BY task_type, status
        """, username, str(user_uuid))
        print("\nTask Type breakdown:")
        for r in trows:
            print(f"  {r['task_type']} ({r['status']}): {r['count']}")

        # Show pending or waiting or processing rows
        print("\nDetailed pending/waiting/processing rows:")
        detailed_rows = await conn.fetch("""
            SELECT id, task_type, payload_json, status, created_at, started_at, completed_at
            FROM pipeline_queue
            WHERE (team_id = $1 OR team_id = $2) AND status IN ('pending', 'processing', 'waiting_key', 'failed')
            ORDER BY created_at DESC
            LIMIT 20
        """, username, str(user_uuid))
        for r in detailed_rows:
            print(f"  {dict(r)}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
