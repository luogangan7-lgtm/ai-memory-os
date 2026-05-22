# AI Memory OS — OpenAI-Compatible Chinese Providers
# All providers here use the OpenAI API format with a different base URL.
# They share the GenericOpenAIProvider logic, only base_url and catalog differ.

import httpx
from backend.providers.base import BaseProvider, ModelCapability, ModelInfo, ProviderConfig


def _make_compat_provider(name: str, base_url: str, catalog: list[ModelInfo]):
    """Factory: creates a named OpenAI-compatible provider class."""

    class CompatProvider(BaseProvider):
        provider_name = name
        _base_url = base_url
        _catalog = catalog

        async def validate(self) -> dict:
            if not self.config.api_key:
                return {"valid": False, "error": "API Key 为空"}
            try:
                effective_base = self.config.api_base or self._base_url
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{effective_base}/models",
                        headers={"Authorization": f"Bearer {self.config.api_key}"}
                    )
                    if resp.status_code in (200, 404):
                        return {"valid": True}
                    return {"valid": False, "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                return {"valid": False, "error": str(e)}

        async def discover_models(self) -> list[ModelInfo]:
            return self._catalog

        async def chat(self, messages: list[dict], **kwargs) -> str:
            base = self.config.api_base or self._base_url
            model = self.config.enabled_models.get("llm", self._catalog[0].id if self._catalog else "")
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
                    CostTracker.record(model, tokens, provider=self.provider_name)
                return data["choices"][0]["message"]["content"]

        async def embed(self, texts: list[str]) -> list[list[float]]:
            base = self.config.api_base or self._base_url
            model = self.config.enabled_models.get("embedding", "")
            if not model:
                raise ValueError(f"{self.provider_name} 未配置 embedding 模型")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{base}/embeddings",
                    json={"model": model, "input": texts},
                    headers={"Authorization": f"Bearer {self.config.api_key}"}
                )
                resp.raise_for_status()
                data = resp.json()
                return [i["embedding"] for i in data["data"]]

    CompatProvider.__name__ = f"{name.capitalize()}Provider"
    return CompatProvider


# ── Tencent CI ──
TencentCIProvider = _make_compat_provider(
    "tencentci",
    "https://ci.tencentcloudapi.com/v1",
    [
        ModelInfo(id="ci-vision-pro", display_name="CI Vision Pro", provider="tencentci",
                  capabilities=[ModelCapability.VISION], context_window=8192,
                  description="腾讯云数据万象视觉大模型", pricing_per_1m_tokens=2.0),
        ModelInfo(id="ci-vision-lite", display_name="CI Vision Lite", provider="tencentci",
                  capabilities=[ModelCapability.VISION], context_window=8192,
                  description="数据万象基础视觉模型", pricing_per_1m_tokens=0.5),
    ]
)

# ── MiniMax (海螺 AI) ──
MiniMaxProvider = _make_compat_provider(
    "minimax",
    "https://api.minimax.chat/v1",
    [
        ModelInfo(id="MiniMax-M2.7", display_name="MiniMax M2.7", provider="minimax",
                  capabilities=[ModelCapability.CHAT], context_window=1000000,
                  description="百万上下文旗舰模型，国内最长上下文之一", pricing_per_1m_tokens=1.0),
        ModelInfo(id="MiniMax-M2.5", display_name="MiniMax M2.5 (Standard)", provider="minimax",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="标准版", pricing_per_1m_tokens=0.5),
        ModelInfo(id="MiniMax-M2.7-highspeed", display_name="MiniMax M2.7 (快速)", provider="minimax",
                  capabilities=[ModelCapability.CHAT], context_window=245760,
                  description="高速版，适合高频任务", pricing_per_1m_tokens=0.1),
        ModelInfo(id="MiniMax-M2", display_name="MiniMax M2", provider="minimax",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="基础版", pricing_per_1m_tokens=0.8),
    ]
)

# ── 字节跳动豆包 (Doubao / Ark) ──
DoubaoProvider = _make_compat_provider(
    "doubao",
    "https://ark.cn-beijing.volces.com/api/v3",
    [
        ModelInfo(id="doubao-seed-2-0-pro-260215", display_name="Doubao Seed 2.0 Pro", provider="doubao",
                  capabilities=[ModelCapability.CHAT], context_window=262144,
                  description="字节最新旗舰，综合能力强，价格低", pricing_per_1m_tokens=0.8),
        ModelInfo(id="doubao-seed-2-0-lite-260215", display_name="Doubao Seed 2.0 Lite", provider="doubao",
                  capabilities=[ModelCapability.CHAT], context_window=262144,
                  description="极速轻量版，适合高频任务", pricing_per_1m_tokens=0.3),
        ModelInfo(id="doubao-1-5-pro-32k", display_name="豆包 1.5 Pro (32K)", provider="doubao",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="字节上一代旗舰", pricing_per_1m_tokens=0.8),
        ModelInfo(id="doubao-1-5-lite-32k", display_name="豆包 1.5 Lite (32K)", provider="doubao",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="极速轻量版", pricing_per_1m_tokens=0.3),
        ModelInfo(id="doubao-embedding", display_name="豆包 Embedding", provider="doubao",
                  capabilities=[ModelCapability.EMBED], context_window=4096,
                  description="字节官方向量模型", pricing_per_1m_tokens=0.1),
    ]
)

