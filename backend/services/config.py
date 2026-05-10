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
    qdrant_port: int = 6335
    use_standalone: bool = True  # SQLite mode, no Docker needed

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

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
    search_rerank_threshold: float = 0.85
    lifecycle_promotion_importance: float = 0.8
    lifecycle_promotion_confidence: float = 0.8
    chunk_overlap_tokens: int = 64

    # Engines & Providers
    active_provider: str = "alibaba"
    language_model: str = "qwen-turbo"

    model_config = {"env_prefix": "MEMORY_OS_"}


settings = Settings()
