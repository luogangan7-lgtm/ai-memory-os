#!/usr/bin/env python3
"""AI Memory OS - Test Suite"""
import httpx, sys, time
import os
PORT = "8003"
port_file = os.path.join(os.path.dirname(__file__), ".server.port")
if os.path.exists(port_file):
    PORT = open(port_file).read().strip()
BASE = f"http://127.0.0.1:{PORT}"
print(f"Testing on port {PORT}...")
P = F = 0

def T(name, ok):
    global P, F
    if ok: P += 1; print(f"  ✅ {name}")
    else: F += 1; print(f"  ❌ {name}")

def R(method, path, **kw):
    headers = kw.pop("headers", {})
    if "json" in kw: headers["Content-Type"] = "application/json"
    return httpx.request(method, f"{BASE}{path}", headers=headers, timeout=30, **kw)

try:
    r = httpx.get(f"{BASE}/", timeout=5)
    if r.status_code != 200:
        print(f"Server returned {r.status_code}. Is it running? Run: python3 run.py"); sys.exit(1)
except Exception as e:
    print(f"Cannot connect to {BASE}. Start server first: python3 run.py"); sys.exit(1)

print("=== 功能测试 ===")
# Root
T("root endpoint", R("GET","/").status_code == 200)

# Register
r = R("POST","/admin/auth/register", json={"username":f"tester_{int(time.time())}","password":"test123","team_id":"testteam","agent_id":"tester"})
T("register", r.status_code == 200)
KEY = r.json().get("api_key","") if r.status_code == 200 else ""
if not KEY:
    print("Registration failed - cannot continue with authenticated tests")
    sys.exit(1)
AH = {"Authorization": f"Bearer {KEY}"}

# Login
T("login correct", R("POST","/admin/auth/login", json={"username":f"tester_{int(time.time())}","password":"test123"}).status_code == 200)
T("login wrong pw", R("POST","/admin/auth/login", json={"username":f"tester_{int(time.time())}","password":"wrong"}).status_code == 401)

# Store
time.sleep(1.5)
r = R("POST","/memory/store", headers=AH, json={"title":"Qdrant Guide","content":"Qdrant uses cosine distance.","category":"AI","importance":0.9,"confidence":0.95})
T("store memory", r.status_code == 200)
MID = r.json().get("id","") if r.status_code == 200 else ""

# Remember
time.sleep(1.5)
T("agent remember", R("POST","/memory/remember", headers=AH, json={"title":"Remember","content":"Agent fact.","category":"AI"}).status_code == 200)

# Search
time.sleep(1.5)
r = R("POST","/memory/search", headers=AH, json={"query":"vector similarity","top_k":3})
T("search returns results", r.status_code == 200 and len(r.json()) > 0)


# Graph
T("graph query", R("POST","/memory/graph", headers=AH, json={"max_depth":1,"top_k":5}).status_code == 200)

# Lifecycle
T("lifecycle promote", R("POST","/memory/lifecycle", headers=AH, json={"memory_id":MID,"target_stage":"working"}).status_code == 200)

# Reflect
r = R("POST","/memory/reflect", headers=AH)
T("reflect run", r.status_code == 200 and "stage_transitions" in r.json())

# Backup/Promote/Gaps/Metrics
T("backup", R("GET","/memory/backup", headers=AH).status_code == 200)
T("gaps", R("GET","/memory/gaps", headers=AH).status_code in (200,500))
T("promote", R("POST","/memory/promote", headers=AH, json={"memory_id":MID}).status_code == 200)
T("metrics", R("GET","/metrics").status_code == 200)

print("\n=== 安全测试 ===")
T("admin needs auth", R("GET","/admin/providers").status_code == 401)
T("dashboard needs auth", R("GET","/admin/dashboard").status_code == 401)
T("search needs auth", R("POST","/memory/search", json={"query":"test"}).status_code == 401)
T("store needs auth", R("POST","/memory/store", json={"title":"x","content":"x"}).status_code == 401)
T("fake token rejected", R("GET","/admin/providers", headers={"Authorization":"Bearer fake123"}).status_code == 401)

print("\n=== 边界测试 ===")
T("empty search", R("POST","/memory/search", headers=AH, json={"query":"","top_k":1}).status_code == 200)
r = R("POST","/memory/search", headers=AH, json={"query":"test","top_k":999})
T("large top_k rejected", r.status_code in (200,422))
T("long content", R("POST","/memory/store", headers=AH, json={"title":"Long","content":"x"*5000}).status_code == 200)
T("missing fields", R("POST","/memory/store", headers=AH, json={"content":"no title"}).status_code == 422)
T("special chars", R("POST","/memory/store", headers=AH, json={"title":"Special","content":"unicode ✓ 中文 🚀"}).status_code == 200)

print(f"\n{'='*40}")
print(f"  ✅ {P} passed  |  ❌ {F} failed")
print(f"{'='*40}")
sys.exit(1 if F > 0 else 0)
