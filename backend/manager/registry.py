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


CONFIG_DIR = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "memory-os"
CONFIG_FILE = CONFIG_DIR / "providers.json"

DEFAULT_PROVIDER_CONFIGS: dict[str, dict] = {
    "alibaba": {
        "provider_type": "alibaba",
        "api_key": "",
        "api_base": "",
        "enabled_capabilities": [],
        "enabled_models": {},
    },
    "openai": {
        "provider_type": "openai",
        "api_key": "",
        "api_base": "",
        "enabled_capabilities": [],
        "enabled_models": {},
    },
    "zhipu": {
        "provider_type": "zhipu",
        "api_key": "",
        "api_base": "",
        "enabled_capabilities": [],
        "enabled_models": {},
    },
}

from backend.providers.openai import OpenAIProvider
from backend.providers.zhipu import ZhipuProvider

PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "alibaba": AlibabaProvider,
    "openai": OpenAIProvider,
    "zhipu": ZhipuProvider,
}



class ModelRegistry:
    """Singleton registry for all model providers."""

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

    async def validate_provider(self, provider_type: str) -> bool:
        provider = await self._get_provider(provider_type)
        return await provider.validate() if provider else False

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
        for ptype in ["alibaba", "openai", "zhipu"]:
            cfg = self.configs.get(ptype)
            if cfg and "embedding" in cfg.enabled_models:
                p = await self._get_provider(ptype)
                if p:
                    return await p.embed(texts)
        raise RuntimeError("No embedding provider configured")

    async def embed_single(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


    async def rerank(self, query: str, docs: list[str], top_n: int = 10) -> list[dict]:
        for ptype in ["alibaba", "openai", "zhipu"]:
            cfg = self.configs.get(ptype)
            if cfg and "rerank" in cfg.enabled_models:
                p = await self._get_provider(ptype)
                if p:
                    return await p.rerank(query, docs, top_n)
        raise RuntimeError("No rerank provider configured")

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
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            info["ollama_installed"] = result.returncode == 0
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

