# AI Memory OS - Rate Limiter
from __future__ import annotations
import time, asyncio
from collections import defaultdict
from fastapi.responses import JSONResponse

class PerMinuteRateLimiter:
    def __init__(self):
        self._windows = defaultdict(list)

    async def check(self, key: str, max_per_minute: int):
        now = time.time()
        window = self._windows[key]
        # Keep requests within last 60 seconds
        window[:] = [t for t in window if now - t < 60.0]
        if len(window) >= max_per_minute:
            raise RuntimeError("Rate limit exceeded")
        window.append(now)

_per_minute_limiter = PerMinuteRateLimiter()

async def rate_limit_middleware(request, call_next):
    # Allow local admin access without strict limit or let it follow general rules
    # We can read limits dynamically from the system configuration
    from backend.services.config import load_system_config
    try:
        sys_config = load_system_config()
        sec_cfg = sys_config.get("security", {})
        limit_write = sec_cfg.get("rate_write", 60)
        limit_read = sec_cfg.get("rate_read", 120)
    except Exception:
        limit_write = 60
        limit_read = 120

    is_write = request.method in ("POST", "PUT", "DELETE", "PATCH")
    limit = limit_write if is_write else limit_read
    
    host = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
    key = f"{host}:{'write' if is_write else 'read'}"
    
    try:
        await _per_minute_limiter.check(key, limit)
    except RuntimeError:
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        
    return await call_next(request)
