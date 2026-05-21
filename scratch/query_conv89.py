import sys
sys.path.append("/Volumes/data/ai-memory-os")
import asyncio
import asyncpg

DATABASE_URL = "postgresql://memoryos:memoryos@localhost:5432/memory_os"

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check conversation 89
        row_conv = await conn.fetchrow("SELECT * FROM pipeline_conversations WHERE id = 89")
        if row_conv:
            print("=== Conversation 89 ===")
            print(dict(row_conv))
        
        # Check memories created around 2026-05-21 19:29:00 to 19:35:00 UTC
        print("\n=== Memories created around 19:29 - 19:35 UTC ===")
        rows_m = await conn.fetch("""
            SELECT id, title, content, layer, source_type, created_at, source_session_id 
            FROM memories 
            WHERE created_at >= '2026-05-21 19:20:00+00' AND created_at <= '2026-05-21 19:40:00+00'
        """)
        for r in rows_m:
            print(dict(r))
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
