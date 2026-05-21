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

async def call_llm(prompt: str, team_id: str = "", engine_type: str = "classifier") -> tuple[str | None, int]:
    """Call LLM and return (content, total_tokens). Returns (None, 0) on failure."""
    is_user = team_id and team_id != "default"

    # Try to load user config if not cached in-memory
    if is_user and team_id not in _user_llm_configs:
        try:
            from backend.api.routes import pg_repo
            if pg_repo:
                cfg = await pg_repo.get_active_user_provider_config(team_id)
                if cfg and cfg.get("api_key"):
                    user_cfg = {
                        "provider": cfg.get("provider_name", ""),
                        "model": cfg.get("model_name", ""),
                        "api_key": cfg.get("api_key", ""),
                        "base_url": cfg.get("api_base_url", ""),
                    }
                    _user_llm_configs[team_id] = user_cfg
                    from backend.memory.pg_repo import safe_uuid
                    _user_llm_configs[str(safe_uuid(team_id))] = user_cfg
        except Exception as e:
            print(f"[llm_client] failed to load user config from db: {e}")

    # 1. Check user's own LLM config first (per-team isolation)
    user_cfg = _user_llm_configs.get(team_id, {})
    api_key = user_cfg.get("api_key", "")
    # Resolve base_url: use explicit value or fall back to provider default
    base_url = user_cfg.get("base_url", "") or ""
    if not base_url:
        provider = (user_cfg.get("provider") or "").lower()
        base_url = _DEFAULT_BASES.get(provider, "")

    if api_key and base_url:
        try:
            async with httpx.AsyncClient(timeout=30)(timeout=30) as client:
                resp = await client.post(
                    base_url.rstrip("/") + "/chat/completions",
                    json={"model": user_cfg.get("model", "deepseek-chat"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                    headers={"Authorization": f"Bearer {api_key}"})
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                
                # Log usage to database
                from backend.api.routes import pg_repo
                if pg_repo and hasattr(pg_repo, 'insert_user_token_usage'):
                    try:
                        usage = data.get("usage", {})
                        p_tok = int(usage.get("prompt_tokens", 0))
                        c_tok = int(usage.get("completion_tokens", 0))
                        t_tok = int(tokens)
                        if p_tok == 0 and c_tok == 0 and t_tok > 0:
                            p_tok = int(t_tok * 0.7)
                            c_tok = t_tok - p_tok
                        await pg_repo.insert_user_token_usage(
                            user_id=team_id,
                            provider_name=user_cfg.get("provider", "custom"),
                            model_name=user_cfg.get("model", "deepseek-chat"),
                            prompt_tokens=p_tok,
                            completion_tokens=c_tok,
                            total_tokens=t_tok
                        )
                    except Exception as e:
                        print(f"[token-log-pipeline] warning: {e}")
                
                return text, int(tokens)
        except Exception as e:
            if is_user:
                raise RuntimeError(f"User LLM call failed for team {team_id}: {e}") from e
            pass
    elif is_user:
        raise ValueError(f"User {team_id} has no active LLM configuration.")

    # 2. Fallback to admin ModelRegistry (system default)
    from backend.manager.registry import ModelRegistry
    reg = ModelRegistry.get_instance()

    engine_data = reg.load_llm_engine_config()
    cfg = engine_data.get(engine_type) or engine_data.get("reflection") or engine_data.get("classifier") or {}
    provider_name = cfg.get("provider", "")
    model_name = cfg.get("model", "")

    if not provider_name or provider_name not in reg.configs:
        return None, 0

    provider = reg.configs[provider_name]
    if not provider.api_key:
        return None, 0

    base_url = provider.api_base or ""
    if not base_url:
        base_url = get_default_base(provider_name)
    model = model_name or provider.enabled_models.get("llm", "")
    if not model:
        return None, 0

    try:
        async with httpx.AsyncClient(timeout=30)(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                headers={"Authorization": f"Bearer {provider.api_key}"}
            )
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            
            # Log usage to database
            from backend.api.routes import pg_repo
            if pg_repo and hasattr(pg_repo, 'insert_user_token_usage'):
                try:
                    usage = data.get("usage", {})
                    p_tok = int(usage.get("prompt_tokens", 0))
                    c_tok = int(usage.get("completion_tokens", 0))
                    t_tok = int(tokens)
                    if p_tok == 0 and c_tok == 0 and t_tok > 0:
                        p_tok = int(t_tok * 0.7)
                        c_tok = t_tok - p_tok
                    await pg_repo.insert_user_token_usage(
                        user_id=team_id,
                        provider_name=provider_name,
                        model_name=model,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        total_tokens=t_tok
                    )
                except Exception as e:
                    print(f"[token-log-fallback] warning: {e}")
                    
            return text, int(tokens)
    except Exception:
        return None, 0

