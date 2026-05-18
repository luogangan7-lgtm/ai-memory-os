"""Shared database helper - auto-detects Docker vs Standalone mode."""
from __future__ import annotations
import os, asyncpg, aiosqlite
from pathlib import Path
from backend.services.config import settings

DATABASE_URL = os.getenv("DATABASE_URL", "")
STANDALONE_DB = str(Path.home() / ".codex" / "memory-os" / "memories.db")

class DBConn:
    """Unified database connection wrapper. Works with both asyncpg and aiosqlite."""
    def __init__(self, conn, is_standalone: bool, pool=None):
        self._conn = conn
        self._standalone = is_standalone
        self._pool = pool
    
    async def fetchrow(self, query: str, *args):
        if self._standalone:
            # Convert $1,$2,... to ?,?,...
            q = query
            for i in range(len(args), 0, -1):
                q = q.replace(f"${i}", "?")
            cursor = await self._conn.execute(q, args)
            row = await cursor.fetchone()
            await cursor.close()
            return row
        else:
            return await self._conn.fetchrow(query, *args)
    
    async def fetch(self, query: str, *args):
        if self._standalone:
            q = query
            for i in range(len(args), 0, -1):
                q = q.replace(f"${i}", "?")
            cursor = await self._conn.execute(q, args)
            rows = await cursor.fetchall()
            await cursor.close()
            return rows
        else:
            return await self._conn.fetch(query, *args)
    
    async def execute(self, query: str, *args):
        if self._standalone:
            q = query
            for i in range(len(args), 0, -1):
                q = q.replace(f"${i}", "?")
            await self._conn.execute(q, args)
            await self._conn.commit()
        else:
            await self._conn.execute(query, *args)
    
    async def close(self):
        if self._standalone:
            await self._conn.close()
        elif self._pool:
            await self._pool.release(self._conn)
        else:
            await self._conn.close()

async def get_db_conn() -> DBConn:
    if settings.use_standalone:
        db = await aiosqlite.connect(STANDALONE_DB)
        db.row_factory = aiosqlite.Row
        return DBConn(db, True)
    # Use global connection pool instead of creating new connections
    from backend.main import _pg_pool
    if _pg_pool:
        conn = await _pg_pool.acquire()
        return DBConn(conn, False, pool=_pg_pool)
    return DBConn(await asyncpg.connect(DATABASE_URL), False)
