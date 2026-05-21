import sys
sys.path.append("/Volumes/data/ai-memory-os")
import asyncio
import asyncpg
from backend.memory.pg_repo import safe_uuid

DATABASE_URL = "postgresql://memoryos:memoryos@localhost:5432/memory_os"

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    with open("scratch/luolimoa_db_info.txt", "w") as f:
        try:
            username = "luolimoa"
            user_uuid = safe_uuid(username)
            f.write(f"Username: {username}\n")
            f.write(f"UUID: {user_uuid}\n\n")

            tables_of_interest = [
                "user_token_usage",
                "pipeline_usage",
                "pipeline_queue",
                "pipeline_conversations",
                "memories",
                "user_provider_configs",
                "user_persona",
                "task_canvas"
            ]

            for table in tables_of_interest:
                f.write(f"\n=================== Table: {table} ===================\n")
                # Find column names
                columns = await conn.fetch(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                """)
                col_names = [c['column_name'] for c in columns]
                
                # Find which columns match user_uuid or username
                matching_cols = []
                for col in col_names:
                    query = f"SELECT count(*) FROM {table} WHERE CAST({col} AS TEXT) IN ($1, $2)"
                    try:
                        count = await conn.fetchval(query, username, str(user_uuid))
                        if count > 0:
                            matching_cols.append(col)
                    except Exception:
                        pass
                
                if not matching_cols:
                    f.write("No matching rows.\n")
                    continue

                f.write(f"Matching columns: {matching_cols}\n")
                for col in matching_cols:
                    rows = await conn.fetch(f"SELECT * FROM {table} WHERE CAST({col} AS TEXT) IN ($1, $2)", username, str(user_uuid))
                    f.write(f"Rows matching via column '{col}' ({len(rows)} rows):\n")
                    for r in rows:
                        r_dict = dict(r)
                        # Truncate long content/messages for display
                        for k, v in list(r_dict.items()):
                            if isinstance(v, str) and len(v) > 200:
                                r_dict[k] = v[:200] + "..."
                            elif isinstance(v, list) and len(v) > 10:
                                r_dict[k] = v[:10] + ["..."]
                        f.write(f"  {r_dict}\n")

        finally:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
