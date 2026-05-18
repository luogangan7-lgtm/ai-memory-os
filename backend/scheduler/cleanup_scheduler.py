"""Cleanup scheduler — remove old processed L0 conversations."""
import asyncio
from datetime import datetime, timedelta

RETENTION_DAYS = 30

async def cleanup_old_conversations():
    """Delete L0 records older than RETENTION_DAYS that have been processed."""
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
        await conn.execute(
            "DELETE FROM pipeline_conversations WHERE ended_at IS NOT NULL AND ended_at < $1",
            cutoff.isoformat())
        await conn.close()
        print(f"[cleanup] Old L0 conversations before {cutoff.date()} removed")
    except Exception as e:
        print(f"[cleanup] Error: {e}")

async def start_cleanup_scheduler():
    """Run cleanup daily."""
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            await cleanup_old_conversations()
        except Exception as e:
            print(f"[cleanup] Scheduler error: {e}")
