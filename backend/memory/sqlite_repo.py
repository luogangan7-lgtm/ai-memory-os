import json, aiosqlite, uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pathlib import Path
from backend.utils.crypto import encrypt_key, decrypt_key

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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_provider_configs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    api_base_url TEXT,
                    model_name TEXT,
                    is_active INTEGER DEFAULT 0,
                    validated_at TEXT,
                    created_at TEXT,
                    UNIQUE(user_id, provider_name)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_token_usage (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    model_name TEXT,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    memory_tokens_injected INTEGER DEFAULT 0,
                    tokens_saved_estimate INTEGER DEFAULT 0,
                    created_at TEXT
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

    # --- User-Pay API Keys & Token Usage Methods (V5.0 Spec) ---
    async def get_user_provider_config(self, user_id: str, provider_name: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_provider_configs WHERE user_id=? AND provider_name=?",
                (user_id, provider_name)
            ) as cursor:
                r = await cursor.fetchone()
                if not r: return None
                d = dict(r)
                d["api_key"] = decrypt_key(d["api_key"])
                return d

    async def get_active_user_provider_config(self, user_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_provider_configs WHERE user_id=? AND is_active=1 LIMIT 1",
                (user_id,)
            ) as cursor:
                r = await cursor.fetchone()
                if not r: return None
                d = dict(r)
                d["api_key"] = decrypt_key(d["api_key"])
                return d

    async def save_user_provider_config(self, user_id: str, provider_name: str, api_key: str, api_base_url: str = None, model_name: str = None, is_active: bool = False):
        now = datetime.now(timezone.utc).isoformat()
        encrypted = encrypt_key(api_key)
        async with aiosqlite.connect(self.db_path) as db:
            if is_active:
                # Set others to inactive first
                await db.execute("UPDATE user_provider_configs SET is_active=0 WHERE user_id=?", (user_id,))
            
            # Upsert
            await db.execute("""
                INSERT INTO user_provider_configs (id, user_id, provider_name, api_key, api_base_url, model_name, is_active, created_at, validated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, provider_name) DO UPDATE SET
                    api_key=excluded.api_key,
                    api_base_url=excluded.api_base_url,
                    model_name=excluded.model_name,
                    is_active=excluded.is_active,
                    validated_at=excluded.validated_at
            """, (str(uuid.uuid4()), user_id, provider_name, encrypted, api_base_url, model_name, 1 if is_active else 0, now, now))
            await db.commit()

    async def list_user_provider_configs(self, user_id: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM user_provider_configs WHERE user_id=?", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                res = []
                for r in rows:
                    d = dict(r)
                    d["api_key"] = decrypt_key(d["api_key"])
                    res.append(d)
                return res

    async def insert_user_token_usage(self, user_id: str, provider_name: str, model_name: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost_usd: float = 0.0, memory_tokens_injected: int = 0, tokens_saved_estimate: int = 0):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_token_usage (id, user_id, provider_name, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd, memory_tokens_injected, tokens_saved_estimate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), user_id, provider_name, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd, memory_tokens_injected, tokens_saved_estimate, now))
            await db.commit()

    async def close(self):
        pass
