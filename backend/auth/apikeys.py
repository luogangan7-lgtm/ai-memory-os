# AI Memory OS - API Key Management (DB Driven)
from __future__ import annotations
import secrets, hashlib
from typing import Optional

_REPO = None

def init_keys(repo):
    global _REPO
    _REPO = repo

class Role:
    ADMIN = "admin"
    USER = "user"
    READER = "reader"

async def validate_key(token: str) -> Optional[dict]:
    if not _REPO: return None
    
    # Check accounts table for API Key
    info = await _REPO.get_account_by_token(token)
    if info:
        if info.get("suspended") or info.get("revoked"):
            return None
        return {
            "team_id": info.get("team_id", "default"),
            "role": info.get("role", "user"),
            "agent_id": info.get("agent_id") or info.get("username"),
            "username": info.get("username")
        }
    
    # Fallback: Support authenticating directly via valid JWT access tokens (e.g. from user app web UI login)
    try:
        from jose import jwt
        from backend.services.config import settings
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        team_id = payload.get("team_id", "default")
        return {
            "team_id": team_id,
            "role": payload.get("role", "user"),
            "agent_id": "mcp-agent",
            "username": team_id
        }
    except Exception:
        pass
        
    return None

async def revoke_key(token: str) -> bool:
    if not _REPO: return False
    # To revoke, we just find the account by token and mark it revoked
    account = await _REPO.get_account_by_token(token)
    if account:
        from backend.auth.accounts import revoke_user
        return await revoke_user(account["username"])
    return False

async def list_keys(team_id: str = None) -> list[dict]:
    if not _REPO: return []
    accounts = await _REPO.list_accounts()
    result = []
    for u in accounts:
        if team_id and u["team_id"] != team_id: continue
        result.append({
            "token": u["api_key"][:12] + "...",
            "team_id": u["team_id"],
            "role": u["role"],
            "created": u["created_at"].isoformat() if u["created_at"] else ""
        })
    return result
