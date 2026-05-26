"""Alibaba Cloud Embedding Service — reads API key from admin-configured providers."""
from __future__ import annotations
import os, httpx
from typing import Any

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"

def _get_api_key() -> str:
    """Get DashScope API key from admin-configured provider, fallback to env."""
    # 1. Reload registry from file (handles admin key changes without restart)
    try:
        from backend.manager.registry import ModelRegistry
        reg = ModelRegistry.get_instance()
        # Force reload configs from disk to pick up admin changes
        if hasattr(reg, '_load_configs'):
            reg._load_configs()
        if reg and hasattr(reg, 'configs'):
            cfg: Any = reg.configs.get('alibaba', {})
            if hasattr(cfg, 'api_key') and cfg.api_key:
                return cfg.api_key
    except Exception:
        pass
    # 2. Fallback to env
    return os.getenv("DASHSCOPE_API_KEY", "")


class EmbeddingService:
    """Embedding via Alibaba Cloud text-embedding-v3 (1024-dim)."""

    def __init__(self, model: str = "text-embedding-v3"):
        self.model = model

    def load(self) -> None:
        """No-op: cloud API needs no local loading."""
        pass

    def encode(self, texts: list[str]) -> list[list[float]]:
        api_key = _get_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            DASHSCOPE_URL,
            json={
                "model": self.model,
                "input": texts,
                "dimensions": 1024,
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]
