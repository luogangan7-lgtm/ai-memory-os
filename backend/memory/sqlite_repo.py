import json, aiosqlite
from datetime import datetime, timezone
from typing import Any, Optional
from pathlib import Path

class SQLiteMemoryRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @classmethod
    async def create(cls, db_path: str = None):
        if not db_path:
            db_dir = Path.home() / ".codex" / "memory-os"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "memories.db")
        
        repo = cls(db_path)
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
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
                    tags TEXT, -- JSON array string
                    metadata TEXT, -- JSON object string
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT,
                    agent_id TEXT,
                    action TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        return repo

    async def insert(self, **kw):
        now = datetime.now(timezone.utc).isoformat()
        fields = ["id","team_id","workspace_id","agent_id","category","subcategory","topic","memory_type","title","content","summary","embedding_model","importance","confidence","source_type","source_uri","tags","metadata","created_at","updated_at"]
        
        tags = json.dumps(kw.get("tags", []))
        metadata = json.dumps(kw.get("metadata", {}))
        
        vals = [
            kw.get("id"), kw.get("team_id"), kw.get("workspace_id"), kw.get("agent_id"),
            kw.get("category"), kw.get("subcategory"), kw.get("topic"), kw.get("memory_type"),
            kw.get("title"), kw.get("content"), kw.get("summary"), kw.get("embedding_model"),
            kw.get("importance", 0.5), kw.get("confidence", 0.5), kw.get("source_type"),
            kw.get("source_uri"), tags, metadata, now, now
        ]
        
        q = f"INSERT INTO memories ({','.join(fields)}) VALUES ({','.join(['?']*len(fields))})"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(q, vals)
            await db.commit()
        return kw["id"]

    async def get(self, mid):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM memories WHERE id=?", (mid,)) as cursor:
                r = await cursor.fetchone()
                if not r: return None
                d = dict(r)
                d["tags"] = json.loads(d["tags"]) if d["tags"] else []
                d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
                return d

    async def list_recent(self, team_id, limit=20, filter="all"):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            q = "SELECT * FROM memories WHERE team_id=?"
            if filter == "agent": q += " AND (source_type='agent' OR source_type='human' OR source_type IS NULL)"
            elif filter == "knowledge": q += " AND source_type='knowledge'"
            q += " ORDER BY created_at DESC LIMIT ?"
            async with db.execute(q, (team_id, limit)) as cursor:
                rows = await cursor.fetchall()
                res = []
                for r in rows:
                    d = dict(r)
                    d["tags"] = json.loads(d["tags"]) if d["tags"] else []
                    d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
                    res.append(d)
                return res

    async def audit(self, memory_id: str, agent_id: str, action: str, details: dict = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO audit_log (memory_id, agent_id, action, details) VALUES (?,?,?,?)",
                (memory_id, agent_id, action, json.dumps(details or {}))
            )
            await db.commit()

    async def close(self):
        pass
