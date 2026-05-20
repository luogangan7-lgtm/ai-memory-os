# AI Memory OS - Auth Middleware
from __future__ import annotations
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from backend.services.config import settings

security = HTTPBearer(auto_error=False)

def create_access_token(team_id: str, role: str = "user") -> str:
    try:
        from backend.services.config import load_system_config
        sys_config = load_system_config()
        expire_minutes = sys_config.get("security", {}).get("jwt_expire", settings.jwt_expire_minutes)
    except Exception:
        expire_minutes = settings.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return jwt.encode({"sub": team_id, "team_id": team_id, "role": role, "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)

async def get_user_context(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials is None:
        print("get_user_context: credentials is None", flush=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    token = credentials.credentials
    
    # 1. Check API Key / Account
    from backend.auth.apikeys import validate_key
    info = await validate_key(token)
    if info:
        return {
            "team_id": info["team_id"],
            "agent_id": info.get("agent_id", info["team_id"]),
            "role": info.get("role", "user")
        }
        
    # 2. Check JWT (Legacy/Internal)
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        team_id = payload.get("team_id", "default")
        role = payload.get("role", "user")
        return {
            "team_id": team_id,
            # Use team_id as agent_id so users see their own memories (not "system")
            "agent_id": team_id if role != "admin" else "system",
            "role": role
        }
    except JWTError as e:
        print(f"get_user_context: JWT decode failed for token '{token[:15]}...': {e}", flush=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_team(ctx: dict = Depends(get_user_context)) -> str:
    return ctx["team_id"]

async def require_admin(ctx: dict = Depends(get_user_context)) -> dict:
    if ctx.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员权限不足")
    return ctx

async def get_agent_id(ctx: dict = Depends(get_user_context)) -> str:
    return ctx["agent_id"]



class TraceMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID for distributed tracing."""
    async def dispatch(self, request, call_next):
        import uuid
        trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        return response
