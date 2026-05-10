# AI Memory OS — Alibaba Cloud DashScope Provider

from __future__ import annotations

from typing import Any
import httpx
from backend.providers.base import (
    BaseProvider, ModelCapability, ModelInfo, ProviderConfig,
)

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"

ALIBABA_MODELS = {
    "text-embedding-v3": ModelInfo(
        id="text-embedding-v3", display_name="Text Embedding V3",
        provider="alibaba", capabilities=[ModelCapability.EMBED],
        context_window=8192, embedding_dim=1024,
        description="1024-dim, 100+ languages, 8K context",
        pricing_per_1m_tokens=0.70,
    ),
    "qwen3-rerank": ModelInfo(
        id="qwen3-rerank", display_name="Qwen3 Rerank",
        provider="alibaba", capabilities=[ModelCapability.RERANK],
        context_window=4000,
        description="100+ languages, cross-encoder reranker",
        pricing_per_1m_tokens=0.50,
    ),
}


class AlibabaProvider(BaseProvider):
    provider_name = "alibaba"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "密钥为空"}
        try:
            # Use lightweight model list check to avoid rate limit abuse
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{DASHSCOPE_BASE}/compatible-mode/v1/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
        except Exception as e:
            err_msg = str(e)
            print(f"DEBUG: Alibaba Validation Failed: {err_msg}", flush=True)
            return {"valid": False, "error": err_msg}

    async def discover_models(self) -> list[ModelInfo]:
        return list(ALIBABA_MODELS.values())

    def supports(self, capability: ModelCapability) -> bool:
        model_id = self.config.enabled_models.get({
            ModelCapability.EMBED: "embedding",
            ModelCapability.RERANK: "rerank",
        }.get(capability, ""), "")
        if model_id not in ALIBABA_MODELS:
            return False
        return capability in ALIBABA_MODELS[model_id].capabilities

    async def chat(self, messages: list[dict], **kwargs) -> str:
        model = self.config.enabled_models.get("chat", "qwen-turbo")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{DASHSCOPE_BASE}/compatible-mode/v1/chat/completions",
                json={
                    "model": model, "messages": messages,
                    "max_tokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.3),
                },
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.config.enabled_models.get("embedding", "text-embedding-v3")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{DASHSCOPE_BASE}/compatible-mode/v1/embeddings",
                json={"model": model, "input": texts, "dimensions": 1024},
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Record token usage
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", sum(len(t) for t in texts) // 2)
            from backend.services.cost_tracker import CostTracker
            CostTracker.record(model, tokens, provider="alibaba")
            return [item["embedding"] for item in data["data"]]

    async def rerank(
        self, query: str, documents: list[str], top_n: int = 10
    ) -> list[dict[str, Any]]:
        model = self.config.enabled_models.get("rerank", "qwen3-rerank")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{DASHSCOPE_BASE}/api/v1/services/rerank/text-rerank/text-rerank",
                json={
                    "model": model,
                    "input": {"query": query, "documents": documents},
                    "parameters": {"top_n": top_n, "return_documents": True},
                },
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Record token usage
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", len(query) // 4 + sum(len(d) for d in documents) // 4)
            from backend.services.cost_tracker import CostTracker
            CostTracker.record(model, tokens, provider="alibaba")
            return [
                {"index": r["index"], "score": r["relevance_score"],
                 "text": r.get("document", {}).get("text", "")}
                for r in data["output"]["results"]
            ]
