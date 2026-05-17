"""User Provider API — per-user LLM config for pipeline usage."""
from fastapi import APIRouter, HTTPException, Depends
from backend.auth.middleware import get_current_team

router = APIRouter(prefix="/user/llm", tags=["user_llm"])
_user_llm_configs: dict[str, dict] = {}

@router.get("")
async def get_user_llm(team_id: str = Depends(get_current_team)):
    cfg = _user_llm_configs.get(team_id, {})
    return {"provider": cfg.get("provider", ""), "model": cfg.get("model", ""), "has_key": bool(cfg.get("api_key"))}

@router.post("")
async def save_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    _user_llm_configs[team_id] = {
        "provider": data.get("provider", ""),
        "model": data.get("model", ""),
        "api_key": data.get("api_key", ""),
        "base_url": data.get("base_url", ""),
    }
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
