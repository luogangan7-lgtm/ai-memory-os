# AI Memory OS — Zhipu AI GLM Provider
import httpx
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo

class ZhipuProvider(BaseProvider):
    provider_name = "zhipu"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "密钥为空"}
        try:
            # Use lightweight model list check (avoids triggering 429 rate limits)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://open.bigmodel.cn/api/paas/v4/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            err_msg = str(e)
            print(f"DEBUG: Zhipu Validation Failed: {err_msg}", flush=True)
            return {"valid": False, "error": err_msg}

    async def discover_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="embedding-3", display_name="Embedding-3", provider="zhipu",
                      capabilities=[ModelCapability.EMBED], embedding_dim=1024),
            ModelInfo(id="glm-4-flash", display_name="GLM-4 Flash", provider="zhipu",
                      capabilities=[ModelCapability.CHAT])
        ]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.config.enabled_models.get("embedding", "embedding-3")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://open.bigmodel.cn/api/paas/v4/embeddings",
                json={"model": model, "input": texts},
                headers={"Authorization": f"Bearer {self.config.api_key}"}
            )
            resp.raise_for_status()
            data = resp.json()
            # Record actual token usage from API response
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", sum(len(t) for t in texts) // 2)
            from backend.services.cost_tracker import CostTracker
            CostTracker.record(model, tokens, provider="zhipu")
            return [i["embedding"] for i in data["data"]]

