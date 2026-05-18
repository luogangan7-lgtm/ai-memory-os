"""User Provider API — per-user LLM config for pipeline usage."""
from fastapi import APIRouter, HTTPException, Depends
from backend.auth.middleware import get_current_team

router = APIRouter(prefix="/user/llm", tags=["user_llm"])
_user_llm_configs: dict[str, dict] = {}

@router.get("")
async def get_user_llm(team_id: str = Depends(get_current_team)):
    # Try DB first, fallback to memory
    try:
        from backend.api.routes import pg_repo
        if pg_repo:
            cfg = await pg_repo.get_active_user_provider_config(team_id)
            if cfg:
                return {
                    "provider": cfg.get("provider_name", ""),
                    "model": cfg.get("model_name", ""),
                    "has_key": True,
                    "base_url": cfg.get("api_base_url", "")
                }
    except Exception:
        pass
    # Fallback to in-memory
    cfg = _user_llm_configs.get(team_id, {})
    return {"provider": cfg.get("provider", ""), "model": cfg.get("model", ""), "has_key": bool(cfg.get("api_key"))}

@router.post("")
async def save_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    # Save to memory for pipeline access
    _user_llm_configs[team_id] = {
        "provider": data.get("provider", ""),
        "model": data.get("model", ""),
        "api_key": data.get("api_key", ""),
        "base_url": data.get("base_url", ""),
    }
    # Persist to database for proxy gateway
    try:
        from backend.api.routes import pg_repo
        if pg_repo:
            await pg_repo.save_user_provider_config(
                user_id=team_id,
                provider_name=data.get("provider", ""),
                api_key=data.get("api_key", ""),
                api_base_url=data.get("base_url", ""),
                model_name=data.get("model", ""),
                is_active=True
            )
    except Exception as e:
        print(f"save_user_provider_config failed: {e}")
    return {"status": "saved", "team_id": team_id}

@router.post("/test")
async def test_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    import httpx
    key = data.get("api_key", "")
    base = data.get("base_url", "")
    model = data.get("model", "")
    if not key or not base:
        raise HTTPException(400, "API Key and Base URL required")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{base}/chat/completions", json={
                "model": model, "messages": [{"role":"user","content":"hi"}], "max_tokens":5
            }, headers={"Authorization": f"Bearer {key}"})
            return {"connected": r.status_code == 200, "status": r.status_code}
    except Exception as e:
        return {"connected": False, "error": str(e)}
