# AI Memory OS — Model Registry
# Manages providers, model discovery, and environment detection.

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Optional

from backend.providers.alibaba import AlibabaProvider
from backend.providers.base import (
    BaseProvider,
    ModelCapability,
    ModelInfo,
    ProviderConfig,
    ProviderType,
)




from backend.providers.openai import OpenAIProvider
from backend.providers.zhipu import ZhipuProvider
from backend.providers.deepseek import DeepSeekProvider
from backend.providers.anthropic import AnthropicProvider
from backend.providers.moonshot import MoonshotProvider
from backend.providers.generic import GenericOpenAIProvider
from backend.providers.elevenlabs import ElevenLabsProvider
from backend.providers.compat_providers import (
    MiniMaxProvider, DoubaoProvider, BaiduProvider, HunyuanProvider,
    SparkProvider, StepfunProvider, YiProvider, TencentCIProvider
)
from backend.providers.compat_providers import ALL_COMPAT_PROVIDERS
class OllamaLocalProvider(GenericOpenAIProvider):
    provider_name = "ollama"

class OmlxLocalProvider(GenericOpenAIProvider):
    provider_name = "omlx"

CONFIG_DIR = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "memory-os"
CONFIG_FILE = CONFIG_DIR / "providers.json"
ROUTING_FILE = CONFIG_DIR / "routing.json"
ENGINE_CONFIG_FILE = CONFIG_DIR / "llm_engine.json"