# ── 百度文心 (ERNIE / Qianfan) ──
BaiduProvider = _make_compat_provider(
    "baidu",
    "https://qianfan.baidubce.com/v2",
    [
        ModelInfo(id="ernie-4.5-8k", display_name="ERNIE 4.5 (8K)", provider="baidu",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="百度最新旗舰推理模型", pricing_per_1m_tokens=1.6),
        ModelInfo(id="ernie-4.5-turbo-8k", display_name="ERNIE 4.5 Turbo (8K)", provider="baidu",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="高速推理版", pricing_per_1m_tokens=0.8),
        ModelInfo(id="ernie-lite-8k", display_name="ERNIE Lite (8K)", provider="baidu",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="轻量免费版", pricing_per_1m_tokens=0.0),
        ModelInfo(id="bce-embedding-v1", display_name="BCE Embedding", provider="baidu",
                  capabilities=[ModelCapability.EMBED], context_window=2048,
                  description="百度向量嵌入模型", pricing_per_1m_tokens=0.5),
        ModelInfo(id="bce-reranker-base_v1", display_name="BCE Reranker", provider="baidu",
                  capabilities=[ModelCapability.RERANK], context_window=2048,
                  description="百度重排序模型", pricing_per_1m_tokens=0.5),
    ]
)

# ── 腾讯混元 (Hunyuan) ──
HunyuanProvider = _make_compat_provider(
    "hunyuan",
    "https://api.hunyuan.cloud.tencent.com/v1",
    [
        ModelInfo(id="hunyuan-2.0-thinking", display_name="Hunyuan 2.0 (Thinking)", provider="hunyuan",
                  capabilities=[ModelCapability.CHAT], context_window=128000,
                  description="腾讯深度思考模型", pricing_per_1m_tokens=1.0),
        ModelInfo(id="hunyuan-2.0-instruct", display_name="Hunyuan 2.0 (Instruct)", provider="hunyuan",
                  capabilities=[ModelCapability.CHAT], context_window=128000,
                  description="腾讯混元2.0指令微调模型", pricing_per_1m_tokens=1.0),
        ModelInfo(id="hunyuan-turbos-latest", display_name="Hunyuan Turbo S Latest", provider="hunyuan",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="腾讯最新极速旗舰，综合能力强", pricing_per_1m_tokens=0.8),
        ModelInfo(id="hunyuan-turbos", display_name="混元 Turbo S", provider="hunyuan",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="腾讯极速旗舰", pricing_per_1m_tokens=0.8),
        ModelInfo(id="hunyuan-lite", display_name="混元 Lite", provider="hunyuan",
                  capabilities=[ModelCapability.CHAT], context_window=256000,
                  description="免费轻量版，超长上下文", pricing_per_1m_tokens=0.0),
        ModelInfo(id="hunyuan-embedding", display_name="混元 Embedding", provider="hunyuan",
                  capabilities=[ModelCapability.EMBED], context_window=1024,
                  description="腾讯向量嵌入模型", pricing_per_1m_tokens=0.7),
    ]
)

# ── 讯飞星火 (Spark / iFlytek) ──
SparkProvider = _make_compat_provider(
    "spark",
    "https://spark-api-open.xf-yun.com/v1",
    [
        ModelInfo(id="x1", display_name="星火 X1 (推理)", provider="spark",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="讯飞最强推理模型", pricing_per_1m_tokens=4.0),
        ModelInfo(id="4.0Ultra", display_name="星火 4.0 Ultra", provider="spark",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="旗舰综合模型", pricing_per_1m_tokens=4.0),
        ModelInfo(id="generalv3.5", display_name="星火 3.5 (标准)", provider="spark",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="标准版", pricing_per_1m_tokens=1.2),
    ]
)

# ── 阶跃星辰 (Stepfun / Step) ──
StepfunProvider = _make_compat_provider(
    "stepfun",
    "https://api.stepfun.com/v1",
    [
        ModelInfo(id="step-2-16k", display_name="Step 2 (16K)", provider="stepfun",
                  capabilities=[ModelCapability.CHAT], context_window=16384,
                  description="阶跃旗舰推理模型", pricing_per_1m_tokens=3.8),
        ModelInfo(id="step-1-8k", display_name="Step 1 (8K)", provider="stepfun",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="标准版", pricing_per_1m_tokens=1.2),
        ModelInfo(id="step-1-flash", display_name="Step 1 Flash", provider="stepfun",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="高速轻量版", pricing_per_1m_tokens=0.2),
    ]
)

