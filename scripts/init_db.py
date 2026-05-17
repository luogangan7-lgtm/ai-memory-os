#!/usr/bin/env python3
"""Initialize database schema - run once before first deploy."""
import asyncio, asyncpg, sys

async def init():
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        user="memoryos", password="memoryos", database="memory_os"
    )
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id UUID PRIMARY KEY,
            team_id TEXT NOT NULL DEFAULT '',
            workspace_id TEXT DEFAULT '',
            agent_id TEXT DEFAULT '',
            category TEXT,
            subcategory TEXT,
            topic TEXT,
            memory_type TEXT DEFAULT 'general',
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            embedding_model TEXT DEFAULT 'text-embedding-v3',
            embedding_version INTEGER DEFAULT 1,
            importance REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            freshness REAL DEFAULT 1.0,
            lifecycle_stage TEXT DEFAULT 'recent',
            access_count INTEGER DEFAULT 0,
            source_type TEXT DEFAULT 'human',
            source_uri TEXT,
            version INTEGER DEFAULT 1,
            tags TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_team ON memories(team_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(team_id, agent_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_topic ON memories(topic)")
    
    print("[OK] Database initialized")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(init())