DEFAULT_PROVIDER_CONFIGS: dict[str, dict] = {
    "alibaba":   {"provider_type": "alibaba",   "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "openai":    {"provider_type": "openai",     "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "deepseek":  {"provider_type": "deepseek",   "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "anthropic": {"provider_type": "anthropic",  "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "zhipu":     {"provider_type": "zhipu",      "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "moonshot":  {"provider_type": "moonshot",   "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "minimax":   {"provider_type": "minimax",    "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "doubao":    {"provider_type": "doubao",     "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "baidu":     {"provider_type": "baidu",      "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "hunyuan":   {"provider_type": "hunyuan",    "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "spark":     {"provider_type": "spark",      "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "stepfun":   {"provider_type": "stepfun",    "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "yi":        {"provider_type": "yi",         "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
    "google":    {"provider_type": "google",     "api_key": "", "api_base": "https://generativelanguage.googleapis.com/v1beta/openai", "enabled_capabilities": [], "enabled_models": {}},
    "cohere":    {"provider_type": "cohere",     "api_key": "", "api_base": "https://api.cohere.com/v1", "enabled_capabilities": [], "enabled_models": {}},
    "groq":      {"provider_type": "groq",       "api_key": "", "api_base": "https://api.groq.com/openai/v1", "enabled_capabilities": [], "enabled_models": {}},
    "mistral":   {"provider_type": "mistral",    "api_key": "", "api_base": "https://api.mistral.ai/v1", "enabled_capabilities": [], "enabled_models": {}},
    "openrouter":{"provider_type": "openrouter",  "api_key": "", "api_base": "https://openrouter.ai/api/v1", "enabled_capabilities": [], "enabled_models": {}},
    "ollama":    {"provider_type": "ollama",     "api_key": "ollama", "api_base": "http://localhost:11434/v1", "enabled_capabilities": [], "enabled_models": {}},
    "omlx":      {"provider_type": "omlx",       "api_key": "omlx", "api_base": "http://host.docker.internal:7749/v1", "enabled_capabilities": [], "enabled_models": {}},
    "custom":    {"provider_type": "custom",     "api_key": "", "api_base": "", "enabled_capabilities": [], "enabled_models": {}},
}

PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "alibaba":   AlibabaProvider,
    "openai":    OpenAIProvider,
    "zhipu":     ZhipuProvider,
    "deepseek":  DeepSeekProvider,
    "anthropic": AnthropicProvider,
    "moonshot":  MoonshotProvider,
    "google":    GenericOpenAIProvider,
    "cohere":    GenericOpenAIProvider,
    "groq":      GenericOpenAIProvider,
    "mistral":   GenericOpenAIProvider,
    "openrouter":GenericOpenAIProvider,
    "ollama":    OllamaLocalProvider,
    "omlx":      OmlxLocalProvider,
    "custom":    GenericOpenAIProvider,
    "elevenlabs":ElevenLabsProvider,
    **ALL_COMPAT_PROVIDERS,
}




class ModelRegistry:
    """Singleton registry for all model providers."""
    _instance: Optional[ModelRegistry] = None

    @classmethod
    def get_instance(cls) -> ModelRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.configs: dict[str, ProviderConfig] = {}
        self.providers: dict[str, BaseProvider] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        configs = DEFAULT_PROVIDER_CONFIGS.copy()
        if CONFIG_FILE.exists():
            saved = json.loads(CONFIG_FILE.read_text())
            for k, v in saved.items():
                if k in configs:
                    configs[k].update(v)
                else:
                    configs[k] = v
        self.configs = {k: ProviderConfig(**v) for k, v in configs.items()}

    def _save_configs(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            k: {
                "provider_type": v.provider_type,
                "api_key": v.api_key,
                "api_base": v.api_base,
                "enabled_capabilities": [c.value for c in v.enabled_capabilities],
                "enabled_models": v.enabled_models,
            }
            for k, v in self.configs.items()
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    # ── Routing (per-capability cross-provider selection) ──

    def load_routing(self) -> dict:
        """Return current routing: {llm, embedding, rerank} -> {provider, model}"""
        if ROUTING_FILE.exists():
            try:
                return json.loads(ROUTING_FILE.read_text())
            except Exception:
                pass
        return {}

    def save_routing(self, routing: dict) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ROUTING_FILE.write_text(json.dumps(routing, indent=2))

    def recommend_routing(self) -> dict:
        """
        Auto-recommend cheapest connected providers for each capability.
        Only considers providers that have a non-empty api_key.
        Returns recommendation dict with provider, model, price, reason.
        """
        # Static model catalogs with pricing (price per 1M tokens in USD)
        CATALOGS = {
            "deepseek":  [{"model": "deepseek-chat",      "cap": "llm",  "price": 0.27, "name": "DeepSeek V4 (Chat)"},
                          {"model": "deepseek-reasoner",   "cap": "llm",  "price": 0.55, "name": "DeepSeek V4 Reasoner"}],
            "moonshot":  [{"model": "moonshot-v1-8k",     "cap": "llm",  "price": 1.2,  "name": "Kimi v1 (8K)"},
                          {"model": "moonshot-v1-32k",    "cap": "llm",  "price": 2.4,  "name": "Kimi v1 (32K)"},
                          {"model": "moonshot-v1-128k",   "cap": "llm",  "price": 8.0,  "name": "Kimi v1 (128K)"}],
            "zhipu":     [{"model": "glm-4-flash",        "cap": "llm",  "price": 0.14, "name": "GLM-4 Flash"},
                          {"model": "glm-4",              "cap": "llm",  "price": 14.0, "name": "GLM-4"}],
            "openai":    [{"model": "gpt-4o-mini",        "cap": "llm",  "price": 0.15, "name": "GPT-4o Mini"},
                          {"model": "gpt-4o",             "cap": "llm",  "price": 2.50, "name": "GPT-4o"},
                          {"model": "text-embedding-3-small", "cap": "embedding", "price": 0.02, "name": "Text Embedding 3 Small"}],
            "anthropic": [{"model": "claude-haiku-3-5",   "cap": "llm",  "price": 0.25, "name": "Claude Haiku 3.5"},
                          {"model": "claude-sonnet-4-5",  "cap": "llm",  "price": 3.0,  "name": "Claude Sonnet 4.5"},
                          {"model": "claude-opus-4-5",    "cap": "llm",  "price": 15.0, "name": "Claude Opus 4.5"}],
            "alibaba":   [{"model": "qwen-turbo",         "cap": "llm",  "price": 0.3,  "name": "Qwen Turbo"},
                          {"model": "qwen-plus",          "cap": "llm",  "price": 0.8,  "name": "Qwen Plus"},
                          {"model": "text-embedding-v3",  "cap": "embedding", "price": 0.07, "name": "Text Embedding V3"},
                          {"model": "gte-rerank",         "cap": "rerank",    "price": 0.07, "name": "GTE Rerank"}],
        }

        connected = {p for p, cfg in self.configs.items() if cfg.api_key}

        def cheapest(cap: str) -> dict | None:
            candidates = []
            for ptype, models in CATALOGS.items():
                if ptype not in connected:
                    continue
                for m in models:
                    if m["cap"] == cap:
                        candidates.append({"provider": ptype, **m})
            if not candidates:
                return None
            return sorted(candidates, key=lambda x: x["price"])[0]

        llm = cheapest("llm")
        emb = cheapest("embedding")
        rerank = cheapest("rerank")

        result = {}
        if llm:
            result["llm"] = {"provider": llm["provider"], "model": llm["model"],
                             "display": llm["name"], "price": llm["price"],
                             "reason": f"已连通服务商中价格最低的推理模型 (¥{llm['price']}/1M tokens)"}
        if emb:
            result["embedding"] = {"provider": emb["provider"], "model": emb["model"],
                                   "display": emb["name"], "price": emb["price"],
                                   "reason": f"已连通服务商中最优嵌入模型 (¥{emb['price']}/1M tokens)"}
        if rerank:
            result["rerank"] = {"provider": rerank["provider"], "model": rerank["model"],
                                "display": rerank["name"], "price": rerank["price"],
                                "reason": "已连通服务商中最优重排模型"}
        return result



    # ── Provider management ──

    def update_provider(self, provider_type: str, **kwargs) -> ProviderConfig:
        if provider_type not in self.configs:
            self.configs[provider_type] = ProviderConfig(
                provider_type=provider_type,
                api_key="",
                api_base="",
                enabled_capabilities=[],
                enabled_models={},
            )
        cfg = self.configs[provider_type]
        for k, v in kwargs.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        # CRITICAL: Clear the cached provider instance so it's recreated with new config
        if provider_type in self.providers:
            del self.providers[provider_type]
        self._save_configs()
        return cfg


    def delete_provider(self, provider_type: str) -> None:
        if provider_type in self.providers:
            del self.providers[provider_type]
        if provider_type in self.configs:
            del self.configs[provider_type]
        self._save_configs()

    async def validate_provider(self, provider_type: str) -> dict:
        provider = await self._get_provider(provider_type)
        if not provider:
            return {"valid": False, "error": "服务商未初始化"}
        res = await provider.validate()
        
        valid = res.get("valid", False) if isinstance(res, dict) else bool(res)
        error = res.get("error", "") if isinstance(res, dict) else ""
        
        cfg = self.configs.get(provider_type)
        if cfg:
            if valid:
                caps = ["llm"]
                if provider_type in ["alibaba", "openai", "zhipu", "minimax", "doubao", "baidu", "hunyuan", "ollama", "omlx", "custom"]:
                    caps.append("embedding")
                if provider_type in ["alibaba", "custom"]:
                    caps.append("rerank")
                cfg.enabled_capabilities = caps
            else:
                cfg.enabled_capabilities = []
            self._save_configs()
            
        return {"valid": valid, "error": error}

    async def discover_provider_models(self, provider_type: str) -> list[ModelInfo]:
        provider = await self._get_provider(provider_type)
        return await provider.discover_models() if provider else []

    # ── Internal ──

    async def _get_provider(self, provider_type: str) -> Optional[BaseProvider]:
        if provider_type in self.providers:
            return self.providers[provider_type]
        if provider_type not in PROVIDER_CLASSES:
            return None
        if provider_type not in self.configs:
            return None
        cls = PROVIDER_CLASSES[provider_type]
        provider = cls(self.configs[provider_type])
        self.providers[provider_type] = provider
        return provider

    # ── Delegation ──

    async def embed(self, texts: list[str]) -> list[list[float]]:
        for ptype, cfg in self.configs.items():
            if cfg and "embedding" in cfg.enabled_models:
                p = await self._get_provider(ptype)
                if p:
                    return await p.embed(texts)
        raise RuntimeError("No embedding provider configured")

    async def embed_single(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


    async def rerank(self, query: str, docs: list[str], top_n: int = 10) -> list[dict]:
        route = self.load_routing().get("rerank")
        if not route:
            return [{"index": i, "score": 0.0} for i in range(len(docs))]
        provider = await self._get_provider(route["provider"])
        if not provider:
            return [{"index": i, "score": 0.0} for i in range(len(docs))]
        # Ensure the correct model is used
        provider.config.enabled_models["rerank"] = route["model"]
        return await provider.rerank(query, docs, top_n)

    async def chat(self, messages: list[dict], stream: bool = False, **kwargs) -> Any:
        """Forward chat request with dynamic model routing."""
        requested_model = kwargs.get("model")
        target_provider = None
        target_model_id = None
        
        # 1. Try to find a provider that has the requested model enabled
        if requested_model and requested_model != "default":
            for p_type, cfg in self.configs.items():
                # Check if this provider has the model in any of its roles (llm, etc)
                for role, m_id in cfg.enabled_models.items():
                    if m_id == requested_model:
                        target_provider = await self._get_provider(p_type)
                        target_model_id = m_id
                        break
                if target_provider: break
        
        # 2. Fallback to default routing if no specific model matched or requested
        if not target_provider:
            route = self.load_routing().get("llm")
            if not route:
                raise ValueError("未配置逻辑推理引擎 (LLM) 路由且未指定有效模型")
            target_provider = await self._get_provider(route["provider"])
            target_model_id = route["model"]

        if not target_provider:
            raise ValueError("无法找到可用的算力提供商")
            
        # Ensure the provider is using the resolved model
        # (Some providers use the internal 'llm' config key)
        target_provider.config.enabled_models["llm"] = target_model_id
        
        if not hasattr(target_provider, 'chat'):
            raise ValueError(f"服务商 {target_provider.config.provider_type} 不支持对话功能")
            
        return await target_provider.chat(messages, stream=stream, **kwargs)

    async def add_message(self, role: str, content: str, team_id: str = "default", agent_id: str = ""):
        """Centralized method to archive message and trigger ingestion."""
        from backend.api.routes import pg_repo, ingestion
        if not pg_repo: return
        
        # 1. Save to PostgreSQL
        mid = await pg_repo.add_message(team_id, agent_id, role, content)
        
        # 2. Trigger Vector Ingestion for RAG
        if ingestion:
            try:
                await ingestion.ingest(
                    content=content,
                    title=f"{role.capitalize()} Chat Message",
                    category="conversation",
                    importance=0.5,
                    team_id=team_id,
                    agent_id=agent_id,
                    memory_id=mid
                )
            except Exception as e:
                print(f"Failed to ingest chat message: {e}")
        return mid

    # ── Environment detection ──

    @staticmethod
    def detect_environment() -> dict[str, Any]:
        info = {
            "system": platform.system(),
            "python_version": platform.python_version(),
            "cpu_cores": os.cpu_count(),
            "memory_gb": 0,
            "gpus": [],
        }
        try:
            import psutil
            info["memory_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
        except ImportError:
            try:
                import subprocess
                r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
                info["memory_gb"] = round(int(r.stdout.strip()) / 1e9, 1)
            except Exception:
                pass
        try:
            import torch
            info["torch_available"] = True
            info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    info["gpus"].append({
                        "name": torch.cuda.get_device_name(i),
                        "memory_gb": round(torch.cuda.get_device_properties(i).total_mem / 1e9, 1),
                    })
        except ImportError:
            info["torch_available"] = False
        try:
            from backend.providers.ollama_wizard import detect_ollama
            info["ollama_installed"] = detect_ollama().get("installed", False)
        except Exception:
            info["ollama_installed"] = False
        return info
    @staticmethod
    def recommend_models() -> list[dict]:
        """Recommend optimal local models based on system specs."""
        env = ModelRegistry.detect_environment()
        mem_gb = env.get("memory_gb", 0)
        gpus = env.get("gpus", [])
        has_gpu = len(gpus) > 0
        gpu_mem = max((g["memory_gb"] for g in gpus), default=0) if gpus else 0

        recs = []

        # Embedding models
        if has_gpu and gpu_mem >= 6:
            recs.append({"type": "embedding", "model": "BAAI/bge-m3", "dim": 1024,
                         "size": "2.2GB", "reason": "Best quality, multilingual, GPU-accelerated",
                         "install": "pip install sentence-transformers"})
        elif has_gpu and gpu_mem >= 2:
            recs.append({"type": "embedding", "model": "BAAI/bge-small-en-v1.5", "dim": 384,
                         "size": "133MB", "reason": "Fast, lightweight, GPU-accelerated",
                         "install": "pip install sentence-transformers"})
        elif mem_gb >= 4:
            recs.append({"type": "embedding", "model": "BAAI/bge-small-en-v1.5", "dim": 384,
                         "size": "133MB", "reason": "Lightweight, runs on CPU",
                         "install": "pip install sentence-transformers"})
        else:
            recs.append({"type": "embedding", "model": "all-MiniLM-L6-v2", "dim": 384,
                         "size": "80MB", "reason": "Minimal resource usage, CPU-only",
                         "install": "pip install sentence-transformers"})

        # Reranker models
        if has_gpu and gpu_mem >= 4:
            recs.append({"type": "rerank", "model": "BAAI/bge-reranker-v2-m3", "dim": None,
                         "size": "2.2GB", "reason": "Best quality cross-encoder, GPU-accelerated",
                         "install": "pip install sentence-transformers"})
        elif mem_gb >= 8:
            recs.append({"type": "rerank", "model": "BAAI/bge-reranker-base", "dim": None,
                         "size": "1.1GB", "reason": "Good quality, CPU-capable",
                         "install": "pip install sentence-transformers"})
        else:
            recs.append({"type": "rerank", "model": "cloud (qwen3-rerank)", "dim": None,
                         "size": "N/A", "reason": "Insufficient local resources, use cloud API",
                         "install": "Configure via Admin UI"})

        # BM25 status
        from backend.providers.local import get_bm25
        bm25 = get_bm25()
        recs.append({"type": "bm25_sparse", "model": f"auto ({bm25.name if bm25 else 'disabled'})", "dim": None,
                     "size": "N/A", "reason": "Auto-detected best backend for this platform",
                     "install": "pip install fastembed  # or sklearn (built-in)"})

        return recs

    def load_llm_engine_config(self) -> dict:
        """Load specific LLM engine configs (classifier, reflection)."""
        if ENGINE_CONFIG_FILE.exists():
            try:
                return json.loads(ENGINE_CONFIG_FILE.read_text())
            except Exception:
                pass
        return {}

    def save_llm_engine_config(self, config: dict) -> None:
        """Save specific LLM engine configs."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ENGINE_CONFIG_FILE.write_text(json.dumps(config, indent=2))

    async def chat_for_engine(self, engine_name: str, messages: list[dict], **kwargs) -> str:
        """Forward chat request using specific configured engine, or fallback to standard chat."""
        configs = self.load_llm_engine_config()
        cfg = configs.get(engine_name)
        if not cfg or not cfg.get("provider") or not cfg.get("model"):
            # Fallback to default routing
            return await self.chat(messages, **kwargs)
        
        provider_name = cfg["provider"]
        model_name = cfg["model"]
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url")
        
        from backend.utils.crypto import decrypt_key
        if api_key:
            try:
                # API keys are stored encrypted, so decrypt it
                api_key = decrypt_key(api_key)
            except Exception:
                pass # Fallback if already plain
        
        from backend.providers.base import ProviderConfig
        prov_cfg = ProviderConfig(
            provider_type=provider_name,
            api_key=api_key,
            api_base=base_url or "",
            enabled_models={engine_name: model_name},
            enabled_capabilities=["llm"]
        )
        cls = PROVIDER_CLASSES.get(provider_name)
        if not cls:
            # Fallback
            return await self.chat(messages, **kwargs)
        prov = cls(prov_cfg)
        prov.config.enabled_models["llm"] = model_name
        return await prov.chat(messages, **kwargs)

