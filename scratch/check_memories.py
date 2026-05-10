import asyncio, asyncpg, json
from backend.services.config import settings

async def check():
    conn = await asyncpg.connect(host=settings.pg_host, port=settings.pg_port, user=settings.pg_user, password=settings.pg_password, database=settings.pg_db)
    rows = await conn.fetch("SELECT title, source_type, created_at FROM memories WHERE team_id = $1 ORDER BY created_at DESC LIMIT 5", "广州创业")
    for r in rows:
        print(f"Title: {r['title']} | Source: {r['source_type']} | Created: {r['created_at']}")
    await conn.close()

asyncio.run(check())
