#!/usr/bin/env python3
import asyncio
import httpx
import os
import sys

PORT = "8003"
port_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".server.port")
if os.path.exists(port_file):
    PORT = open(port_file).read().strip()
BASE = f"http://127.0.0.1:{PORT}"

print(f"Verifying whitelist and plan features on {BASE}...")

# 1. Login as admin/admin to get token
try:
    r = httpx.post(f"{BASE}/admin/auth/login", json={"username": "admin", "password": "admin"}, timeout=10)
    if r.status_code != 200:
        print(f"❌ Failed to login as admin: {r.status_code} - {r.text}")
        sys.exit(1)
    admin_token = r.json().get("token") or r.json().get("api_key")
    if not admin_token:
        print(f"❌ Token not found in login response: {r.json()}")
        sys.exit(1)
    print("✅ Successfully logged in as admin.")
except Exception as e:
    print(f"❌ Login request error: {e}")
    sys.exit(1)

AH = {"Authorization": f"Bearer {admin_token}"}
TEST_USER = "whitelist_test_user"

# 2. Register test user
try:
    r = httpx.post(f"{BASE}/admin/auth/register", json={
        "username": TEST_USER,
        "password": "password123",
        "team_id": "test_whitelist_team",
        "agent_id": "whitelist_tester"
    }, timeout=10)
    if r.status_code in (200, 409):
        print(f"✅ User registration request handled (status {r.status_code}).")
    else:
        print(f"❌ Failed to register test user: {r.status_code} - {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Registration request error: {e}")
    sys.exit(1)

# Helper function to get users list
def get_user_plan_info(username):
    r = httpx.get(f"{BASE}/admin/users", headers=AH, timeout=10)
    if r.status_code != 200:
        print(f"❌ Failed to list users: {r.status_code} - {r.text}")
        sys.exit(1)
    users = r.json().get("users", [])
    for u in users:
        if u["username"] == username:
            return u
    return None

# 3. Test Unauthorized PATCH request
try:
    r = httpx.patch(f"{BASE}/admin/users/{TEST_USER}/plan", json={"plan": "exempt"}, timeout=10)
    if r.status_code in (401, 403):
        print("✅ Unauthorized PATCH request correctly blocked.")
    else:
        print(f"❌ Unauthorized PATCH request not blocked (returned {r.status_code}).")
        sys.exit(1)
except Exception as e:
    print(f"❌ Unauthorized request error: {e}")
    sys.exit(1)

# 4. Test Authorized PATCH request: update plan to exempt
try:
    r = httpx.patch(f"{BASE}/admin/users/{TEST_USER}/plan", headers=AH, json={"plan": "exempt"}, timeout=10)
    if r.status_code == 200:
        print("✅ PATCH request to set plan to 'exempt' succeeded.")
    else:
        print(f"❌ PATCH request to set plan to 'exempt' failed: {r.status_code} - {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ PATCH request error: {e}")
    sys.exit(1)

# 5. Verify plan is 'exempt' in DB
u_info = get_user_plan_info(TEST_USER)
if u_info and u_info["plan"] == "exempt":
    print("✅ Verified: Plan in database is 'exempt'.")
else:
    print(f"❌ Verified: Plan in database is NOT 'exempt' (got {u_info})")
    sys.exit(1)

# 6. Test updating plan to pro
try:
    r = httpx.patch(f"{BASE}/admin/users/{TEST_USER}/plan", headers=AH, json={"plan": "pro"}, timeout=10)
    if r.status_code == 200:
        print("✅ PATCH request to set plan to 'pro' succeeded.")
    else:
        print(f"❌ PATCH request to set plan to 'pro' failed: {r.status_code} - {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ PATCH request error: {e}")
    sys.exit(1)

# 7. Verify plan is 'pro' in DB
u_info = get_user_plan_info(TEST_USER)
if u_info and u_info["plan"] == "pro":
    print("✅ Verified: Plan in database is 'pro'.")
else:
    print(f"❌ Verified: Plan in database is NOT 'pro' (got {u_info})")
    sys.exit(1)

# 8. Increment mcp_call_count to 12 via direct SQL
async def simulate_mcp_calls():
    # Setup paths to import backend modules
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.services.config import settings
    os.environ["DATABASE_URL"] = f"postgresql://{settings.pg_user}:{settings.pg_password}@{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        await conn.execute("UPDATE accounts SET mcp_call_count = 12 WHERE username = $1", TEST_USER)
        print("✅ Direct DB SQL: set mcp_call_count to 12.")
    finally:
        await conn.close()

# Run the async simulated calls
asyncio.run(simulate_mcp_calls())

# 9. Verify mcp_call_count is 12
u_info = get_user_plan_info(TEST_USER)
if u_info and u_info["mcp_call_count"] == 12:
    print("✅ Verified: mcp_call_count is 12 in DB.")
else:
    print(f"❌ Verified: mcp_call_count is NOT 12 (got {u_info})")
    sys.exit(1)

# 10. Execute the reset PATCH request
try:
    r = httpx.patch(f"{BASE}/admin/users/{TEST_USER}/plan", headers=AH, json={"plan": "pro", "reset_mcp_count": True}, timeout=10)
    if r.status_code == 200:
        print("✅ PATCH request to reset MCP call count succeeded.")
    else:
        print(f"❌ PATCH request to reset MCP call count failed: {r.status_code} - {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ PATCH request error: {e}")
    sys.exit(1)

# 11. Verify mcp_call_count is 0 in DB
u_info = get_user_plan_info(TEST_USER)
if u_info and u_info["mcp_call_count"] == 0:
    print("✅ Verified: mcp_call_count has been reset to 0.")
else:
    print(f"❌ Verified: mcp_call_count is NOT 0 (got {u_info})")
    sys.exit(1)

# 12. Cleanup: delete test user
try:
    r = httpx.delete(f"{BASE}/admin/users/{TEST_USER}", headers=AH, timeout=10)
    if r.status_code == 200:
        print("✅ Successfully deleted test user.")
    else:
        print(f"❌ Failed to delete test user: {r.status_code} - {r.text}")
except Exception as e:
    print(f"❌ Delete request error: {e}")

print("🎉 ALL WHITELIST AND PLAN API TESTS PASSED!")
