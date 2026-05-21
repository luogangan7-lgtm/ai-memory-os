"""Email verification with Redis-backed code storage."""
import random
import smtplib
import asyncio
from email.mime.text import MIMEText
from backend.services.config import settings

async def _get_redis():
    import redis.asyncio as aioredis
    return aioredis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

def _send_sync(email: str, code: str):
    msg = MIMEText(
        f"您的 Cortex 验证码：{code}\nYour Cortex verification code: {code}\n\n10 分钟内有效 · Valid for 10 minutes",
        "plain", "utf-8")
    msg["Subject"] = f"Cortex 验证码 · Verification Code: {code}"
    msg["From"] = settings.smtp_from
    msg["To"] = email
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as s:
        s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)

async def send_code(email: str) -> bool:
    """Send 6-digit code to email. Store in Redis with 10min TTL."""
    code = str(random.randint(100000, 999999))
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_sync, email, code)
        r = await _get_redis()
        await r.setex(f"verify:{email}", 600, code)
        return True
    except Exception as e:
        print(f"[email] send failed: {e}")
        return False

async def verify_code(email: str, code: str) -> bool:
    """Verify the code matches Redis-stored value."""
    try:
        r = await _get_redis()
        stored = await r.get(f"verify:{email}")
        if stored and stored == code:
            await r.delete(f"verify:{email}")
            return True
        return False
    except Exception:
        return False
