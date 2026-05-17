# AI Memory OS — Anthropic (Claude) Provider

import httpx
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo

ANTHROPIC_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"

ANTHROPIC_CATALOG = [
    ModelInfo(id="claude-opus-4-7", display_name="Claude Opus 4.7",
              provider="anthropic", capabilities=[ModelCapability.CHAT],
              context_window=1000000, description="Anthropic 最新旗舰推理模型",
              pricing_per_1m_tokens=5.0),
    ModelInfo(id="claude-sonnet-4-6", display_name="Claude Sonnet 4.6",
              provider="anthropic", capabilities=[ModelCapability.CHAT],
              context_window=1000000, description="高性价比，逻辑与代码极佳",
              pricing_per_1m_tokens=3.0),
    ModelInfo(id="claude-haiku-4-5-20251001", display_name="Claude Haiku 4.5",
              provider="anthropic", capabilities=[ModelCapability.CHAT],
              context_window=200000, description="极速轻量版，适合高频低延迟任务",
              pricing_per_1m_tokens=1.0),
]


class AnthropicProvider(BaseProvider):
    provider_name = "anthropic"

    def _headers(self):
        return {
            "x-api-key": self.config.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "API Key 为空"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{ANTHROPIC_BASE}/messages",
                    headers=self._headers(),
                    json={"model": "claude-3-5-sonnet-20241022", "max_tokens": 1,
                          "messages": [{"role": "user", "content": "Hi"}]}
                )
                if resp.status_code in (200, 400):
                    return {"valid": True}
                return {"valid": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def discover_models(self) -> list[ModelInfo]:
        return ANTHROPIC_CATALOG

    async def chat(self, messages: list[dict], **kwargs) -> str:
        model = self.config.enabled_models.get("llm", "claude-sonnet-4-5")
        max_tokens = kwargs.pop("max_tokens", 4096)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{ANTHROPIC_BASE}/messages",
                headers=self._headers(),
                json={"model": model, "max_tokens": max_tokens, "messages": messages}
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            if tokens:
                from backend.services.cost_tracker import CostTracker
                CostTracker.record(model, tokens, provider="anthropic")
            return data["content"][0]["text"]
