# AI Memory OS - Rate Limiter
from __future__ import annotations
import time, asyncio
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_per_second=100):
        self.max = max_per_second; self._windows = defaultdict(list)

    async def check(self, key: str):
        now = time.time()
        window = self._windows[key]
        window[:] = [t for t in window if now-t < 1.0]
        if len(window) >= self.max:
            raise RuntimeError("Rate limit exceeded")
        window.append(now)

_global_limiter = RateLimiter(max_per_second=50)

async def rate_limit_middleware(request, call_next):
    key = request.client.host if request.client else "unknown"
    try: await _global_limiter.check(key)
    except RuntimeError: return __import__("fastapi.responses").JSONResponse(status_code=429, content={"detail":"Too many requests"})
    return await call_next(request)
