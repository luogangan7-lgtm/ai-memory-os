"""User Persona API - read L3 user profiles with Redis cache."""
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.middleware import get_current_team
from backend.api.db_helper import get_db_conn
import json

router = APIRouter(prefix="/persona", tags=["persona"])

PERSONA_TTL = 300  # Redis cache TTL: 5 minutes

# Module-level Redis pool — created once, reused across requests.
# This avoids paying a new connection + ping cost on every invocation.
_redis = None

async def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.Redis(host='redis', port=6379, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception:
        _redis = None
        return None


@router.get("")
@router.get("/")
async def persona_root(current_team: str = Depends(get_current_team)):
    """Redirect to default persona."""
    return await get_persona_default(current_team)

@router.get("/default")
async def get_persona_default(current_team: str = Depends(get_current_team)):
    cache_key = f"persona:{current_team}"

    redis = await _get_redis()
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM user_persona WHERE team_id=$1", current_team)
        if not row:
            default_persona_md = "## 用户画像\n\n系统正在从您的交互记录和存储记忆中构建画像，请继续与 AI 对话以丰富个人档案。"
            await conn.execute(
                """INSERT INTO user_persona (team_id, persona_md, scenario_count, version)
                   VALUES ($1, $2, 0, 1)
                   ON CONFLICT (team_id) DO NOTHING""",
                current_team, default_persona_md)
            row = await conn.fetchrow(
                "SELECT * FROM user_persona WHERE team_id=$1", current_team)

        result = dict(row)

        if redis:
            await redis.setex(cache_key, PERSONA_TTL, json.dumps(result, default=str))

        return result
    finally:
        await conn.close()


@router.get("/{team_id}")
async def get_persona(team_id: str, current_team: str = Depends(get_current_team)):
    if team_id != current_team:
        raise HTTPException(status_code=403, detail="Access denied: unauthorized team context")
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM user_persona WHERE team_id=$1", team_id)
        if not row:
            default_persona_md = "## 用户画像\n\n系统正在从您的交互记录和存储记忆中构建画像，请继续与 AI 对话以丰富个人档案。"
            await conn.execute(
                """INSERT INTO user_persona (team_id, persona_md, scenario_count, version)
                   VALUES ($1, $2, 0, 1)
                   ON CONFLICT (team_id) DO NOTHING""",
                team_id, default_persona_md)
            row = await conn.fetchrow(
                "SELECT * FROM user_persona WHERE team_id=$1", team_id)
        return dict(row)
    finally:
        await conn.close()
