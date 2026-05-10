# AI Memory OS — Alibaba Cloud Embedding Service (text-embedding-v3)
# Uses DashScope API

from __future__ import annotations

import httpx

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
API_KEY = "sk-670638bdc88445f485b42d2d9c8633fa"


class EmbeddingService:
    """Embedding via Alibaba Cloud text-embedding-v3 (1024-dim)."""

    def __init__(self, model: str = "text-embedding-v3"):
        self.model = model

    def load(self) -> None:
        """No-op: cloud API needs no local loading."""
        pass

    def encode(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
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
