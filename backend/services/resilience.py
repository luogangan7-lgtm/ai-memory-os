# AI Memory OS - Resilience: retry, circuit breaker
from __future__ import annotations
import asyncio, functools, time, logging

log = logging.getLogger(__name__)

def retry(max_retries=3, delay=0.5, backoff=2.0):
    """Async retry decorator with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*a,**kw):
            last_err = None
            for attempt in range(max_retries):
                try: return await func(*a,**kw)
                except Exception as e:
                    last_err = e
                    if attempt < max_retries-1:
                        wait = delay * (backoff**attempt)
                        log.warning(f"Retry {attempt+1}/{max_retries} for {func.__name__}: {e}")
                        await asyncio.sleep(wait)
            raise last_err
        return wrapper
    return decorator

class CircuitBreaker:
    """Fail-fast after consecutive failures."""
    def __init__(self, threshold=5, reset_seconds=30):
        self.threshold=threshold; self.reset=reset_seconds; self.failures=0; self.last_fail=0.0

    def record_failure(self):
        self.failures+=1; self.last_fail=time.time()

    def record_success(self):
        self.failures=0

    @property
    def is_open(self):
        if self.failures>=self.threshold:
            if time.time()-self.last_fail<self.reset: return True
            self.failures=0
        return False
