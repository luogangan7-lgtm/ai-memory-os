#!/usr/bin/env python3
"""AI Memory OS - API Performance Benchmark Test"""
import time
import httpx
import asyncio
import sys

BASE_URL = "http://localhost:8003"

BENCHMARKS = {
    "健康检查":     150,     # /health
    "记忆搜索":     1500,    # /memory/search (including vector retrieval)
    "记忆写入":     500,    # /memory/remember
    "分类统计":     400,    # /memory/categories
}

async def measure(name: str, coro):
    start = time.perf_counter()
    resp = await coro
    elapsed = (time.perf_counter() - start) * 1000
    status = "✅" if elapsed < BENCHMARKS[name] else "❌"
    print(f"{status} {name}: {elapsed:.0f}ms (基准: {BENCHMARKS[name]}ms, HTTP {resp.status_code})")
    return elapsed < BENCHMARKS[name]

async def run_benchmarks():
    print("🚀 Starting API Performance Benchmarks...")
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Register a temporary user to perform authenticated queries
        username = f"perf_tester_{int(time.time())}"
        try:
            reg_resp = await client.post(
                f"{BASE_URL}/admin/auth/register",
                json={"username": username, "password": "perfpass123", "team_id": "perfteam", "agent_id": "perf_agent"}
            )
            if reg_resp.status_code != 200:
                print(f"❌ User registration failed with status {reg_resp.status_code}. Make sure the server is running on port 8003.")
                return False
            token = reg_resp.json().get("api_key", "")
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}. Start server first: python3 run.py")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        results = []

        # 1. Health check
        results.append(await measure("健康检查",
            client.get(f"{BASE_URL}/health")))

        # 2. Write a memory first
        results.append(await measure("记忆写入",
            client.post(f"{BASE_URL}/memory/remember",
                json={"title": "Perf Test Memory", "content": "This is a performance test memory.", "category": "Testing"},
                headers=headers)))

        # Wait a brief moment for database sync
        await asyncio.sleep(1)

        # 3. Search memory
        results.append(await measure("记忆搜索",
            client.post(f"{BASE_URL}/memory/search",
                json={"query": "performance test", "top_k": 3},
                headers=headers)))

        # 4. Categories list
        results.append(await measure("分类统计",
            client.get(f"{BASE_URL}/memory/categories", headers=headers)))

        passed = sum(results)
        print(f"\n性能测试：{passed}/{len(results)} 通过")
        return passed == len(results)

if __name__ == "__main__":
    ok = asyncio.run(run_benchmarks())
    sys.exit(0 if ok else 1)
