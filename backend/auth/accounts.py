"""User account management - username/password + API key (PostgreSQL Driven)."""
import hashlib, secrets, asyncio
from typing import Optional

_REPO = None

def init_accounts(repo):
    global _REPO
    _REPO = repo

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

async def register(team_id: str, username: str, password: str, role: str = "user", email: str = None) -> dict:
    if not _REPO: raise RuntimeError("Accounts system not initialized")
    
    # Check if username or email already exists
    existing = await _REPO.get_account(username)
    if existing:
        raise ValueError("用户名或邮箱已存在")
    
    if email:
        existing_email = await _REPO.get_account_by_email(email)
        if existing_email:
            raise ValueError("该邮箱已被注册")
    
    token = "mos_" + secrets.token_hex(16)
    hashed = hash_password(password)
    
    await _REPO.insert_account(
        username=username,
        team_id=team_id,
        password_hash=hashed,
        api_key=token,
        role=role,
        email=email,
        is_verified=False
    )
    
    if email:
        # Mock Email Sending
        code = secrets.token_hex(3).upper()
        print(f"\n[MOCK EMAIL] To: {email} | Content: Your verification code is {code}\n")
        
    return {"username": username, "email": email, "api_key": token, "team_id": team_id, "role": role}

async def login(username_or_email: str, password: str) -> dict:
    if not _REPO: raise RuntimeError("Accounts system not initialized")
    
    user = await _REPO.get_account(username_or_email)
    if not user:
        # Try lookup by email if username not found
        if "@" in username_or_email:
            user = await _REPO.get_account_by_email(username_or_email)
    if not user:
        raise ValueError("账户不存在或密码错误")
    
    if user.get("suspended"):
        raise ValueError("账户已被禁用，请联系管理员")
    
    if not verify_password(password, user["password_hash"]):
        raise ValueError("密码输入错误")
    
    return {
        "username": user["username"], 
        "api_key": user["api_key"], 
        "team_id": user["team_id"], 
        "role": user["role"]
    }

async def list_users() -> list[dict]:
    if not _REPO: return []
    users = await _REPO.list_accounts()
    result = []
    for u in users:
        result.append({
            "username": u["username"],
            "team_id": u["team_id"],
            "role": u["role"],
            "created": u["created_at"].isoformat() if hasattr(u["created_at"], "isoformat") else (u["created_at"] or ""),
            "api_key_prefix": u["api_key"][:12] + "...",
            "status": "revoked" if u["revoked"] else ("suspended" if u["suspended"] else "active")
        })
    return result

async def revoke_user(username: str) -> bool:
    if not _REPO: return False
    new_token = "REVOKED_" + secrets.token_hex(8)
    return await _REPO.update_account_status(username, revoked=True, api_key=new_token)

async def suspend_user(username: str) -> bool:
    if not _REPO: return False
    return await _REPO.update_account_status(username, suspended=True)

async def activate_user(username: str) -> bool:
    if not _REPO: return False
    return await _REPO.update_account_status(username, revoked=False, suspended=False)

async def delete_user(username: str) -> bool:
    if not _REPO: return False
    return await _REPO.delete_account(username)
