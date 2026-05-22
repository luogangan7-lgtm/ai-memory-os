"""Payment API — USDT TRC20 payment provider."""
from fastapi import APIRouter, HTTPException, Depends, Request
from backend.auth.middleware import get_current_team
import uuid, time, hashlib, json, os, httpx

router = APIRouter(prefix="/api/payment", tags=["payment"])

# Environment config
# Arbitrum One USDT
ARB_WALLET = os.getenv("MEMORY_OS_ARB_WALLET", "0x6094a02583d5d2d4969a42e3685cf9bd3daf3def")
USDT_CONTRACT = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"  # USDT on Arbitrum
ARBISCAN_KEY = os.getenv("ARBISCAN_API_KEY", "")
USDT_MONTHLY = int(os.getenv("MEMORY_OS_USDT_MONTHLY", "4"))
USDT_YEARLY = int(os.getenv("MEMORY_OS_USDT_YEARLY", "40"))
CHAIN_ID = 42161
ARBISCAN_API = "https://api.arbiscan.io/api"

def gen_order_no():
    ts = time.strftime("%Y%m%d%H%M%S")
    rand = ''.join(uuid.uuid4().hex[:6].upper())
    return f"CORTEX_{ts}_{rand}"

@router.get("/subscription")
async def get_subscription(team_id: str = Depends(get_current_team)):
    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            "SELECT plan, plan_expires_at, mcp_call_count FROM accounts WHERE team_id=$1", team_id)
        if not row:
            raise HTTPException(404, "Account not found")
        plan = row["plan"] or "free"
        expires = row["plan_expires_at"]
        is_expired = plan == "pro" and expires and expires < __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        if is_expired:
            plan = "free"
        days_remaining = None
        if plan == "pro" and expires:
            delta = expires - __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            days_remaining = max(0, delta.days)
        return {
            "plan": plan, "plan_expires_at": str(expires) if expires else None,
            "mcp_call_count": row["mcp_call_count"] or 0,
            "mcp_call_limit": 50 if plan == "free" else None,
            "is_expired": is_expired, "days_remaining": days_remaining
        }
    finally:
        await conn.close()

@router.post("/create")
async def create_order(data: dict, team_id: str = Depends(get_current_team)):
    duration = data.get("duration", 1)
    amount = USDT_MONTHLY if duration != 12 else USDT_YEARLY
    out_trade_no = gen_order_no()

    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        await conn.execute(
            "INSERT INTO orders (team_id, out_trade_no, plan, duration_months, total_fee, status) VALUES ($1,$2,$3,$4,$5,'pending')",
            team_id, out_trade_no, "pro", duration, amount)
        return {
            "out_trade_no": out_trade_no,
            "wallet": ARB_WALLET,
            "amount": amount,
            "currency": "USDT (Arbitrum)",
            "network": "Arbitrum One",
            "contract": USDT_CONTRACT,
            "memo": f"请转账 {amount} USDT 到上述地址（Arbitrum 链）。无需备注，系统自动匹配。订单号: {out_trade_no}",
            "expires_in": 600
        }
    finally:
        await conn.close()

@router.get("/query")
async def query_order(out_trade_no: str, team_id: str = Depends(get_current_team)):
    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM orders WHERE out_trade_no=$1 AND team_id=$2", out_trade_no, team_id)
        if not row:
            raise HTTPException(404, "Order not found")
        status = row["status"]
        result = {"status": status, "out_trade_no": out_trade_no}
        if status == "paid":
            acct = await conn.fetchrow("SELECT plan, plan_expires_at FROM accounts WHERE team_id=$1", team_id)
            if acct:
                result["plan"] = acct["plan"]
                result["plan_expires_at"] = str(acct["plan_expires_at"])
        return result
    finally:
        await conn.close()

@router.post("/notify")
async def payment_notify(request: Request):
    """Admin manually confirms payment after checking TRON blockchain."""
    data = await request.json()
    out_trade_no = data.get("out_trade_no", "")
    if not out_trade_no:
        raise HTTPException(400, "Missing out_trade_no")
    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM orders WHERE out_trade_no=$1 AND status='pending'", out_trade_no)
        if not row:
            raise HTTPException(404, "Order not found or already processed")
        team_id = row["team_id"]
        duration = row["duration_months"] or 1
        # Mark order paid
        await conn.execute(
            "UPDATE orders SET status='paid', paid_at=NOW(), payjs_raw=$1 WHERE out_trade_no=$2",
            json.dumps(data), out_trade_no)
        # Upgrade user
        from datetime import datetime, timedelta, timezone
        expires = datetime.now(timezone.utc) + timedelta(days=30 * duration)
        await conn.execute(
            "UPDATE accounts SET plan='pro', plan_expires_at=$1 WHERE team_id=$2",
            expires, team_id)
        return {"status": "ok", "message": f"Upgraded to Pro, expires {expires.date()}"}
    finally:
        await conn.close()


async def poll_arbitrum_payments():
    """Background task: poll Arbitrum for incoming USDT transfers every 60s."""
    import asyncio, httpx
    while True:
        await asyncio.sleep(60)
        try:
            if not ARB_WALLET or not ARBISCAN_KEY:
                continue
            # Check recent USDT transfers to our wallet
            url = (f"{ARBISCAN_API}?module=account&action=tokentx"
                   f"&contractaddress={USDT_CONTRACT}&address={ARB_WALLET}"
                   f"&sort=desc&apikey={ARBISCAN_KEY}")
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                data = resp.json()
                if data.get("status") != "1":
                    continue
                from backend.api.db_helper import get_db_conn
                conn = await get_db_conn()
                try:
                    for tx in data.get("result", [])[:20]:
                        value = int(tx.get("value", "0")) / 1e6  # USDT 6 decimals
                        if value <= 0:
                            continue
                        # Find matching pending order by amount
                        row = await conn.fetchrow(
                            "SELECT * FROM orders WHERE status='pending' AND total_fee=$1 "
                            "ORDER BY created_at DESC LIMIT 1", int(value))
                        if row:
                            await conn.execute(
                                "UPDATE orders SET status='paid', paid_at=NOW() WHERE id=$1",
                                row["id"])
                            from datetime import datetime, timedelta, timezone
                            expires = datetime.now(timezone.utc) + timedelta(days=30 * (row["duration_months"] or 1))
                            await conn.execute(
                                "UPDATE accounts SET plan='pro', plan_expires_at=$1 WHERE team_id=$2",
                                expires, row["team_id"])
                            print(f"[payment] Order {row['out_trade_no']} auto-confirmed via chain")
                finally:
                    await conn.close()
        except Exception as e:
            print(f"[payment] Poll error: {e}")

# Start poller in background
import asyncio as _asyncio
try:
    _asyncio.ensure_future(poll_arbitrum_payments())
except Exception:
    pass
