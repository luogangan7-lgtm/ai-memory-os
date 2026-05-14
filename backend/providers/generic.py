# AI Memory OS — Generic OpenAI-Compatible Provider
# Works with any provider using the OpenAI API format:
# Google Gemini (via OpenAI-compat endpoint), Groq, Together AI,
# Baidu ERNIE, Minimax, 01.ai, local vLLM, LM Studio, etc.

import httpx
from typing import Any
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo


class GenericOpenAIProvider(BaseProvider):
    """
    A universal provider for any OpenAI-compatible API.
    User provides: api_key, api_base, and the system auto-fetches the model list.
    """
    provider_name = "custom"

    async def validate(self) -> dict:
        if not self.config.api_key:
            return {"valid": False, "error": "API Key 为空"}
        if not self.config.api_base:
            return {"valid": False, "error": "Base URL 为空，请填写服务商的 API 地址"}
        
        model = self.config.enabled_models.get("llm", "")
        base = self.config.api_base.rstrip("/")
        
        # Step 1: Check if the model list is accessible
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"{base}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    # Great - list models worked. If we have a model name, also try a chat ping.
                    if model:
                        return await self._test_chat(base, model)
                    return {"valid": True, "warning": "连接成功！但请在引擎调度中填写具体模型名称再测试就纪"}
                elif resp.status_code == 404:
                    # /models not supported - must do a real chat call to truly verify
                    if not model:
                        return {"valid": False, "error": "该服务商不支持模型列表查询，请在'强制指定模型标识符'中填写真实模型名再验证"}
                    return await self._test_chat(base, model)
                else:
                    return {"valid": False, "error": f"HTTP {resp.status_code}: {resp.text[:120]}"}
        except httpx.ConnectError:
            return {"valid": False, "error": f"无法连接到 {base}，请检查地址是否正确（Docker 内不能用 127.0.0.1 访问宏机，请改为 host.docker.internal）"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _test_chat(self, base: str, model: str) -> dict:
        """Send a real minimal chat request to verify the endpoint truly works."""
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"{base}/chat/completions",
                    json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    return {"valid": True}
                body = resp.text[:200]
                return {"valid": False, "error": f"HTTP {resp.status_code}: {body}"}
        except httpx.ConnectError:
            return {"valid": False, "error": f"无法连接到 {base}，请检查地址（Docker 内访问宏机请用 host.docker.internal 而非 127.0.0.1）"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def discover_models(self) -> list[ModelInfo]:
        """Try to fetch model list from the provider's /models endpoint."""
        if not self.config.api_base:
            return []
        try:
            base = self.config.api_base.rstrip("/")
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models_raw = data.get("data", [])
                    return [
                        ModelInfo(
                            id=m.get("id", ""),
                            display_name=m.get("id", ""),
                            provider="custom",
                            capabilities=[ModelCapability.CHAT],
                            description="自定义服务商模型",
                        )
                        for m in models_raw if m.get("id")
                    ]
        except Exception:
            pass
        return []

    async def chat(self, messages: list[dict], stream: bool = False, **kwargs) -> Any:
        base_url = self.config.api_base.rstrip("/")
        model = self.config.enabled_models.get("llm", "default")
        client = httpx.AsyncClient(timeout=60)
        try:
            payload = {"model": model, "messages": messages, "stream": stream, **kwargs}
            if stream:
                async def stream_generator():
                    try:
                        async with client.stream("POST", f"{base_url}/chat/completions",
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
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                resp.raise_for_status()
                await client.aclose()
                return resp.json()
        except Exception:
            await client.aclose()
            raise

    async def embed(self, texts: list[str]) -> list[list[float]]:
        base = self.config.api_base.rstrip("/")
        model = self.config.enabled_models.get("embedding", "")
        if not model:
            raise ValueError("请在服务商配置中指定 Embedding 模型名")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base}/embeddings",
                json={"model": model, "input": texts},
                headers={"Authorization": f"Bearer {self.config.api_key}"}
            )
            resp.raise_for_status()
            data = resp.json()
            return [i["embedding"] for i in data["data"]]
