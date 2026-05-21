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
        print(f"Username: {username}")
        print(f"UUID: {user_uuid}")

        # List all tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_names = [t['table_name'] for t in tables]
        print(f"Found tables: {table_names}")

        for table in table_names:
            # Get columns
            columns = await conn.fetch(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            col_names = [c['column_name'] for c in columns]
            
            # Check if any column might contain user identity
            matches = []
            for col in col_names:
                # Find matching UUID, username, or team_id
                query = f"SELECT count(*) FROM {table} WHERE CAST({col} AS TEXT) IN ($1, $2)"
                try:
                    count = await conn.fetchval(query, username, str(user_uuid))
                    if count > 0:
                        matches.append((col, count))
                except Exception:
                    pass
            
            if matches:
                print(f"\nTable: {table} has matches:")
                for col, count in matches:
                    print(f"  Column '{col}': {count} row(s)")
                    rows = await conn.fetch(f"SELECT * FROM {table} WHERE CAST({col} AS TEXT) IN ($1, $2)", username, str(user_uuid))
                    for r in rows:
                        print(f"    {dict(r)}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
