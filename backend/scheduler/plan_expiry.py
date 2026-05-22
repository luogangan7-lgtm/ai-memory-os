"""Pro plan expiration — daily scan reverts expired pro → free."""
import asyncio

async def revert_expired_plans():
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        await conn.execute(
            "UPDATE accounts SET plan='free', plan_expires_at=NULL "
            "WHERE plan='pro' AND plan_expires_at IS NOT NULL AND plan_expires_at < NOW()")
        await conn.close()
        print("[expiry] Plan expiration check complete")
    except Exception as e:
        print(f"[expiry] Error: {e}")

async def start_plan_expiry_scheduler():
    while True:
        await asyncio.sleep(3600)  # Every hour
        try:
            await revert_expired_plans()
        except Exception as e:
            print(f"[expiry] Scheduler error: {e}")
