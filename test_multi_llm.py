#!/usr/bin/env python3
"""
Multi-LLM Pipeline Integration Test
场景1: 单用户录入多个LLM配置，顺序测试每个模型跑管道
场景2: 多用户并发，每人一个LLM配置，随机切换模型跑管道
"""

import asyncio
import httpx
import time
import json
import random
import sys
from datetime import datetime

BASE = "http://localhost:8003"
DB_CONN = "postgresql://memoryos:memoryos@localhost:5432/memory_os"

# ─── 测试用LLM配置 ────────────────────────────────────────────────────────────
LLM_CONFIGS = [
    {
        "label": "阿里云 Qwen",
        "provider_name": "aliyun",
        "model_name": "qwen-plus",
        "api_key": "sk-placeholder-aliyun",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    {
        "label": "DeepSeek 自用",
        "provider_name": "deepseek",
        "model_name": "deepseek-chat",
        "api_key": "sk-placeholder-deepseek-self",
        "base_url": "https://api.deepseek.com/v1",
    },
    {
        "label": "DeepSeek 开发",
        "provider_name": "deepseek",
        "model_name": "deepseek-chat",
        "api_key": "sk-placeholder-deepseek-dev",
        "base_url": "https://api.deepseek.com/v1",
    },
    {
        "label": "DeepSeek 外用",
        "provider_name": "deepseek",
        "model_name": "deepseek-chat",
        "api_key": "sk-placeholder-deepseek-ext",
        "base_url": "https://api.deepseek.com/v1",
    },
    {
        "label": "智谱 GLM",
        "provider_name": "zhipu",
        "model_name": "glm-4-flash",
        "api_key": "zhipu-placeholder-key",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    {
        "label": "MiniMax",
        "provider_name": "minimax",
        "model_name": "MiniMax-M2.5",
        "api_key": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9",  # placeholder - see note
        "base_url": "https://api.minimax.chat/v1",
        "_real_key": "sk-placeholder-minimax",
    },
]

# 修正 minimax 真实key
for cfg in LLM_CONFIGS:
    if "_real_key" in cfg:
        cfg["api_key"] = cfg.pop("_real_key")

TEST_PREFIX = "ts_llm_"   # tenant id prefix，清理时靠它识别

# ─── 结果收集 ─────────────────────────────────────────────────────────────────
results = {
    "scenario1": [],   # 单用户多LLM顺序测试
    "scenario2": [],   # 多用户并发测试
    "cleanup": {},
    "pipeline_monitor": [],
}

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ─── HTTP helpers ─────────────────────────────────────────────────────────────
async def register(client: httpx.AsyncClient, username: str) -> str | None:
    """注册用户，返回 api_key"""
    try:
        r = await client.post(f"{BASE}/admin/auth/register", json={
            "username": username,
            "password": "Tt@12345678",
            "team_id": f"team_{username}",
            "agent_id": f"agent_{username}"
        })
        if r.status_code == 200:
            return r.json().get("api_key")
        log(f"  ✗ 注册 {username} 失败: {r.status_code} {r.text[:100]}")
    except Exception as e:
        log(f"  ✗ 注册异常: {e}")
    return None

async def save_llm(client: httpx.AsyncClient, token: str, cfg: dict) -> bool:
    """保存LLM配置 — 字段名必须与 user_providers.py handler 一致:
    handler 读取 data.get('provider'), data.get('model'), data.get('base_url')
    """
    try:
        r = await client.post(f"{BASE}/api/user/llm",
            json={
                "provider": cfg["provider_name"],   # 注意: 不是 provider_name
                "model":    cfg["model_name"],       # 注意: 不是 model_name
                "api_key":  cfg["api_key"],
                "base_url": cfg["base_url"],         # 注意: 不是 api_base_url
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return r.status_code == 200
    except Exception as e:
        log(f"  ✗ 保存LLM异常: {e}")
        return False

async def test_llm_connection(client: httpx.AsyncClient, token: str, cfg: dict) -> dict:
    """调用 /api/user/llm/test 直接探测连通性"""
    t0 = time.time()
    try:
        r = await client.post(f"{BASE}/api/user/llm/test",
            json={
                "api_key":  cfg["api_key"],
                "base_url": cfg["base_url"],
                "model":    cfg["model_name"],
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        elapsed = round((time.time() - t0) * 1000)
        data = r.json()
        connected = data.get("connected", False)
        return {"label": cfg["label"], "connected": connected,
                "status": data.get("status"), "latency_ms": elapsed,
                "error": data.get("error")}
    except Exception as e:
        elapsed = round((time.time() - t0) * 1000)
        return {"label": cfg["label"], "connected": False, "latency_ms": elapsed, "error": str(e)}

async def store_memory(client: httpx.AsyncClient, token: str, content: str) -> str | None:
    """存一条记忆，返回 memory id"""
    try:
        r = await client.post(f"{BASE}/memory/store",
            json={
                "title": content[:50],
                "content": content,
                "source_type": "human",
                "memory_type": "chat",
                "importance": 0.7,
                "metadata": {"test": True, "test_suite": "multi_llm"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        if r.status_code == 200:
            data = r.json()
            # 响应字段是 'id'（不是 'memory_id'）
            return data.get("id") or data.get("memory_id")
        log(f"    ✗ store_memory 失败: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"    ✗ store_memory 异常: {e}")
    return None

async def get_pipeline_status(client: httpx.AsyncClient, token: str) -> dict:
    """查询管道状态"""
    try:
        r = await client.get(f"{BASE}/api/user/llm/pipeline/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

async def poll_pipeline_done(client: httpx.AsyncClient, token: str, label: str,
                              timeout: int = 120) -> dict:
    """轮询直到 pipeline done 或超时"""
    deadline = time.time() + timeout
    last_status = {}
    while time.time() < deadline:
        st = await get_pipeline_status(client, token)
        last_status = st
        counts = st.get("counts", {})
        processing = counts.get("processing", 0)
        pending    = counts.get("pending", 0)
        done       = counts.get("done", 0)
        failed     = counts.get("failed", 0)

        if processing == 0 and pending == 0:
            if done > 0:
                log(f"  ✅ [{label}] 管道完成: done={done}, failed={failed}")
                return {"success": True, "done": done, "failed": failed, "status": st}
            elif failed > 0:
                log(f"  ⚠️  [{label}] 管道有失败: done={done}, failed={failed}")
                return {"success": False, "done": done, "failed": failed, "status": st}
            else:
                # No jobs at all yet - wait a bit more
                pass

        log(f"  ⏳ [{label}] pending={pending}, processing={processing}, done={done}, failed={failed}")
        await asyncio.sleep(5)

    log(f"  ⏰ [{label}] 轮询超时 ({timeout}s)")
    return {"success": False, "timeout": True, "status": last_status}

# ─── 场景1：单用户顺序测试每个LLM ────────────────────────────────────────────
async def scenario1(client: httpx.AsyncClient):
    log("\n" + "="*60)
    log("🧪 场景1: 单用户多LLM — 顺序测试每个模型跑管道")
    log("="*60)

    username = f"{TEST_PREFIX}s1_main"
    token = await register(client, username)
    if not token:
        log("  ✗ 注册失败，跳过场景1")
        return

    log(f"  ✓ 注册用户 {username}")

    for i, cfg in enumerate(LLM_CONFIGS):
        log(f"\n  [{i+1}/{len(LLM_CONFIGS)}] 测试: {cfg['label']}")

        # 1. 连通性测试
        conn_result = await test_llm_connection(client, token, cfg)
        log(f"    连通性: {'✅' if conn_result['connected'] else '❌'} "
            f"latency={conn_result['latency_ms']}ms "
            f"error={conn_result.get('error','')}")

        # 2. 先保存LLM配置（has_llm必须为True，存记忆才会触发pipeline）
        ok = await save_llm(client, token, cfg)
        log(f"    保存配置: {'✅' if ok else '❌'}")
        if not ok:
            results["scenario1"].append({**conn_result, "pipeline": "skipped"})
            continue

        await asyncio.sleep(1.5)  # 等待配置写入DB生效

        # 3. 存记忆（此时has_llm=True，会自动触发pipeline）
        content = f"我在测试{cfg['label']}模型处理记忆的能力，时间戳{int(time.time())}"
        mem_id = await store_memory(client, token, content)
        log(f"    存记忆: {'✅ ' + mem_id[:8] + '...' if mem_id else '❌'}")

        if not mem_id:
            results["scenario1"].append({**conn_result, "pipeline": "store_failed"})
            continue

        # 4. 等待管道执行
        pipeline_result = await poll_pipeline_done(client, token, cfg['label'], timeout=90)
        results["scenario1"].append({
            **conn_result,
            "pipeline_done": pipeline_result.get("done", 0),
            "pipeline_failed": pipeline_result.get("failed", 0),
            "pipeline_success": pipeline_result.get("success", False),
            "pipeline_timeout": pipeline_result.get("timeout", False),
        })

        await asyncio.sleep(2)

    log(f"\n  ✅ 场景1完成，共 {len(results['scenario1'])} 个LLM测试")

# ─── 场景2：多用户并发 ────────────────────────────────────────────────────────
async def test_one_user(client: httpx.AsyncClient, user_idx: int, cfg: dict):
    """单个并发用户的完整流程"""
    username = f"{TEST_PREFIX}s2_u{user_idx}"
    label = cfg["label"]

    token = await register(client, username)
    if not token:
        return {"user": username, "label": label, "error": "register_failed"}

    log(f"  ✓ 注册 {username} ({label})")

    # 连通性测试
    conn = await test_llm_connection(client, token, cfg)

    # 先保存LLM配置（必须先于存记忆）
    ok = await save_llm(client, token, cfg)
    if not ok:
        return {**conn, "user": username, "pipeline": "save_failed"}

    await asyncio.sleep(random.uniform(1.0, 2.5))  # 等待配置写入DB + 随机延迟模拟真实并发

    # 存记忆（此时has_llm=True，自动触发pipeline）
    content = f"并发用户{user_idx}测试{label}，时间={int(time.time())}"
    mem_id = await store_memory(client, token, content)

    if not mem_id:
        return {**conn, "user": username, "pipeline": "store_failed"}

    await asyncio.sleep(2)  # 等待worker拣起

    # 手动触发一次（备用）
    try:
        await client.post(f"{BASE}/api/user/llm/pipeline/trigger",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10)
    except Exception:
        pass

    # 监控管道
    pipeline_result = await poll_pipeline_done(client, token, f"u{user_idx}/{label}", timeout=120)

    return {
        **conn,
        "user": username,
        "pipeline_done": pipeline_result.get("done", 0),
        "pipeline_failed": pipeline_result.get("failed", 0),
        "pipeline_success": pipeline_result.get("success", False),
        "pipeline_timeout": pipeline_result.get("timeout", False),
    }

async def scenario2(client: httpx.AsyncClient):
    log("\n" + "="*60)
    log("🧪 场景2: 多用户并发 — 6个用户各用一个LLM随机分配管道")
    log("="*60)

    shuffled = LLM_CONFIGS.copy()
    random.shuffle(shuffled)
    log(f"  LLM分配顺序: {[c['label'] for c in shuffled]}")

    tasks = [
        test_one_user(client, i, shuffled[i % len(shuffled)])
        for i in range(len(shuffled))
    ]

    t0 = time.time()
    user_results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = round(time.time() - t0)

    for r in user_results:
        if isinstance(r, Exception):
            results["scenario2"].append({"error": str(r)})
        else:
            results["scenario2"].append(r)

    log(f"\n  ✅ 场景2完成，耗时 {elapsed}s，{len(user_results)} 个并发用户")

# ─── 清理 ─────────────────────────────────────────────────────────────────────
async def cleanup():
    log("\n" + "="*60)
    log("🗑️  清理测试数据")
    log("="*60)

    import asyncpg, uuid as _uuid

    def safe_uuid(s: str) -> _uuid.UUID:
        """Convert string to UUID (deterministic, same as pg_repo.safe_uuid)"""
        try:
            return _uuid.UUID(s)
        except ValueError:
            return _uuid.UUID(bytes=_uuid.uuid5(_uuid.NAMESPACE_DNS, s).bytes)

    try:
        conn = await asyncpg.connect(DB_CONN)
    except Exception as e:
        log(f"  ✗ 连接DB失败: {e}")
        results["cleanup"] = {"error": str(e)}
        return

    try:
        # 找所有测试账户（表名是 accounts，主键是 username）
        users = await conn.fetch(
            "SELECT username, team_id FROM accounts WHERE username LIKE $1",
            f"{TEST_PREFIX}%"
        )
        log(f"  找到 {len(users)} 个测试账户: {[u['username'] for u in users]}")

        usernames = [u["username"] for u in users]
        team_ids  = [u["team_id"]  for u in users]

        if not usernames:
            log("  没有测试账户，跳过清理")
            results["cleanup"] = {"users_deleted": 0}
            return

        # 统计删前数量
        mem_count = await conn.fetchval(
            "SELECT COUNT(*) FROM memories WHERE team_id = ANY($1::text[])", team_ids
        ) or 0
        pq_count = await conn.fetchval(
            "SELECT COUNT(*) FROM pipeline_queue WHERE team_id = ANY($1::text[])", team_ids
        ) or 0
        # user_provider_configs.user_id 是 UUID，需要转换
        uuid_list = [safe_uuid(u) for u in usernames]
        llm_count = await conn.fetchval(
            "SELECT COUNT(*) FROM user_provider_configs WHERE user_id = ANY($1::uuid[])", uuid_list
        ) or 0

        log(f"  待删: memories={mem_count}, pipeline_queue={pq_count}, provider_configs={llm_count}")

        # 级联删除
        await conn.execute(
            "DELETE FROM pipeline_queue WHERE team_id = ANY($1::text[])", team_ids
        )
        await conn.execute(
            "DELETE FROM memories WHERE team_id = ANY($1::text[])", team_ids
        )
        await conn.execute(
            "DELETE FROM user_provider_configs WHERE user_id = ANY($1::uuid[])", uuid_list
        )
        # accounts（含 api_key 内嵌，无单独 api_keys 表）
        await conn.execute(
            "DELETE FROM accounts WHERE username = ANY($1::text[])", usernames
        )

        log(f"  ✅ PostgreSQL 删除完成")

        # Qdrant: 删除向量集合
        async with httpx.AsyncClient(timeout=30) as hc:
            for team_id in team_ids:
                coll = f"memories_{team_id}"
                try:
                    r = await hc.delete(f"http://localhost:6333/collections/{coll}")
                    if r.status_code in (200, 404):
                        log(f"    Qdrant {coll}: {'deleted' if r.status_code==200 else 'not_found'}")
                    else:
                        log(f"    Qdrant {coll}: {r.status_code}")
                except Exception as e:
                    log(f"    Qdrant {coll}: error={e}")

        # Neo4j: 删除测试节点
        try:
            neo4j_available = False
            async with httpx.AsyncClient(timeout=10) as hc:
                r = await hc.get("http://localhost:7474/db/neo4j/tx/commit",
                    auth=("neo4j", "memoryos"))
                neo4j_available = True

            if neo4j_available:
                async with httpx.AsyncClient(timeout=30) as hc:
                    for team_id in team_ids:
                        cypher = f"MATCH (n {{team_id: '{team_id}'}}) DETACH DELETE n"
                        r = await hc.post(
                            "http://localhost:7474/db/neo4j/tx/commit",
                            json={"statements": [{"statement": cypher}]},
                            auth=("neo4j", "memoryos"),
                            headers={"Content-Type": "application/json"}
                        )
                        log(f"    Neo4j {team_id}: {r.status_code}")
        except Exception as e:
            log(f"    Neo4j 清理跳过: {e}")

        results["cleanup"] = {
            "users_deleted": len(usernames),
            "memories_deleted": mem_count,
            "pipeline_jobs_deleted": pq_count,
            "provider_configs_deleted": llm_count,
        }
        log(f"  ✅ 全部清理完成")

    finally:
        await conn.close()

# ─── 打印摘要 ─────────────────────────────────────────────────────────────────
def print_summary():
    log("\n" + "="*60)
    log("📊 测试摘要")
    log("="*60)

    log("\n【场景1：单用户顺序多LLM】")
    for r in results["scenario1"]:
        status = "✅" if r.get("pipeline_success") else ("⏰" if r.get("pipeline_timeout") else "❌")
        log(f"  {status} {r.get('label','?')}: "
            f"连通={'✅' if r.get('connected') else '❌'} "
            f"latency={r.get('latency_ms','?')}ms "
            f"pipeline_done={r.get('pipeline_done','?')} "
            f"failed={r.get('pipeline_failed','?')}")

    log("\n【场景2：多用户并发随机LLM】")
    for r in results["scenario2"]:
        if "error" in r and "connected" not in r:
            log(f"  ❌ {r.get('user','?')}: {r['error']}")
            continue
        status = "✅" if r.get("pipeline_success") else ("⏰" if r.get("pipeline_timeout") else "❌")
        log(f"  {status} {r.get('user','?')} ({r.get('label','?')}): "
            f"连通={'✅' if r.get('connected') else '❌'} "
            f"latency={r.get('latency_ms','?')}ms "
            f"pipeline_done={r.get('pipeline_done','?')} "
            f"failed={r.get('pipeline_failed','?')}")

    log("\n【清理结果】")
    c = results["cleanup"]
    for k, v in c.items():
        log(f"  {k}: {v}")

    return results

# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    log(f"🚀 Multi-LLM Pipeline Test 启动 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    log(f"   目标API: {BASE}")
    log(f"   测试LLM数: {len(LLM_CONFIGS)}")

    async with httpx.AsyncClient(timeout=60) as client:
        # 健康检查
        try:
            r = await client.get(f"{BASE}/health")
            log(f"   健康检查: {r.json()}")
        except Exception as e:
            log(f"   ✗ API不可达: {e}")
            sys.exit(1)

        # 场景1
        await scenario1(client)

        # 场景2
        await scenario2(client)

    # 清理（独立连接）
    await cleanup()

    # 打印摘要并保存JSON
    summary = print_summary()
    out_path = "/tmp/test_multi_llm_result.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    log(f"\n📄 结果已保存: {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
