# AI Memory OS — DeepSeek Provider
# DeepSeek uses OpenAI-compatible API. Supports V3 (chat) and R1 (reasoner).

import httpx
from typing import Any
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo

DEEPSEEK_BASE = "https://api.deepseek.com/v1"

# Static model catalog with rich metadata
DEEPSEEK_CATALOG = [
    ModelInfo(
        id="deepseek-v4-flash",
        display_name="DeepSeek V4 (Chat)",
        provider="deepseek",
        capabilities=[ModelCapability.CHAT],
        context_window=65536,
        description="DeepSeek V4 通用旗舰模型，综合推理能力强，成本极低",
        pricing_per_1m_tokens=1.0,
    ),
    ModelInfo(
        id="deepseek-v4-pro",
        display_name="DeepSeek V4 Reasoner",
        provider="deepseek",
        capabilities=[ModelCapability.CHAT],
        context_window=65536,
        description="V4 满血推理模型，数学/代码/逻辑链推理全球顶级，适合复杂分析任务",
        pricing_per_1m_tokens=4.0,
    ),
    ModelInfo(
        id="deepseek-chat",
        display_name="DeepSeek V3.2 (Chat)",
        provider="deepseek",
        capabilities=[ModelCapability.CHAT],
        context_window=128000,
        description="当前主力通用对话模型",
        pricing_per_1m_tokens=1.99,
    ),
    ModelInfo(
        id="deepseek-reasoner",
        display_name="DeepSeek R1 (Reasoner)",
        provider="deepseek",
        capabilities=[ModelCapability.CHAT],
        context_window=64000,
        description="满血推理大模型",
        pricing_per_1m_tokens=4.0,
    ),
]


class DeepSeekProvider(BaseProvider):
    provider_name = "deepseek"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "API Key 为空"}
        try:
            base = self.config.api_base or DEEPSEEK_BASE
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{base}/chat/completions",
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    },
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    return {"valid": True}
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                return {"valid": False, "error": f"HTTP {resp.status_code}: {err_msg[:100]}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def discover_models(self) -> list[ModelInfo]:
        return DEEPSEEK_CATALOG

    async def chat(self, messages: list[dict], **kwargs) -> str:
        base = self.config.api_base or DEEPSEEK_BASE
        model = self.config.enabled_models.get("llm", "deepseek-chat")
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
                CostTracker.record(model, tokens, provider="deepseek")
            return data["choices"][0]["message"]["content"]
