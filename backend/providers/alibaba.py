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
    "qwen3.6-flash": ModelInfo(
        id="qwen3.6-flash", display_name="Qwen3.6 Flash",
        provider="alibaba", capabilities=[ModelCapability.CHAT],
        context_window=128000, description="通义千问极速版",
        pricing_per_1m_tokens=0.2,
    ),
    "qwen3.6-plus": ModelInfo(
        id="qwen3.6-plus", display_name="Qwen3.6 Plus",
        provider="alibaba", capabilities=[ModelCapability.CHAT],
        context_window=128000, description="通义千问主力版",
        pricing_per_1m_tokens=0.8,
    ),
    "qwen3.6-max-preview": ModelInfo(
        id="qwen3.6-max-preview", display_name="Qwen3.6 Max Preview",
        provider="alibaba", capabilities=[ModelCapability.CHAT],
        context_window=32000, description="通义千问旗舰版",
        pricing_per_1m_tokens=2.5,
    ),
    "qwen3.5-omni-plus": ModelInfo(
        id="qwen3.5-omni-plus", display_name="Qwen3.5 Omni Plus",
        provider="alibaba", capabilities=[ModelCapability.CHAT],
        context_window=32000, description="全能模型",
        pricing_per_1m_tokens=0.5,
    ),
    "qwen-flash": ModelInfo(
        id="qwen-flash", display_name="Qwen Flash",
        provider="alibaba", capabilities=[ModelCapability.CHAT],
        context_window=128000, description="通义千问限流免费版",
        pricing_per_1m_tokens=0.0,
    ),
}


class AlibabaProvider(BaseProvider):
    provider_name = "alibaba"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "密钥为空"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{DASHSCOPE_BASE}/compatible-mode/v1/chat/completions",
                    json={
                        "model": "qwen-plus",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    },
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                if resp.status_code == 200:
                    return {"valid": True}
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                return {"valid": False, "error": f"HTTP {resp.status_code}: {err_msg[:100]}"}
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
            ModelCapability.CHAT: "llm",
        }.get(capability, ""), "")
        if model_id not in ALIBABA_MODELS:
            return False
        return capability in ALIBABA_MODELS[model_id].capabilities

    async def chat(self, messages: list[dict], stream: bool = False, **kwargs) -> Any:
        model = self.config.enabled_models.get("llm", "qwen-plus")
        client = httpx.AsyncClient(timeout=60)
        try:
            payload = {"model": model, "messages": messages, "stream": stream, **kwargs}
            if stream:
                async def stream_generator():
                    try:
                        async with client.stream("POST", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                                               json=payload,
                                               headers={"Authorization": f"Bearer {self.config.api_key}"}) as resp:
                            resp.raise_for_status()
                            async for line in resp.aiter_lines():
                                if line.strip():
                                    yield line + "\n\n"
                    finally:
                        await client.aclose()
                return stream_generator()
            else:
                resp = await client.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                resp.raise_for_status()
                await client.aclose()
                data = resp.json()
                # Record token usage
                usage = data.get("usage", {})
                tokens = usage.get("total_tokens", 0)
                if tokens:
                    from backend.services.cost_tracker import CostTracker
                    CostTracker.record(model, tokens, provider="alibaba")
                from backend.utils.response import clean_llm_response
            return clean_llm_response(data)
        except Exception:
            await client.aclose()
            raise

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
