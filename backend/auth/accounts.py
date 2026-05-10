"""User account management - username/password + API key."""

import json, os, hashlib, secrets
from pathlib import Path

ACCOUNTS_FILE = Path(os.environ.get("MEMORY_OS_ACCOUNTS", str(Path.home() / ".codex" / "memory-os" / "accounts.json")))

def _load():
    ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ACCOUNTS_FILE.exists():
        return json.loads(ACCOUNTS_FILE.read_text())
    return {}

def _save(data):
    ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACCOUNTS_FILE.write_text(json.dumps(data, indent=2))

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${h}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex() == h
    except:
        return False

def register(team_id: str, username: str, password: str, role: str = "user") -> dict:
    accounts = _load()
    if username in accounts:
        raise ValueError("用户名已存在")
    token = "mos_" + secrets.token_hex(16)
    accounts[username] = {
        "team_id": team_id,
        "password": hash_password(password),
        "api_key": token,
        "role": role,
        "agent_id": username,
        "created": __import__("datetime").datetime.now().isoformat(),
    }
    _save(accounts)
    return {"username": username, "api_key": token, "team_id": team_id, "role": role}

def login(username: str, password: str) -> dict | None:
    accounts = _load()
    user = accounts.get(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return {"username": username, "api_key": user["api_key"], "team_id": user["team_id"], "role": user["role"]}

def list_users() -> list[dict]:
    """Return all users (without passwords)."""
    accounts = _load()
    result = []
    for username, info in accounts.items():
        result.append({
            "username": username,
            "team_id": info.get("team_id", "default"),
            "role": info.get("role", "user"),
            "created": info.get("created", ""),
            "api_key_prefix": info.get("api_key", "")[:12] + "...",
        })
    return result

def revoke_user(username: str) -> bool:
    """Revoke a user: rotate their API key so it's invalid, mark as revoked."""
    accounts = _load()
    if username not in accounts:
        return False
    # Rotate the key to invalidate it, mark as revoked
    accounts[username]["api_key"] = "REVOKED_" + secrets.token_hex(8)
    accounts[username]["revoked"] = True
    _save(accounts)
    return True

def delete_user(username: str) -> bool:
    """Completely remove a user account."""
    accounts = _load()
    if username not in accounts:
        return False
    del accounts[username]
    _save(accounts)
    return True
