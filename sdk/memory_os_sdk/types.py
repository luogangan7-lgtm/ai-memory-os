from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Memory:
    id: str; team_id: str = ""; workspace_id: str = ""; title: str = ""; content: str = ""
    category: str = ""; subcategory: Optional[str] = None; topic: Optional[str] = None
    memory_type: str = "general"; summary: Optional[str] = None
    embedding_model: str = ""; embedding_version: int = 1
    importance: float = 0.5; confidence: float = 0.5
    freshness: float = 1.0; lifecycle_stage: str = "recent"
    access_count: int = 0; source_type: str = "human"
    source_uri: Optional[str] = None; version: int = 1
    tags: list = field(default_factory=list); relations: list = field(default_factory=list)
    created_at: str = ""; updated_at: str = ""

@dataclass
class SearchResult:
    memory: Memory; score: float
    chunk_text: Optional[str] = None; graph_context: list = field(default_factory=list)

@dataclass
class GraphResult:
    nodes: list = field(default_factory=list); edges: list = field(default_factory=list)
