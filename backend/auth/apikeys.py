# AI Memory OS - API Key Management
from __future__ import annotations
import json, os, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path

KEYS_FILE = Path(os.environ.get("MEMORY_OS_KEYS_FILE", Path.home() / ".codex" / "memory-os" / "api_keys.json"))

class Role:
    ADMIN = "admin"
    USER = "user"
    READER = "reader"

def _load_keys():
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if KEYS_FILE.exists(): return json.loads(KEYS_FILE.read_text())
    return {}

def _save_keys(keys): KEYS_FILE.write_text(json.dumps(keys, indent=2))

def create_api_key(team_id: str, role: str = Role.USER, agent_id: str = "") -> str:
    keys = _load_keys()
    token = "mos_" + hashlib.sha256(os.urandom(32)).hexdigest()[:32]
    keys[token] = {"team_id": team_id, "role": role, "agent_id": agent_id or team_id, "created": datetime.now(timezone.utc).isoformat()}
    _save_keys(keys)
    return token

def validate_key(token: str) -> dict | None:
    # 1. Check dedicated API keys file
    keys = _load_keys()
    if token in keys:
        return keys[token]
    
    # 2. Check accounts file (User-specific API keys)
    from backend.auth.accounts import _load as _load_accounts
    accounts = _load_accounts()
    for username, info in accounts.items():
        if info.get("api_key") == token:
            if info.get("suspended") or info.get("revoked"):
                return None
            return {
                "team_id": info.get("team_id", "default"),
                "role": info.get("role", "user"),
                "agent_id": info.get("agent_id", username),
                "username": username
            }
    
    return None

def revoke_key(token: str) -> bool:
    keys = _load_keys()
    if token in keys:
        del keys[token]; _save_keys(keys); return True
    return False

def list_keys(team_id: str = None) -> list[dict]:
    keys = _load_keys()
    result = []
    for k, v in keys.items():
        if team_id and v.get("team_id") != team_id: continue
        result.append({"token": k[:12]+"...", "team_id": v["team_id"], "role": v["role"], "created": v.get("created","")})
    return result
