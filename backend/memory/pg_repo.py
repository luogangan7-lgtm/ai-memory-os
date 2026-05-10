import json, asyncpg
from datetime import datetime, timezone
from typing import Any, Optional
from backend.services.resilience import retry, CircuitBreaker

class MemoryRepo:
    def __init__(self, pool):
        self.pool = pool
        self._cb = CircuitBreaker()

    @classmethod
    async def create(cls, host='localhost', port=5432, user='memoryos', password='memoryos', database='memory_os'):
        pool = await asyncpg.create_pool(host=host, port=port, user=user, password=password, database=database, min_size=2, max_size=20)
        async with pool.acquire() as conn:
            # Auto-Migration: Ensure table structure is up to date
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    team_id TEXT,
                    workspace_id TEXT,
                    agent_id TEXT,
                    category TEXT,
                    subcategory TEXT,
                    topic TEXT,
                    memory_type TEXT,
                    title TEXT,
                    content TEXT,
                    summary TEXT,
                    embedding_model TEXT,
                    importance FLOAT,
                    confidence FLOAT,
                    source_type TEXT,
                    source_uri TEXT,
                    tags TEXT[],
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE
                );
                
                -- Add columns if they were missing from older versions
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS subcategory TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS topic TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS source_type TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata JSONB;
            """)
        return cls(pool)


    @retry(max_retries=2, delay=0.3)
    async def insert(self, **kw):
        now = datetime.now(timezone.utc)
        fields = ["id","team_id","workspace_id","agent_id","category","subcategory","topic","memory_type","title","content","summary","embedding_model","importance","confidence","source_type","source_uri","tags","metadata","created_at","updated_at"]
        vals = {**kw, "created_at": now, "updated_at": now, "tags": kw.get("tags",[]), "metadata": json.dumps(kw.get("metadata",{}))}
        q = "INSERT INTO memories (" + ",".join(fields) + ") VALUES (" + ",".join("$"+str(i+1) for i in range(len(fields))) + ")"
        async with self.pool.acquire() as conn:
            await conn.execute(q, *(vals.get(f) for f in fields))
        return kw["id"]

    async def get(self, mid):
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM memories WHERE id=$1", mid)
        return dict(r) if r else None

    async def get_by_ids(self, ids):
        if not ids: return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM memories WHERE id = ANY($1)", ids)
        return [dict(r) for r in rows]

    async def update_access(self, mid):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE memories SET access_count=access_count+1, updated_at=$2 WHERE id=$1", mid, datetime.now(timezone.utc))

    
    async def audit(self, memory_id: str, agent_id: str, action: str, details: dict = None):
        """Record an audit log entry."""
        import json
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO audit_log (memory_id, agent_id, action, details) VALUES ($1,$2,$3,$4)",
                memory_id, agent_id, action, json.dumps(details or {})
            )

    async def list_recent(self, team_id, limit=20, filter="all"):
        async with self.pool.acquire() as conn:
            q = "SELECT * FROM memories WHERE team_id=$1"
            if filter == "agent": q += " AND (source_type='agent' OR source_type='human' OR source_type IS NULL)"
            elif filter == "knowledge": q += " AND source_type='knowledge'"
            q += " ORDER BY created_at DESC LIMIT $2"
            rows = await conn.fetch(q, team_id, limit)

        return [dict(r) for r in rows]


    async def count_by_team(self, team_id, source_type=None):
        async with self.pool.acquire() as conn:
            if source_type:
                return await conn.fetchval("SELECT count(*) FROM memories WHERE team_id=$1 AND source_type=$2", team_id, source_type)
            return await conn.fetchval("SELECT count(*) FROM memories WHERE team_id=$1", team_id)

    async def delete(self, mid, team_id):
        async with self.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM memories WHERE id=$1 AND team_id=$2", mid, team_id)
            return "DELETE 1" in r

    async def save_version(self, memory_id: str, title: str, content: str, editor_id: str):
        """Save a version snapshot before update."""
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow("SELECT max(version) as v FROM memory_versions WHERE memory_id=$1", memory_id)
            ver = (r["v"] or 0) + 1 if r else 1
            await conn.execute(
                "INSERT INTO memory_versions (memory_id, version, title, content, editor_id) VALUES ($1,$2,$3,$4,$5)",
                memory_id, ver, title, content, editor_id
            )

    async def close(self):
        await self.pool.close()
