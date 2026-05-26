# AI Memory OS — Provider Base Class
# All embedding/rerank/LLM providers inherit from this.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ProviderType(str, Enum):
    EMBEDDING = "embedding"
    RERANK = "rerank"
    LLM = "llm"


class ModelCapability(str, Enum):
    EMBED = "embed"
    RERANK = "rerank"
    CHAT = "chat"
    VISION = "vision"
    AUDIO = "audio"


@dataclass
class ModelInfo:
    """Describes a single model from a provider."""
    id: str
    display_name: str
    provider: str
    capabilities: list[ModelCapability] = field(default_factory=list)
    context_window: int = 8192
    embedding_dim: Optional[int] = None
    description: str = ""
    pricing_per_1m_tokens: float = 0.0


@dataclass
class ProviderConfig:
    """User-provided configuration for a cloud provider."""
    provider_type: str  # "alibaba", "openai", "zhipu"
    api_key: str
    api_base: str = ""
    enabled_capabilities: list[ProviderType] = field(default_factory=list)
    enabled_models: dict[str, str] = field(default_factory=dict)
    # e.g. {"embedding": "text-embedding-v3", "rerank": "qwen3-rerank"}


class BaseProvider(ABC):
    """Abstract provider: cloud or local."""

    provider_name: str = "base"

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def validate(self) -> dict | bool:
        """Test connection and API key validity."""
        ...

    @abstractmethod
    async def discover_models(self) -> list[ModelInfo]:
        """List all available models and their capabilities."""
        ...

    def supports(self, capability: ModelCapability) -> bool:
        """Check if any enabled model supports this capability."""
        return False

    # ── Optional capability methods ──

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(f"{self.provider_name} does not support embedding")

    async def rerank(
        self, query: str, documents: list[str], top_n: int = 10
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(f"{self.provider_name} does not support rerank")

    async def chat(self, messages: list[dict], stream: bool = False, **kwargs) -> Any:
        raise NotImplementedError(f"{self.provider_name} does not support chat")
