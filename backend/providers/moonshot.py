# AI Memory OS — Moonshot (Kimi) Provider (OpenAI-Compatible)

import httpx
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo

MOONSHOT_BASE = "https://api.moonshot.cn/v1"

MOONSHOT_CATALOG = [
    ModelInfo(id="moonshot-v1-8k", display_name="Kimi v1 (8K)",
              provider="moonshot", capabilities=[ModelCapability.CHAT],
              context_window=8192, description="轻量快速，适合短文本任务",
              pricing_per_1m_tokens=1.2),
    ModelInfo(id="moonshot-v1-32k", display_name="Kimi v1 (32K)",
              provider="moonshot", capabilities=[ModelCapability.CHAT],
              context_window=32768, description="标准版，支持长文档分析",
              pricing_per_1m_tokens=2.4),
    ModelInfo(id="moonshot-v1-128k", display_name="Kimi v1 (128K)",
              provider="moonshot", capabilities=[ModelCapability.CHAT],
              context_window=131072, description="超长上下文，支持完整代码库/长报告分析",
              pricing_per_1m_tokens=8.0),
]


class MoonshotProvider(BaseProvider):
    provider_name = "moonshot"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "API Key 为空"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{MOONSHOT_BASE}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def discover_models(self) -> list[ModelInfo]:
        return MOONSHOT_CATALOG

    async def chat(self, messages: list[dict], **kwargs) -> str:
        model = self.config.enabled_models.get("llm", "moonshot-v1-8k")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{MOONSHOT_BASE}/chat/completions",
                json={"model": model, "messages": messages, **kwargs},
                headers={"Authorization": f"Bearer {self.config.api_key}"}
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            if tokens:
                from backend.services.cost_tracker import CostTracker
                CostTracker.record(model, tokens, provider="moonshot")
            return data["choices"][0]["message"]["content"]
