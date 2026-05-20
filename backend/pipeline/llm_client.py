"""LLM client — calls user's own LLM config. Zero cost to system owner."""
from __future__ import annotations
import httpx

from backend.api.user_providers import _user_llm_configs

_DEFAULT_BASES = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "zhipu": "https://bigmodel.cn/api/paas/v4",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "cohere": "https://api.cohere.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "omlx": "http://host.docker.internal:7749/v1",
}

def get_default_base(provider_name: str) -> str:
    return _DEFAULT_BASES.get(provider_name, "")

async def call_llm(prompt: str, team_id: str = "", engine_type: str = "classifier") -> str | None:
    # 1. Check user's own LLM config first (per-team isolation)
    user_cfg = _user_llm_configs.get(team_id, {})
    if user_cfg.get("api_key") and user_cfg.get("base_url"):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    user_cfg["base_url"].rstrip("/") + "/chat/completions",
                    json={"model": user_cfg.get("model", "deepseek-chat"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                    headers={"Authorization": f"Bearer {user_cfg['api_key']}"})
                return resp.json()["choices"][0]["message"]["content"]
        except: pass

    # 2. Fallback to admin ModelRegistry (system default)
    """Call user's configured LLM. Returns None if user has no key."""
    from backend.manager.registry import ModelRegistry
    reg = ModelRegistry.get_instance()
    
    # Get user's engine config
    engine_data = reg.load_llm_engine_config()
    cfg = engine_data.get(engine_type) or engine_data.get("reflection") or engine_data.get("classifier") or {}
    provider_name = cfg.get("provider", "")
    model_name = cfg.get("model", "")
    
    if not provider_name or provider_name not in reg.configs:
        return None  # User hasn't configured LLM - return silently
    
    provider = reg.configs[provider_name]
    if not provider.api_key:
        return None  # User hasn't set API key
    
    base_url = provider.api_base or ""
    if not base_url:
        base_url = get_default_base(provider_name)
    model = model_name or provider.enabled_models.get("llm", "")
    if not model:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                headers={"Authorization": f"Bearer {provider.api_key}"}
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None  # LLM call failed - silent skip, don't break the pipeline
