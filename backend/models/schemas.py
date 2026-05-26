# AI Memory OS — Pydantic Models
# Blueprint Section 5 — Memory Object Schema

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator



from pydantic import field_validator

# Standard metadata fields that must be present
REQUIRED_METADATA_KEYS: list[str] = []

def validate_memory_tags(tags: list[str]) -> list[str]:
    """Normalize tags: lowercase, no spaces."""
    return [t.lower().replace(' ', '-').strip()[:50] for t in tags if t.strip()]

def validate_category(cat: str) -> str:
    """Normalize category to standard set."""
    valid = {"ai","finance","trading","marketing","research","programming","personal","projects","general","relationships","testing"}
    cat_lower = cat.lower().strip()
    return cat_lower if cat_lower in valid else "general"

class MemoryStoreRequest(BaseModel):
    """Payload for POST /memory/store"""
    team_id: str = "default"
    workspace_id: str = "default"
    agent_id: str = ""
    category: str = "general"
    subcategory: Optional[str] = None
    topic: Optional[str] = None
    memory_type: str = "general"
    title: str
    content: str
    summary: Optional[str] = None
    embedding_model: str = "text-embedding-v3"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    lifecycle_stage: str = "recent"
    source_type: str = "human"
    agent_source: Optional[str] = "unknown"


    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if v is None: return []
        return [t.lower().replace(" ","-").strip()[:50] for t in v if t.strip()]

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v):
        if not v or not str(v).strip(): return "general"
        return str(v).lower().strip()
    source_uri: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    relations: list[MemoryRelation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRelation(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0


class MemoryResponse(BaseModel):
    id: str
    team_id: str
    workspace_id: str
    agent_id: str = ""
    category: str
    subcategory: Optional[str] = None
    topic: Optional[str] = None
    memory_type: str
    title: str
    content: str
    summary: Optional[str] = None
    embedding_model: str
    embedding_version: int = 1
    importance: float
    confidence: float
    freshness: float = 1.0
    lifecycle_stage: str = "recent"
    access_count: int = 0
    source_type: str
    source_uri: Optional[str] = None
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str


class MemorySearchRequest(BaseModel):
    """Payload for POST /memory/search"""
    query: str
    team_id: str = "default"
    agent_id: str = ""
    workspace_id: str = "default"

    category: Optional[str] = None
    memory_type: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=100)
    use_rerank: bool = True
    source_type: Optional[str] = None
    layer: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    use_graph: bool = False
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    score: float
    chunk_text: Optional[str] = None
    graph_context: list[dict[str, Any]] = Field(default_factory=list)


class GraphQueryRequest(BaseModel):
    """Payload for POST /memory/graph"""
    memory_id: Optional[str] = None
    team_id: str = "default"
    relation_types: list[str] = Field(default_factory=list)
    max_depth: int = Field(default=2, ge=1, le=5)
    top_k: int = Field(default=20, ge=1, le=100)


class GraphNode(BaseModel):
    id: str
    title: str
    category: str
    memory_type: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relation_type: str
    weight: float


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class LongTermMemoryRequest(BaseModel):
    """Payload for POST /memory/longterm"""
    team_id: str = "default"
    workspace_id: str = "default"
    agent_id: str = ""
    top_k: int = Field(default=5, ge=1, le=50)
    min_importance: float = Field(default=0.6, ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


class LifecycleTransitionRequest(BaseModel):
    """Promote/demote a memory between lifecycle stages."""
    memory_id: str
    target_stage: str  # recent / working / longterm / core
