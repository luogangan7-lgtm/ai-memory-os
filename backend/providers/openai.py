# AI Memory OS — OpenAI Provider
import httpx
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo

class OpenAIProvider(BaseProvider):
    provider_name = "openai"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "密钥为空"}
        try:
            base = self.config.api_base or "https://api.openai.com/v1"
            # Lightweight: just list models, no billing impact
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            err_msg = str(e)
            print(f"DEBUG: OpenAI Validation Failed: {err_msg}", flush=True)
            return {"valid": False, "error": err_msg}

    async def discover_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="text-embedding-3-small", display_name="Text Embedding 3 Small",
                      provider="openai", capabilities=[ModelCapability.EMBED], embedding_dim=1536),
            ModelInfo(id="text-embedding-3-large", display_name="Text Embedding 3 Large",
                      provider="openai", capabilities=[ModelCapability.EMBED], embedding_dim=3072),
            ModelInfo(id="gpt-4o-mini", display_name="GPT-4o Mini",
                      provider="openai", capabilities=[ModelCapability.CHAT])
        ]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        base = self.config.api_base or "https://api.openai.com/v1"
        model = self.config.enabled_models.get("embedding", "text-embedding-3-small")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base}/embeddings",
                json={"model": model, "input": texts},
                headers={"Authorization": f"Bearer {self.config.api_key}"}
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", sum(len(t) for t in texts) // 4)
            from backend.services.cost_tracker import CostTracker
            CostTracker.record(model, tokens, provider="openai")
            return [i["embedding"] for i in data["data"]]

    async def chat(self, messages: list[dict], **kwargs) -> str:
        base = self.config.api_base or "https://api.openai.com/v1"
        model = self.config.enabled_models.get("llm", "gpt-4o-mini")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                json={"model": model, "messages": messages, **kwargs},
                headers={"Authorization": f"Bearer {self.config.api_key}"}
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            if tokens:
                from backend.services.cost_tracker import CostTracker
                CostTracker.record(model, tokens, provider="openai")
            return data["choices"][0]["message"]["content"]