# ── 零一万物 (Yi / 01.ai) ──
YiProvider = _make_compat_provider(
    "yi",
    "https://api.lingyiwanwu.com/v1",
    [
        ModelInfo(id="yi-lightning", display_name="Yi Lightning", provider="yi",
                  capabilities=[ModelCapability.CHAT], context_window=16384,
                  description="极速旗舰，价格极低", pricing_per_1m_tokens=0.14),
        ModelInfo(id="yi-medium", display_name="Yi Medium", provider="yi",
                  capabilities=[ModelCapability.CHAT], context_window=16384,
                  description="标准综合模型", pricing_per_1m_tokens=2.5),
        ModelInfo(id="yi-large", display_name="Yi Large", provider="yi",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="旗舰推理模型", pricing_per_1m_tokens=20.0),
    ]
)

# ── SiliconFlow (硅基流动) ──
SiliconFlowProvider = _make_compat_provider(
    "siliconflow",
    "https://api.siliconflow.cn/v1",
    [
        ModelInfo(id="BAAI/bge-m3", display_name="BGE-M3", provider="siliconflow",
                  capabilities=[ModelCapability.EMBED], context_window=8192,
                  description="SiliconFlow BGE-M3 Embedding", pricing_per_1m_tokens=0.1),
        ModelInfo(id="BAAI/bge-large-zh-v1.5", display_name="BGE-Large-ZH", provider="siliconflow",
                  capabilities=[ModelCapability.EMBED], context_window=512,
                  description="SiliconFlow BGE-Large", pricing_per_1m_tokens=0.1),
        ModelInfo(id="BAAI/bge-reranker-v2-m3", display_name="BGE-Reranker-V2", provider="siliconflow",
                  capabilities=[ModelCapability.RERANK], context_window=8192,
                  description="SiliconFlow BGE-Reranker", pricing_per_1m_tokens=0.2),
        ModelInfo(id="deepseek-ai/DeepSeek-V3", display_name="DeepSeek-V3 (Silicon)", provider="siliconflow",
                  capabilities=[ModelCapability.CHAT], context_window=131072,
                  description="DeepSeek V3 硅基流动托管", pricing_per_1m_tokens=1.0),
        ModelInfo(id="Qwen/Qwen2.5-7B-Instruct", display_name="Qwen2.5 7B", provider="siliconflow",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="开源永久免费", pricing_per_1m_tokens=0.0),
        ModelInfo(id="THUDM/glm-4-9b-chat", display_name="GLM-4 9B", provider="siliconflow",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="开源永久免费", pricing_per_1m_tokens=0.0),
        ModelInfo(id="internlm/internlm2_5-7b-chat", display_name="InternLM 2.5 7B", provider="siliconflow",
                  capabilities=[ModelCapability.CHAT], context_window=32768,
                  description="开源永久免费", pricing_per_1m_tokens=0.0),
        ModelInfo(id="meta-llama/Meta-Llama-3.1-8B-Instruct", display_name="Llama 3.1 8B", provider="siliconflow",
                  capabilities=[ModelCapability.CHAT], context_window=8192,
                  description="开源永久免费", pricing_per_1m_tokens=0.0),
    ]
)

# ── Jina AI ──
JinaProvider = _make_compat_provider(
    "jina",
    "https://api.jina.ai/v1",
    [
        ModelInfo(id="jina-embeddings-v3", display_name="Jina Embeddings V3", provider="jina",
                  capabilities=[ModelCapability.EMBED], context_window=8192,
                  description="Jina AI 最先进的多语言向量模型", pricing_per_1m_tokens=0.02),
        ModelInfo(id="jina-reranker-v2-base-multilingual", display_name="Jina Reranker V2", provider="jina",
                  capabilities=[ModelCapability.RERANK], context_window=8192,
                  description="Jina AI 跨语种重排序模型", pricing_per_1m_tokens=0.02),
    ]
)

# Export all new providers
ALL_COMPAT_PROVIDERS = {
    "minimax": MiniMaxProvider,
    "doubao":  DoubaoProvider,
    "baidu":   BaiduProvider,
    "hunyuan": HunyuanProvider,
    "spark":   SparkProvider,
    "stepfun": StepfunProvider,
    "yi":      YiProvider,
    "tencentci": TencentCIProvider,
    "siliconflow": SiliconFlowProvider,
    "jina": JinaProvider
}
