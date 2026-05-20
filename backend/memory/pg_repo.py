import json, asyncpg, uuid
from datetime import datetime, timezone
from typing import Any, Optional
from backend.services.resilience import retry, CircuitBreaker
from backend.utils.crypto import encrypt_key, decrypt_key

def safe_uuid(id_str: str) -> uuid.UUID:
    """Safely convert any arbitrary string into a stable UUID v5 based on namespace."""
    if not id_str:
        return uuid.uuid4()
    try:
        return uuid.UUID(id_str)
    except ValueError:
        # Map non-UUID strings like "default" or usernames deterministically to UUIDs
        return uuid.uuid5(uuid.NAMESPACE_DNS, id_str)

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
                    updated_at TIMESTAMP WITH TIME ZONE,
                    lifecycle_stage TEXT DEFAULT 'recent'
                );
                
                -- Add columns if they were missing from older versions
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS subcategory TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS topic TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS source_type TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata JSONB;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS agent_id TEXT DEFAULT '';
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS lifecycle_stage TEXT DEFAULT 'recent';
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS layer TEXT DEFAULT 'L0';
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS source_session_id TEXT;

                -- Ensure audit_log table exists
                CREATE TABLE IF NOT EXISTS audit_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    memory_id TEXT,
                    agent_id TEXT,
                    action TEXT NOT NULL,
                    details JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );

                -- Ensure user_provider_configs table exists
                CREATE TABLE IF NOT EXISTS user_provider_configs (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    provider_name VARCHAR(64) NOT NULL,
                    api_key TEXT NOT NULL,
                    api_base_url TEXT,
                    model_name VARCHAR(128),
                    is_active BOOLEAN DEFAULT false,
                    validated_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    UNIQUE(user_id, provider_name)
                );

                -- Ensure user_token_usage table exists
                CREATE TABLE IF NOT EXISTS user_token_usage (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    provider_name VARCHAR(64) NOT NULL,
                    model_name VARCHAR(128),
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost_usd DECIMAL(10,6) DEFAULT 0.0,
                    memory_tokens_injected INTEGER DEFAULT 0,
                    tokens_saved_estimate INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );

                -- System LLM Engine Configs
                CREATE TABLE IF NOT EXISTS system_llm_configs (
                    id          SERIAL PRIMARY KEY,
                    engine_type VARCHAR(20) NOT NULL UNIQUE,  -- 'embed' | 'reflect' | 'classify'
                    provider    VARCHAR(50),
                    model_name  VARCHAR(100),
                    api_base_url VARCHAR(255),
                    api_key_encrypted TEXT,                   -- AES-256 加密后的 API Key
                    extra_params JSONB DEFAULT '{}',
                    updated_at  TIMESTAMPTZ DEFAULT NOW()
                );

                -- Documents table
                CREATE TABLE IF NOT EXISTS documents (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    team_id     VARCHAR(100) NOT NULL,
                    filename    VARCHAR(500),
                    minio_key   VARCHAR(500),                 -- MinIO Object Path
                    chunk_count INTEGER DEFAULT 0,
                    file_size   BIGINT,
                    tags        TEXT[],
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_documents_team_id ON documents(team_id);

                -- Accounts table (Migrated from JSON for concurrency)

                -- V6.0 Core tables
                CREATE TABLE IF NOT EXISTS pipeline_conversations (
                    id SERIAL PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    messages JSONB DEFAULT '[]',
                    started_at TIMESTAMP WITH TIME ZONE,
                    ended_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS memory_scenarios (
                    id SERIAL PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL UNIQUE,
                    title VARCHAR(300) NOT NULL,
                    content_md TEXT NOT NULL,
                    atom_ids TEXT[] DEFAULT '{}',
                    source_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS user_persona (
                    id SERIAL PRIMARY KEY,
                    team_id TEXT NOT NULL UNIQUE,
                    persona_md TEXT DEFAULT '',
                    scenario_count INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS task_canvas (
                    id SERIAL PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    task_title VARCHAR(300) DEFAULT '',
                    canvas_mermaid TEXT DEFAULT '',
                    completed_steps JSONB DEFAULT '[]',
                    next_steps JSONB DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    UNIQUE(team_id, task_id)
                );
                CREATE TABLE IF NOT EXISTS pipeline_usage (
                    id SERIAL PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    year_month VARCHAR(7) NOT NULL,
                    l1_calls INTEGER DEFAULT 0,
                    l2_calls INTEGER DEFAULT 0,
                    l3_calls INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    UNIQUE(team_id, year_month)
                );
                CREATE TABLE IF NOT EXISTS pipeline_queue (
                    id SERIAL PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    task_type VARCHAR(50) NOT NULL,
                    payload_json JSONB DEFAULT '{}',
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    username TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    role TEXT DEFAULT 'user',
                    agent_id TEXT,
                    revoked BOOLEAN DEFAULT false,
                    suspended BOOLEAN DEFAULT false,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                CREATE INDEX IF NOT EXISTS idx_accounts_api_key ON accounts(api_key);
            """)
        return cls(pool)

    @retry(max_retries=2, delay=0.3)
    async def update(self, mid: str, team_id: str, **kw):
        """Update an existing memory."""
        fields = []
        values = []
        i = 1
        for k, v in kw.items():
            fields.append(f"{k} = ${i}")
            if k == "metadata" and isinstance(v, dict):
                values.append(json.dumps(v))
            else:
                values.append(v)
            i += 1
        
        values.append(datetime.now(timezone.utc))
        q = f"UPDATE memories SET {', '.join(fields)}, updated_at = ${i} WHERE id = ${i+1} AND team_id = ${i+2}"
        values.append(mid)
        values.append(team_id)
        
        async with self.pool.acquire() as conn:
            r = await conn.execute(q, *values)
            return "UPDATE 1" in r

    async def list_documents(self, team_id: str):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM documents WHERE team_id = $1 ORDER BY created_at DESC", team_id)
        return [dict(r) for r in rows]

    async def delete_document(self, doc_id: str, team_id: str):
        async with self.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM documents WHERE id = $1 AND team_id = $2", safe_uuid(doc_id), team_id)
            return "DELETE 1" in r

    async def insert_document(self, team_id: str, filename: str, minio_key: str, chunk_count: int, file_size: int, tags: list[str] = None):
        async with self.pool.acquire() as conn:
            doc_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO documents (id, team_id, filename, minio_key, chunk_count, file_size, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, doc_id, team_id, filename, minio_key, chunk_count, file_size, tags or [])
            return doc_id


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

    
    async def audit(self, memory_id: str, agent_id: str, action: str, details: dict = None, team_id: str = "default"):
        """Record an audit log entry mapping to DB schema."""
        import json
        import uuid
        try:
            res_id = None
            if memory_id:
                try:
                    res_id = uuid.UUID(memory_id)
                except ValueError:
                    pass
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO audit_log (team_id, user_id, action, resource_type, resource_id, details) VALUES ($1,$2,$3,$4,$5,$6)",
                    team_id, agent_id, action, "memory", res_id, json.dumps(details or {})
                )
        except Exception as e:
            print(f"[pg_repo.audit] Failed to record audit log: {e}")

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

    async def get_total_memory_count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT count(*) FROM memories") or 0

    async def get_total_team_count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT count(DISTINCT team_id) FROM accounts") or 0

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

    async def add_message(self, team_id: str, agent_id: str, role: str, content: str):
        """High-level helper to archive a chat message into memory."""
        import uuid
        mid = str(uuid.uuid4())
        return await self.insert(
            id=mid,
            team_id=team_id,
            workspace_id=agent_id or "default",
            agent_id=agent_id or "default",
            category="conversation",
            memory_type="chat",
            title=f"{role.capitalize()} Message",
            content=content,
            source_type="agent" if role == "assistant" else "human",
            importance=0.5
        )

    # --- User-Pay API Keys & Token Usage Methods (V5.0 Spec) ---
    async def get_user_provider_config(self, user_id: str, provider_name: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT * FROM user_provider_configs WHERE user_id=$1 AND provider_name=$2",
                safe_uuid(user_id), provider_name
            )
            if not r: return None
            d = dict(r)
            d["api_key"] = decrypt_key(d["api_key"])
            return d

    async def get_active_user_provider_config(self, user_id: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT * FROM user_provider_configs WHERE user_id=$1 AND is_active=true LIMIT 1",
                safe_uuid(user_id)
            )
            if not r: return None
            d = dict(r)
            d["api_key"] = decrypt_key(d["api_key"])
            return d

    async def save_user_provider_config(self, user_id: str, provider_name: str, api_key: str, api_base_url: str = None, model_name: str = None, is_active: bool = False):
        encrypted = encrypt_key(api_key)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if is_active:
                    await conn.execute("UPDATE user_provider_configs SET is_active=false WHERE user_id=$1", safe_uuid(user_id))
                
                await conn.execute("""
                    INSERT INTO user_provider_configs (id, user_id, provider_name, api_key, api_base_url, model_name, is_active, validated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, now())
                    ON CONFLICT(user_id, provider_name) DO UPDATE SET
                        api_key=excluded.api_key,
                        api_base_url=excluded.api_base_url,
                        model_name=excluded.model_name,
                        is_active=excluded.is_active,
                        validated_at=now()
                """, uuid.uuid4(), safe_uuid(user_id), provider_name, encrypted, api_base_url, model_name, is_active)

    async def list_user_provider_configs(self, user_id: str) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM user_provider_configs WHERE user_id=$1", safe_uuid(user_id))
            res = []
            for r in rows:
                d = dict(r)
                d["api_key"] = decrypt_key(d["api_key"])
                res.append(d)
            return res

    async def insert_user_token_usage(self, user_id: str, provider_name: str, model_name: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost_usd: float = 0.0, memory_tokens_injected: int = 0, tokens_saved_estimate: int = 0):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_token_usage (id, user_id, provider_name, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd, memory_tokens_injected, tokens_saved_estimate, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
            """, uuid.uuid4(), safe_uuid(user_id), provider_name, model_name, prompt_tokens, completion_tokens, total_tokens, cost_usd, memory_tokens_injected, tokens_saved_estimate)

    async def increment_pipeline_usage(self, team_id: str, layer: str, tokens: int = 0):
        ym = datetime.now(timezone.utc).strftime("%Y-%m")
        l1 = 1 if layer == 'L1' else 0
        l2 = 1 if layer == 'L2' else 0
        l3 = 1 if layer == 'L3' else 0
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO pipeline_usage (team_id, year_month, l1_calls, l2_calls, l3_calls, total_tokens)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (team_id, year_month) DO UPDATE SET
                    l1_calls = pipeline_usage.l1_calls + EXCLUDED.l1_calls,
                    l2_calls = pipeline_usage.l2_calls + EXCLUDED.l2_calls,
                    l3_calls = pipeline_usage.l3_calls + EXCLUDED.l3_calls,
                    total_tokens = pipeline_usage.total_tokens + EXCLUDED.total_tokens
            """, team_id, ym, l1, l2, l3, tokens)

    # --- Account Management Methods ---
    async def get_account(self, username: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM accounts WHERE username=$1 OR email=$1", username)
            return dict(r) if r else None

    async def get_account_by_email(self, email: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM accounts WHERE email=$1", email)
            return dict(r) if r else None

    async def get_account_by_token(self, token: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow("SELECT * FROM accounts WHERE api_key=$1", token)
            return dict(r) if r else None

    async def insert_account(self, username: str, team_id: str, password_hash: str, api_key: str, role: str = 'user', agent_id: str = None, email: str = None, is_verified: bool = False, metadata: dict = None):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO accounts (username, team_id, password_hash, api_key, role, agent_id, email, is_verified, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, username, team_id, password_hash, api_key, role, agent_id or username, email, is_verified, json.dumps(metadata or {}))

    async def list_accounts(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM accounts ORDER BY created_at DESC")
            return [dict(r) for r in rows]

    async def update_account_status(self, username: str, revoked: bool = None, suspended: bool = None, api_key: str = None):
        fields = []
        vals = []
        i = 1
        if revoked is not None:
            fields.append(f"revoked = ${i}")
            vals.append(revoked)
            i += 1
        if suspended is not None:
            fields.append(f"suspended = ${i}")
            vals.append(suspended)
            i += 1
        if api_key is not None:
            fields.append(f"api_key = ${i}")
            vals.append(api_key)
            i += 1
        
        if not fields: return False
        
        vals.append(datetime.now(timezone.utc))
        vals.append(username)
        q = f"UPDATE accounts SET {', '.join(fields)}, updated_at = ${i} WHERE username = ${i+1}"
        
        async with self.pool.acquire() as conn:
            r = await conn.execute(q, *vals)
            return "UPDATE 1" in r

    async def delete_account(self, username: str) -> bool:
        import logging
        async with self.pool.acquire() as conn:
            # 1. Fetch the user's team_id
            row = await conn.fetchrow("SELECT team_id FROM accounts WHERE username=$1", username)
            if not row:
                return False
            team_id = row["team_id"]
            
            # 2. Transactionally cascade-delete all PG table relationships
            async with conn.transaction():
                await conn.execute("DELETE FROM user_provider_configs WHERE user_id=$1", safe_uuid(username))
                await conn.execute("DELETE FROM user_token_usage WHERE user_id=$1", safe_uuid(username))
                await conn.execute("DELETE FROM audit_log WHERE user_id=$1", username)
                await conn.execute("DELETE FROM memories WHERE team_id=$1", team_id)
                r = await conn.execute("DELETE FROM accounts WHERE username=$1", username)
                
            # 3. Clean up the physical vector store collection or data entries (Qdrant or LanceDB)
            try:
                from backend.manager.registry import ModelRegistry
                registry = ModelRegistry.get_instance()
                if registry and registry.qs:
                    qs = registry.qs
                    if hasattr(qs, "client") and hasattr(qs.client, "delete_collection"):
                        # Qdrant: delete the entire per-team isolated vector collection
                        collection_name = f"memory_team_{team_id}"
                        try:
                            qs.client.delete_collection(collection_name)
                            logging.info(f"Successfully deleted Qdrant vector collection: {collection_name}")
                        except Exception as e:
                            logging.warning(f"Could not delete Qdrant collection {collection_name}: {e}")
                    elif hasattr(qs, "db") and hasattr(qs, "table_name"):
                        # LanceDB: delete all records belonging to this team_id
                        try:
                            if qs.table_name in qs.db.table_names():
                                table = qs.db.open_table(qs.table_name)
                                table.delete(f"team_id = '{team_id}'")
                                logging.info(f"Successfully cleaned up LanceDB vector records for team: {team_id}")
                        except Exception as e:
                            logging.warning(f"Could not delete LanceDB records for team {team_id}: {e}")
            except Exception as e:
                logging.warning(f"Failed to clean up vector store during user deletion: {e}")
                
            return "DELETE 1" in r

    async def close(self):
        await self.pool.close()
