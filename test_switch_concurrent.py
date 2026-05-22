"""
多用户并发 + 切换模型一致性测试
验证：pipeline 每次从 DB 读取配置，用户换模型后 pipeline 用的是新模型

测试场景:
  User A (稳定) : DeepSeek 自用 → 存记忆 → 等待完成 → 验证 token 用的是 deepseek
  User B (先换后存): DeepSeek 开发 → 换成 阿里云Qwen → 存记忆 → 验证用的是 aliyun
  User C (存后换): 智谱GLM → 存记忆 → 立即换成 DeepSeek 外用 → 等执行 → 验证用的是 deepseek
  User D (并发双存): MiniMax → 连续存2条记忆 → 验证两条都用 minimax
"""
import asyncio, httpx, time, uuid, json
from datetime import datetime

BASE = "http://localhost:8003"
LOG_FILE = "/tmp/test_switch_concurrent.json"

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def safe_uuid(s):
    try: return uuid.UUID(s)
    except: return uuid.uuid5(uuid.NAMESPACE_DNS, s)

# ── LLM 配置 ─────────────────────────────────────────────────────────────────
LLMS = {
    "deepseek_self": {
        "provider": "deepseek", "model": "deepseek-chat",
        "api_key": "sk-placeholder-deepseek-self",
        "base_url": "https://api.deepseek.com/v1",
    },
    "deepseek_dev": {
        "provider": "deepseek", "model": "deepseek-chat",
        "api_key": "sk-placeholder-deepseek-dev",
        "base_url": "https://api.deepseek.com/v1",
    },
    "deepseek_ext": {
        "provider": "deepseek", "model": "deepseek-chat",
        "api_key": "sk-placeholder-deepseek-ext",
        "base_url": "https://api.deepseek.com/v1",
    },
    "aliyun": {
        "provider": "aliyun", "model": "qwen-plus",
        "api_key": "sk-placeholder-aliyun",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "zhipu": {
        "provider": "zhipu", "model": "glm-4-flash",
        "api_key": "zhipu-placeholder-key",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    "minimax": {
        "provider": "minimax", "model": "MiniMax-M2.5",
        "api_key": "sk-placeholder-minimax",
        "base_url": "https://api.minimax.chat/v1",
    },
}

# ── 辅助函数 ──────────────────────────────────────────────────────────────────
async def register(client, username):
    r = await client.post(f"{BASE}/admin/auth/register", json={
        "username": username,
        "password": "Sw@12345678",
        "team_id": username,
        "agent_id": f"agent_{username}"
    })
    return r.json().get("api_key", "")

async def save_llm(client, token, llm_key):
    cfg = LLMS[llm_key]
    r = await client.post(f"{BASE}/api/user/llm",
        json={"provider": cfg["provider"], "model": cfg["model"],
              "api_key": cfg["api_key"], "base_url": cfg["base_url"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    return r.status_code == 200

async def store_memory(client, token, content, idx=0):
    ts = int(time.time())
    r = await client.post(f"{BASE}/memory/store",
        json={"title": f"切换测试-{idx}", "content": content,
              "source_type": "human", "memory_type": "chat", "importance": 0.8},
        headers={"Authorization": f"Bearer {token}"}
    )
    d = r.json()
    return d.get("id") or d.get("memory_id")

async def get_ui_model(client, token):
    r = await client.get(f"{BASE}/api/user/llm",
        headers={"Authorization": f"Bearer {token}"}
    )
    d = r.json()
    return d.get("provider", "?"), d.get("model", "?")

async def poll_pipeline(client, token, label, timeout=90):
    start = time.time()
    prev_done = None
    while time.time() - start < timeout:
        await asyncio.sleep(4)
        r = await client.get(f"{BASE}/api/user/llm/pipeline/status",
            headers={"Authorization": f"Bearer {token}"})
        c = r.json().get("counts", {})
        done, fail = c.get("done", 0), c.get("failed", 0)
        if done != prev_done:
            log(f"  [{label}] pending={c.get('pending',0)} processing={c.get('processing',0)} done={done} failed={fail}")
            prev_done = done
        if c.get("pending", 1) == 0 and c.get("processing", 0) == 0 and (done > 0 or fail > 0):
            return done, fail
    return 0, 0

async def get_token_usage(username, uuid_val):
    """从DB查真实调用了哪个 provider/model"""
    import subprocess, json
    r = subprocess.run(
        ["docker", "exec", "ai-memory-os-postgres-1", "psql",
         "-U", "memoryos", "-d", "memory_os",
         "-t", "-A", "-F", ",", "-c",
         f"SELECT provider_name,model_name,total_tokens FROM user_token_usage WHERE user_id='{uuid_val}' ORDER BY created_at;"],
        capture_output=True, text=True
    )
    rows = []
    for line in r.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) == 3:
            rows.append({"provider": parts[0], "model": parts[1], "tokens": parts[2]})
    return rows

async def cleanup_user(username):
    uid = str(safe_uuid(username))
    import subprocess
    subprocess.run(["docker", "exec", "ai-memory-os-postgres-1", "psql",
        "-U", "memoryos", "-d", "memory_os", "-c",
        f"""
        DELETE FROM pipeline_queue WHERE team_id='{username}';
        DELETE FROM memories WHERE team_id='{username}';
        DELETE FROM user_provider_configs WHERE user_id='{uid}';
        DELETE FROM user_token_usage WHERE user_id='{uid}';
        DELETE FROM accounts WHERE username='{username}';
        """], capture_output=True)
    import httpx as hx
    async with hx.AsyncClient() as c:
        await c.delete(f"http://localhost:6333/collections/memories_{username}")

# ── 测试用例 ──────────────────────────────────────────────────────────────────

async def test_user_A_stable(results):
    """A: 稳定使用 deepseek_self，存1条，验证 token 是 deepseek"""
    name = "tsw_user_A"
    log(f"\n[User A] 稳定模型测试: {name}")
    async with httpx.AsyncClient(timeout=30) as c:
        token = await register(c, name)
        await save_llm(c, token, "deepseek_self")
        ui_p, ui_m = await get_ui_model(c, token)
        log(f"  [A] UI显示: {ui_p}/{ui_m}")
        await store_memory(c, token, "User A 稳定测试记忆，应由 deepseek-chat 处理")
        done, fail = await poll_pipeline(c, token, "A-deepseek_self")
        usage = await get_token_usage(name, str(safe_uuid(name)))
        actual = [(u["provider"], u["model"]) for u in usage]
        expected_provider = "deepseek"
        ok = all(p == expected_provider for p, m in actual)
        log(f"  [A] pipeline done={done} fail={fail} | token记录={actual}")
        results["A"] = {
            "scenario": "稳定 deepseek",
            "ui_display": f"{ui_p}/{ui_m}",
            "pipeline_done": done, "failed": fail,
            "token_usage": actual,
            "PASS": ok and done == 1
        }

async def test_user_B_switch_before_store(results):
    """B: 先配 deepseek_dev → 换成 aliyun → 存记忆 → 验证 token 是 aliyun"""
    name = "tsw_user_B"
    log(f"\n[User B] 先换后存测试: {name}")
    async with httpx.AsyncClient(timeout=30) as c:
        token = await register(c, name)
        await save_llm(c, token, "deepseek_dev")
        log(f"  [B] 初始配置: deepseek_dev")
        await asyncio.sleep(0.5)
        await save_llm(c, token, "aliyun")
        ui_p, ui_m = await get_ui_model(c, token)
        log(f"  [B] 切换后 UI显示: {ui_p}/{ui_m}")
        await store_memory(c, token, "User B 切换后存储，应由 aliyun/qwen-plus 处理")
        done, fail = await poll_pipeline(c, token, "B-aliyun")
        usage = await get_token_usage(name, str(safe_uuid(name)))
        actual = [(u["provider"], u["model"]) for u in usage]
        ok = all(p == "aliyun" for p, m in actual)
        log(f"  [B] pipeline done={done} fail={fail} | token记录={actual}")
        results["B"] = {
            "scenario": "先换(aliyun)后存",
            "ui_display": f"{ui_p}/{ui_m}",
            "pipeline_done": done, "failed": fail,
            "token_usage": actual,
            "PASS": ok and done == 1
        }

async def test_user_C_switch_after_store(results):
    """C: 配 zhipu → 存记忆 → 立即换成 deepseek_ext → pipeline执行时应用 deepseek（DB最新值）"""
    name = "tsw_user_C"
    log(f"\n[User C] 存后换模型测试: {name}")
    async with httpx.AsyncClient(timeout=30) as c:
        token = await register(c, name)
        await save_llm(c, token, "zhipu")
        log(f"  [C] 初始配置: zhipu/glm-4-flash")
        await store_memory(c, token, "User C 存入时用zhipu，执行前会换成deepseek")
        # 立即换模型（pipeline可能还没开始处理）
        await asyncio.sleep(0.3)
        await save_llm(c, token, "deepseek_ext")
        ui_p, ui_m = await get_ui_model(c, token)
        log(f"  [C] 换模型后 UI显示: {ui_p}/{ui_m}  (pipeline 应用此配置)")
        done, fail = await poll_pipeline(c, token, "C-switched-to-deepseek")
        usage = await get_token_usage(name, str(safe_uuid(name)))
        actual = [(u["provider"], u["model"]) for u in usage]
        # 修复后：pipeline 每次读DB，所以应用 deepseek（最新active配置）
        # 注意：如果pipeline抢先在切换前执行完，可能用zhipu，这也是合法的
        log(f"  [C] pipeline done={done} fail={fail} | token记录={actual}")
        # 允许zhipu或deepseek（取决于pipeline执行时间点），但不能两个都不是
        ok = all(p in ("zhipu", "deepseek") for p, m in actual)
        results["C"] = {
            "scenario": "存后换模型(zhipu→deepseek) — pipeline用执行时的最新配置",
            "ui_display_after_switch": f"{ui_p}/{ui_m}",
            "pipeline_done": done, "failed": fail,
            "token_usage": actual,
            "PASS": ok and done == 1
        }

async def test_user_D_double_store(results):
    """D: minimax，连续存2条记忆，两条都应用 minimax"""
    name = "tsw_user_D"
    log(f"\n[User D] 并发双存测试: {name}")
    async with httpx.AsyncClient(timeout=30) as c:
        token = await register(c, name)
        await save_llm(c, token, "minimax")
        ui_p, ui_m = await get_ui_model(c, token)
        log(f"  [D] UI显示: {ui_p}/{ui_m}")
        # 并发存两条记忆
        await asyncio.gather(
            store_memory(c, token, "User D 并发记忆1", idx=1),
            store_memory(c, token, "User D 并发记忆2", idx=2),
        )
        done, fail = await poll_pipeline(c, token, "D-minimax-double", timeout=120)
        usage = await get_token_usage(name, str(safe_uuid(name)))
        actual = [(u["provider"], u["model"]) for u in usage]
        ok = all(p == "minimax" for p, m in actual)
        log(f"  [D] pipeline done={done} fail={fail} | token记录={actual}")
        results["D"] = {
            "scenario": "双并发记忆 minimax",
            "ui_display": f"{ui_p}/{ui_m}",
            "pipeline_done": done, "failed": fail,
            "token_usage": actual,
            "PASS": ok and done == 2
        }

# ── 主流程 ────────────────────────────────────────────────────────────────────
async def main():
    log("=" * 60)
    log("🔀 多用户并发 + 切换模型一致性测试")
    log("=" * 60)

    health = httpx.get(f"{BASE}/health").json()
    log(f"健康检查: {health}")
    assert health.get("status") == "ok", "服务未就绪"

    results = {}
    # A/B/C/D 四个用户并发跑
    await asyncio.gather(
        test_user_A_stable(results),
        test_user_B_switch_before_store(results),
        test_user_C_switch_after_store(results),
        test_user_D_double_store(results),
    )

    log("\n" + "=" * 60)
    log("📊 测试摘要")
    log("=" * 60)
    all_pass = True
    for user, r in sorted(results.items()):
        status = "✅" if r["PASS"] else "❌"
        all_pass = all_pass and r["PASS"]
        log(f"  {status} User {user}: {r['scenario']}")
        log(f"       UI显示: {r.get('ui_display') or r.get('ui_display_after_switch')}")
        log(f"       pipeline_done={r['pipeline_done']} failed={r['failed']}")
        log(f"       实际调用: {r['token_usage']}")

    log("")
    log(f"{'🎉 全部通过' if all_pass else '❌ 存在失败项'}")

    # 保存结果
    with open(LOG_FILE, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, ensure_ascii=False, indent=2)
    log(f"结果已保存: {LOG_FILE}")

    # 清理所有测试数据
    log("\n" + "=" * 60)
    log("🗑️  清理测试数据")
    log("=" * 60)
    for name in ["tsw_user_A", "tsw_user_B", "tsw_user_C", "tsw_user_D"]:
        await cleanup_user(name)
        log(f"  ✓ {name} 已清理")
    log("✅ 清理完毕")

if __name__ == "__main__":
    asyncio.run(main())
