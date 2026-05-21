# AI Memory OS — Application Configuration

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Memory OS"
    version: str = "0.1.0"

    # PostgreSQL
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "memoryos"
    pg_password: str = "memoryos"
    pg_db: str = "memory_os"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    use_standalone: bool = False  # Docker mode enabled

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "password"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Embedding
    embedding_model: str = "text-embedding-v3"
    embedding_dim: int = 1024

    # Chunking
    chunk_size_tokens: int = 512
    # Tunable thresholds (configurable via admin/settings)
    internalize_similarity_threshold: float = 0.88
    internalize_min_content_length: int = 150
    search_rerank_threshold: float = 0.0
    lifecycle_promotion_importance: float = 0.8
    lifecycle_promotion_confidence: float = 0.8
    chunk_overlap_tokens: int = 64

    # Engines & Providers
    active_provider: str = "alibaba"
    language_model: str = "qwen-turbo"

    # SMTP (QQ Mail)
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = "luolimoa@qq.com"
    smtp_password: str = "eyprdnhhrhhxbdhe"
    smtp_from: str = "Cortex <luolimoa@qq.com>"
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    model_config = {"env_prefix": "MEMORY_OS_"}


settings = Settings()

# Surface insecure defaults loudly. Don't fail-fast — that breaks running deployments
# that haven't been migrated yet — but make sure operators can grep the logs for these.
import logging as _logging
_log = _logging.getLogger("config")
if settings.jwt_secret == "change-me-in-production":
    _log.warning(
        "MEMORY_OS_JWT_SECRET is using the built-in default 'change-me-in-production'. "
        "Set it to a random 64-char hex string before exposing this service to the network."
    )
if settings.minio_secret_key == "password" or settings.pg_password == "memoryos" or settings.neo4j_password == "password":
    _log.warning(
        "One or more datastore passwords are still at their compose-template defaults. "
        "Override POSTGRES_PASSWORD / NEO4J_PASSWORD / MINIO_ROOT_PASSWORD via .env before going public."
    )

# --- System-Wide Tuning Config Persistence (V5.1 Spec) ---
import json
from pathlib import Path
import os

SYS_CONFIG_FILE = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "memory-os" / "sys_config.json"

def load_system_config() -> dict:
    if SYS_CONFIG_FILE.exists():
        try:
            return json.loads(SYS_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {
        "rag": { "top_k": 5, "min_similarity": 0.60, "max_context_tokens": 2000, "history_count": 10 },
        "security": { "rate_write": 60, "rate_read": 120, "max_mem_len": 10000, "jwt_expire": 43200 },
        "reflection": { "decay_rate": 0.05, "quality_threshold": 0.80, "interval_hours": 24 }
    }

def save_system_config(config: dict) -> None:
    SYS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYS_CONFIG_FILE.write_text(json.dumps(config, indent=2))

