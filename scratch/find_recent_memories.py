import sys
sys.path.append("/Volumes/data/ai-memory-os")
import asyncio
import asyncpg
from datetime import datetime, timezone

DATABASE_URL = "postgresql://memoryos:memoryos@localhost:5432/memory_os"

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        username = "luolimoa"
        print("Checking recent memories...")
        rows = await conn.fetch("""
            SELECT id, title, content, layer, source_type, created_at 
            FROM memories 
            WHERE team_id = $1 AND created_at >= '2026-05-21 00:00:00+00'
            ORDER BY created_at DESC
        """, username)
        print(f"Found {len(rows)} memories created since 2026-05-21:")
        for r in rows:
            print(f"  ID: {r['id']} | Layer: {r['layer']} | Source: {r['source_type']} | Created: {r['created_at']}")
            print(f"    Title: {r['title']}")
            print(f"    Content: {r['content'][:150]}...")
            print("-" * 50)
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
