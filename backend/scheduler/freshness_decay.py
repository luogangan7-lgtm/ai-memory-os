"""Freshness decay scheduler — gradually reduce freshness of stale memories."""
import asyncio
import math

DECAY_FACTOR = 0.9771599684342459  # 30-day half-life

async def run_freshness_decay():
    """Daily: apply exponential decay to memories untouched for 7+ days."""
    try:
        from backend.services.config import load_system_config
        sys_config = load_system_config()
        decay_rate = sys_config.get("reflection", {}).get("decay_rate", 0.05)
        decay_factor = 1.0 - decay_rate
    except Exception:
        decay_factor = DECAY_FACTOR

    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        await conn.execute(
            "UPDATE memories SET freshness = GREATEST(freshness * $1, 0.01), "
            "updated_at = NOW() WHERE updated_at < NOW() - INTERVAL '7 days' AND freshness > 0.01",
            decay_factor)
        await conn.close()
        print(f"[decay] Freshness decay applied (factor: {decay_factor})")
    except Exception as e:
        print(f"[decay] Error: {e}")

async def start_decay_scheduler():
    while True:
        await asyncio.sleep(24 * 3600)
        try: await run_freshness_decay()
        except Exception as e: print(f"[decay] Scheduler error: {e}")
