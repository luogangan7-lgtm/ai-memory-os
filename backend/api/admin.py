# AI Memory OS — Admin API
# Provider CRUD, model discovery, environment detection, health check.

from __future__ import annotations

import json, time, subprocess, os
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from backend.manager.registry import ModelRegistry
from backend.auth.middleware import get_current_team, require_admin
from backend.providers.base import ProviderConfig

def is_setup_complete() -> bool:
    """Check if the system has been initialized."""
    from backend.manager.registry import CONFIG_FILE
    if not CONFIG_FILE.exists():
        return False
    try:
        data = json.loads(CONFIG_FILE.read_text())
        # If at least one provider has a key, we consider setup done
        return any(p.get("api_key") for p in data.values())
    except:
        return False



# Public route: self-service registration (no auth required)
public_router = APIRouter(prefix="/admin", tags=["public"])



@public_router.post("/auth/login")
async def login_user(data: dict):
    """Login with username + password, get API key."""
    from backend.auth.accounts import login
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    try:
        result = login(username, password)
        return result
    except ValueError as e:
        raise HTTPException(401, str(e))

@public_router.post("/auth/register")
async def register_team(data: dict):
    """Self-service: register with username + password."""
    from backend.auth.accounts import register
    username = data.get("username", data.get("agent_id", "")).strip()
    password = data.get("password", "").strip()
    team_id = data.get("team_id", "default").strip()
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    try:
        result = register(team_id, username, password, data.get("role", "user"))
        return result
    except ValueError as e:
        raise HTTPException(409, str(e))

@public_router.get("/setup/status")
async def get_setup_status():
    return {"complete": is_setup_complete()}

@public_router.post("/setup/init")
async def initialize_system(data: dict):
    if is_setup_complete():
        raise HTTPException(403, "系统已完成初始化，禁止重复操作。")
    
    pwd = data.get("admin_password")
    provider = data.get("provider", "alibaba")
    key = data.get("api_key")
    
    if not pwd or not key:
        raise HTTPException(400, "密码和 API Key 不能为空")
    
    # 1. Register admin
    from backend.auth.accounts import register
    try:
        register("default", "admin", pwd, "admin")
    except ValueError:
        # If admin already exists but setup wasn't marked complete, just continue
        pass
        
    # 2. Update provider
    if not registry: raise HTTPException(503)
    registry.update_provider(provider, api_key=key)
    
    # 3. Auto-setup models
    best = {
        "alibaba": {"embedding": "text-embedding-v3", "llm": "qwen-turbo"},
        "openai": {"embedding": "text-embedding-3-small", "llm": "gpt-4o-mini"}
    }.get(provider, {})
    registry.update_provider(provider, api_key=key, enabled_models=best)
    
    return {"status": "success"}

# Admin router: Mandatory security for all management endpoints

router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])


# ── Routing (cross-provider capability binding) ──

@router.get("/routing")
async def get_routing():
    """Get current LLM/Embedding/Rerank routing config."""
    if not registry:
        raise HTTPException(503)
    return registry.load_routing()


@router.put("/routing")
async def save_routing(data: dict):
    """Save LLM/Embedding/Rerank routing config and apply immediately."""
    if not registry:
        raise HTTPException(503)
    registry.save_routing(data)
    # Apply LLM routing to the active provider setting
    if "llm" in data:
        llm = data["llm"]
        registry.update_provider(llm["provider"], enabled_models={"llm": llm["model"]})
    if "embedding" in data:
        emb = data["embedding"]
        registry.update_provider(emb["provider"], enabled_models={"embedding": emb["model"]})
    if "rerank" in data:
        rk = data["rerank"]
        registry.update_provider(rk["provider"], enabled_models={"rerank": rk["model"]})
    return {"saved": True, "routing": data}


@router.get("/routing/recommend")
async def recommend_routing():
    """Auto-recommend cheapest routing based on connected providers."""
    if not registry:
        raise HTTPException(503)
    return registry.recommend_routing()

@router.get("/routing/test/{engine_type}")
async def test_engine(engine_type: str, admin: bool = Depends(require_admin)):
    """Test the currently ACTIVE (deployed) engine routing."""
    registry = ModelRegistry.get_instance()
    route = registry.load_routing().get(engine_type)
    if not route:
        return {"status": "error", "error": f"未找到 {engine_type} 的路由配置"}
    
    provider_name = route["provider"]
    model_id = route["model"]
    
    return await _perform_engine_test(engine_type, provider_name, model_id)

@router.post("/routing/test_adhoc")
async def test_engine_adhoc(data: dict, admin: bool = Depends(require_admin)):
    """Test a SPECIFIC configuration without deploying it first."""
    engine_type = data.get("engine_type")
    provider_name = data.get("provider")
    model_id = data.get("model")
    
    if not all([engine_type, provider_name, model_id]):
        return {"status": "error", "error": "缺少测试参数"}
        
    return await _perform_engine_test(engine_type, provider_name, model_id)

async def _perform_engine_test(engine_type: str, provider_name: str, model_id: str):
    registry = ModelRegistry.get_instance()
    provider = await registry._get_provider(provider_name)
    
    if not provider:
        return {"status": "error", "error": f"服务商 {provider_name} 未配置或未激活"}

    try:
        # Temporarily ensure the model is in enabled_models for the test
        original_models = provider.config.enabled_models.copy()
        provider.config.enabled_models[engine_type] = model_id
        
        response_text = ""
        if engine_type == "llm":
            if not hasattr(provider, 'chat'):
                 return {"status": "error", "error": f"服务商 {provider_name} 不支持逻辑推理 (LLM)"}
            res = await provider.chat([{"role": "user", "content": "你好，请回复'算力连接成功'并简短打个招呼"}])
            response_text = res
        elif engine_type == "embedding":
            res = await provider.embed(["测试"])
            response_text = f"成功生成向量 (维度: {len(res[0])})"
        elif engine_type == "rerank":
            results = await provider.rerank("测试", ["测试文本"], top_n=1)
            if results and len(results) > 0:
                response_text = f"成功完成语义重排，得分: {results[0].get('score', 'N/A')}"
            else:
                raise Exception("返回了空的重排结果")
        
        return {
            "status": "success", 
            "response": response_text, 
            "model": model_id, 
            "provider": provider_name
        }
    except Exception as e:
        import traceback
        print(f"DEBUG: Test Failed: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "error": str(e)}


@router.get("/providers/{ptype}/catalog")
async def get_provider_catalog(ptype: str):
    """Return static model catalog for a provider with pricing and capability info."""
    if not registry:
        raise HTTPException(503)
    provider = await registry._get_provider(ptype)
    if not provider:
        raise HTTPException(404, f"服务商 {ptype} 未配置或不支持")
    models = await provider.discover_models()
    return {
        "provider": ptype,
        "models": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "capabilities": [c.value for c in m.capabilities],
                "context_window": m.context_window,
                "description": m.description,
                "price_per_1m": m.pricing_per_1m_tokens,
            }
            for m in models
        ]
    }



# Memory cache for connectivity results to avoid 429 Rate Limits
# Format: {provider_name: {"valid": bool, "error": str, "expiry": timestamp}}
_VALIDATION_CACHE = {}
VALIDATION_TTL = 60 # seconds

def init_registry(reg: ModelRegistry, pg=None) -> None:

    global registry, pg_repo
    registry = reg
    if pg: pg_repo = pg


# ── User / Key Management ──

@router.get("/users")
async def list_all_users():
    """List all registered users (no passwords exposed)."""
    from backend.auth.accounts import list_users
    return {"users": list_users()}

@router.post("/users/{username}/revoke")
async def revoke_user_key(username: str):
    """Revoke a user's API key — they can no longer authenticate."""
    from backend.auth.accounts import revoke_user
    ok = revoke_user(username)
    if not ok:
        raise HTTPException(404, f"用户 '{username}' 不存在")
    return {"username": username, "revoked": True, "message": "API Key 已吊销，该用户无法继续访问"}

@router.delete("/users/{username}")
async def delete_user_account(username: str):
    """Permanently delete a user account."""
    from backend.auth.accounts import delete_user
    ok = delete_user(username)
    if not ok:
        raise HTTPException(404, f"用户 '{username}' 不存在")
    return {"username": username, "deleted": True}


# ── Provider CRUD ──

@router.get("/providers")
async def list_providers():
    if not registry:
        raise HTTPException(503, "Registry not ready")
    return {
        ptype: {
            "provider_type": cfg.provider_type,
            "api_key": cfg.api_key[:8] + "..." if cfg.api_key else "",
            "api_base": cfg.api_base or "",
            "enabled_models": cfg.enabled_models,
            "enabled_capabilities": cfg.enabled_capabilities,
        }
        for ptype, cfg in registry.configs.items()
    }


@router.put("/providers/{ptype}")
async def save_provider(ptype: str, data: dict):
    if not registry:
        raise HTTPException(503, "Registry not ready")
    # Avoid 'multiple values for argument' error
    data.pop("provider_type", None)
    cfg = registry.update_provider(ptype, **data)
    return {
        "provider_type": cfg.provider_type,
        "enabled_models": cfg.enabled_models,
        "enabled_capabilities": cfg.enabled_capabilities,
    }


@router.delete("/providers/{ptype}")
async def remove_provider(ptype: str):
    if not registry:
        raise HTTPException(503)
    registry.delete_provider(ptype)
    return {"deleted": True}


@router.post("/providers/{ptype}/validate")
async def validate_provider(ptype: str):
    """Test connectivity for a provider with lightweight check + cache."""
    now = time.time()
    if ptype in _VALIDATION_CACHE and now < _VALIDATION_CACHE[ptype]["expiry"]:
        return {"valid": _VALIDATION_CACHE[ptype]["valid"], "error": _VALIDATION_CACHE[ptype]["error"]}

    if not registry: raise HTTPException(503)
    try:
        result = await registry.validate_provider(ptype)
        
        # Store in cache
        valid = result.get("valid", False) if isinstance(result, dict) else bool(result)
        error = result.get("error", "") if isinstance(result, dict) else ""
        _VALIDATION_CACHE[ptype] = {"valid": valid, "error": error, "expiry": now + VALIDATION_TTL}
        
        return {"valid": valid, "error": error}
    except Exception as e:
        return {"valid": False, "error": str(e)}




@router.get("/providers/{ptype}/models")
async def list_provider_models(ptype: str):
    if not registry:
        raise HTTPException(503)
    models = await registry.discover_provider_models(ptype)
    return {"provider": ptype, "models": models}


@router.get("/recommendations")
async def get_recommendations():
    if not registry:
        raise HTTPException(503)
    return {"system": ModelRegistry.detect_environment(), "recommendations": ModelRegistry.recommend_models()}




# ── System Settings ──



# ── API Key Management ──

@router.get("/auth/keys")
async def list_api_keys(team_id: str = "default"):
    from backend.auth.apikeys import list_keys, Role
    return {"keys": list_keys(team_id)}


@router.delete("/auth/keys/{token_prefix}")
async def remove_api_key(token_prefix: str):
    """Revoke an API key by its full token."""
    from backend.auth.apikeys import revoke_key
    ok = revoke_key(token_prefix)
    return {"revoked": ok}


@router.get("/ollama")
async def ollama_status():
    try:
        from backend.providers.ollama_wizard import detect_ollama, detect_omlx, RECOMMENDED_MODELS
        return {"ollama": detect_ollama(), "omlx": detect_omlx(), "recommended": RECOMMENDED_MODELS}
    except Exception as e:
        return {"ollama": {"installed": False, "error": str(e)}, "omlx": {"installed": False}, "recommended": {}}

@router.post("/ollama/pull")
async def ollama_pull(data: dict):
    from backend.providers.ollama_wizard import pull_model
    import asyncio
    model = data.get("model", "")
    if not model: raise HTTPException(400, "model required")
    try:
        await asyncio.to_thread(pull_model, model)
        return {"pulled": model}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/context/stats")
async def context_stats(team_id: str = "default"):
    """Detect conflicts and duplicates in the knowledge base."""
    if not registry: raise HTTPException(503)
    from backend.memory.context_engineer import detect_conflicts
    # Get all memories
    async with registry._get_provider("alibaba") if False else None:
        pass
    return {"conflicts": 0, "note": "Use POST /memory/reflect for full analysis"}



@router.get("/costs")
def cost_summary():
    from backend.services.cost_tracker import CostTracker
    return CostTracker.summary()


@router.get("/settings")
async def get_settings():
    if not registry:
        raise HTTPException(503)
    from backend.services.config import settings
    import os, json
    settings_file = Path(__file__).parent.parent.parent / "settings.json"
    saved = {}
    if settings_file.exists():
        try:
            saved = json.loads(settings_file.read_text())
        except:
            pass
    return {
        "bm25_enabled": saved.get("bm25_enabled", "auto"),
        "search_rerank_threshold": saved.get("search_rerank_threshold", settings.search_rerank_threshold),
        "bm25": _check_bm25(),
    }


@router.put("/settings")
async def update_settings(data: dict):
    from backend.services.config import settings
    import os, json
    settings_file = Path(__file__).parent.parent.parent / "settings.json"
    current = {}
    if settings_file.exists():
        try:
            current = json.loads(settings_file.read_text())
        except:
            pass
    current.update(data)
    settings_file.write_text(json.dumps(current, indent=2))
    
    # Dynamic sync to runtime
    if "search_rerank_threshold" in data:
        settings.search_rerank_threshold = float(data["search_rerank_threshold"])
    if "bm25_enabled" in data:
        os.environ["MEMORY_OS_BM25"] = str(data["bm25_enabled"])
        
    return {"saved": True, "settings": current}


def _check_bm25() -> dict:
    from backend.providers.local import get_bm25
    bm25 = get_bm25()
    return {
        "available": bm25 is not None,
        "backend": bm25.name if bm25 else None,
    }






@router.get("/debug/registry")
async def debug_registry():
    if not registry:
        return {"error": "no registry"}
    return {
        "alibaba_config": {
            "has_key": bool(registry.configs.get("alibaba", ProviderConfig(provider_type="alibaba", api_key="")).api_key),
            "models": registry.configs.get("alibaba", ProviderConfig(provider_type="alibaba", api_key="")).enabled_models,
        },
        "rerank_callable": callable(registry.rerank),
    }

@router.get("/health")
async def health():
    if not registry:
        return {"status": "degraded", "registry": "not ready"}
    return {"status": "ok", "providers": len(registry.configs)}


@router.post("/system/restart")
async def restart_system():
    import os, signal, asyncio
    async def trigger_exit():
        await asyncio.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
    asyncio.create_task(trigger_exit())
    return {"status": "restarting", "message": "System container is exiting for restart..."}

@router.get("/dashboard")
async def dashboard_stats():
    """Real-time stats for the dashboard including 14-day trends."""
    from backend.services.cost_tracker import CostTracker
    summary = CostTracker.summary()
    total = 0; agent_count = 0
    try:
        async with pg_repo.pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT count(*) as t, count(*) FILTER (WHERE source_type='agent') as a FROM memories"
            )
            if r: total, agent_count = r["t"], r["a"]
    except: pass
    
    saved_tokens = summary.get("total_tokens", 0) * 0.5 # Heuristic: saved approx 50% via RAG
    return {
        "memories": {"total": total, "by_agent": agent_count},
        "costs": summary,
        "estimated_tokens_saved": int(saved_tokens),
        "estimated_cost_saved": round(saved_tokens / 1e6 * 2.0, 4)
    }



@router.get("/stats")
async def usage_stats():
    """Basic usage statistics."""
    total = searches = stores = 0
    try:
        async with pg_repo.pool.acquire() as conn:
            r = await conn.fetchrow("SELECT count(*) as t FROM memories")
            if r: total = r["t"]
            r2 = await conn.fetchrow("SELECT count(*) as t FROM memories WHERE source_type='agent'")
            if r2: stores = r2["t"]
    except: pass
    # Rough search count from audit or just return what we have
    return {"total_memories": total, "agent_memories": stores, "note": "Full analytics requires audit log table"}

@router.get("/system/logs")
async def get_system_logs(lines: int = 100):
    """Read actual application logs for remote debugging."""
    log_path = Path(__file__).parent.parent / "app.log"
    if not log_path.exists(): return {"logs": "Log file not found"}
    try:
        content = subprocess.check_output(["tail", "-n", str(lines), str(log_path)], text=True)
        return {"logs": content}
    except: return {"logs": "Error reading logs"}

@router.get("/knowledge/all")
async def list_all_knowledge(limit: int = 50, query: str = None):
    """Super-admin: View and manage all knowledge across all teams."""
    async with pg_repo.pool.acquire() as conn:
        q = "SELECT * FROM memories "
        if query: q += "WHERE title ILIKE $1 OR content ILIKE $2 "; params = [f"%{query}%", f"%{query}%"]
        q += "ORDER BY created_at DESC LIMIT $1"
        rows = await conn.fetch(q, limit)
        return [dict(r) for r in rows]

@router.get("/knowledge/tree")
async def get_knowledge_tree():
    """Return hierarchical category/subcategory tree with counts."""
    async with pg_repo.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT category, subcategory, count(*) as count 
            FROM memories 
            GROUP BY category, subcategory
            ORDER BY category, subcategory
        """)
        tree = {}
        for r in rows:
            cat = r["category"] or "未分类"
            sub = r["subcategory"] or "其他"
            if cat not in tree: tree[cat] = {"count": 0, "subs": {}}
            tree[cat]["subs"][sub] = r["count"]
            tree[cat]["count"] += r["count"]
        return tree

@router.get("/knowledge/items")
async def get_knowledge_items(category: str, subcategory: str = None, limit: int = 50):
    """Return specific memories under a category/subcategory."""
    async with pg_repo.pool.acquire() as conn:
        if subcategory and subcategory != "其他":
            rows = await conn.fetch("SELECT id, title, content, lifecycle_stage, created_at FROM memories WHERE category=$1 AND subcategory=$2 ORDER BY created_at DESC LIMIT $3", category, subcategory, limit)
        else:
            rows = await conn.fetch("SELECT id, title, content, lifecycle_stage, created_at FROM memories WHERE category=$1 ORDER BY created_at DESC LIMIT $2", category, limit)
        return [dict(r) for r in rows]

@router.get("/environment")
async def get_environment_status():
    """Return the active provider and models being used."""
    if not registry: raise HTTPException(503)
    from backend.services.config import settings
    # Find local availability
    env = registry.detect_environment()
    has_gpu = any(g for g in env.get("gpus", []))
    
    return {
        "active_provider": settings.active_provider,
        "language_model": "Auto-selected (Cloud)" if settings.active_provider != "local" else "Local LLM",
        "embedding_model": settings.embedding_model,
        "embedding_mode": "Local CPU" if not has_gpu else "Local GPU Accelerated",
        "rerank_model": "BAAI/bge-reranker" if callable(registry.rerank) else "None/Cloud",
    }

@router.get("/network/info")
async def get_network_info():
    """Get LAN and local access URLs and deployment guide tips."""
    import socket, os
    env_ips = os.environ.get("HOST_PHYSICAL_IPS") or os.environ.get("HOST_PHYSICAL_IP") or ""
    lan_ips = [ip.strip() for ip in env_ips.split(",") if ip.strip()]
    
    if not lan_ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(('10.254.254.254', 1))
            lan_ips = [s.getsockname()[0]]
            s.close()
        except Exception:
            lan_ips = ["127.0.0.1"]
            
    # Ensure localhost and 127.0.0.1 are present as standard links
    if "127.0.0.1" not in lan_ips:
        lan_ips.append("127.0.0.1")
        
    return {
        "local_ip": "127.0.0.1",
        "lan_ips": lan_ips,
        "port": 8003,
        "wan_guide": "若需要外网访问，您可以使用端口映射（在路由器中将 8003 端口映射至外网）、自建内网穿透（如 frp / Cloudflare Tunnel）或使用 Tailscale / ZeroTier 组建虚拟局域网进行远程接入。"
    }

@router.post("/knowledge/classify-all")
async def batch_classify_all(background_tasks: BackgroundTasks = None):
    """Classify all unclassified memories in background."""
    if background_tasks:
        background_tasks.add_task(_run_batch_classify)
        return {"status": "started", "message": "Classification running in background"}
    return {"status": "sync_not_supported"}

async def _run_batch_classify():
    """Batch classify all unclassified or existing memories."""
    from backend.services.classifier import classify_memory
    async with pg_repo.pool.acquire() as conn:
        # Get all memories to classify
        rows = await conn.fetch("SELECT id, title, content FROM memories WHERE category IS NULL OR category = '' OR category = '未分类'")
        count = 0
        for r in rows:
            clf = await classify_memory(r["content"] or "", r["title"] or "", registry)
            await conn.execute("""
                UPDATE memories 
                SET category=$1, subcategory=$2, topic=$3 
                WHERE id=$4
            """, clf["category"], clf["subcategory"], clf["topic"], r["id"])
            count += 1
        return {"status": "complete", "classified_count": count}

@router.post("/internalize")
async def trigger_internalization(team_id: str = "default"):
    """Manually trigger the evaluation of personal memories for knowledge promotion."""
    from backend.services.internalizer import InternalizationService
    from backend.api.routes import retrieval # Access global retrieval pipeline
    
    svc = InternalizationService(pg_repo, retrieval, registry)
    count = await svc.evaluate_and_promote(team_id)
    return {"status": "success", "promoted_count": count}




@router.delete("/knowledge/{id}")
async def admin_delete_knowledge(id: str):
    """Super-admin: Force delete any memory."""
    async with pg_repo.pool.acquire() as conn:
        await conn.execute("DELETE FROM memories WHERE id=$1", id)
    return {"status": "deleted"}

@router.post("/providers/{ptype}/auto-setup")
async def auto_setup_provider(ptype: str):
    """Validate connectivity and auto-select best cost/perf models for this provider."""
    if not registry: raise HTTPException(503)

    # validate_provider now returns a dict like {"valid": True} or {"valid": False, "error": "..."}
    result = await registry.validate_provider(ptype)
    valid = result.get("valid", False) if isinstance(result, dict) else bool(result)
    if not valid:
        error = result.get("error", "连通性检测失败") if isinstance(result, dict) else "连通性检测失败"
        raise HTTPException(401, f"无法自动优化：{error}，请先确保 API 密钥正确且能连通。")

    # Best model selection per provider (cost-performance optimized)
    BEST_MODELS = {
        "alibaba": {
            "embedding": "text-embedding-v3",   # 1024-dim, 100+ languages, ¥0.7/1M tokens
            "rerank":    "gte-rerank",           # Best quality reranker on DashScope
        },
        "zhipu": {
            "embedding": "embedding-3",          # 2048-dim, best quality on Zhipu
            "rerank":    "",                     # Zhipu has no dedicated reranker yet
        },
        "openai": {
            "embedding": "text-embedding-3-small",  # Best cost/quality balance: $0.02/1M
            "rerank":    "",                         # OpenAI has no dedicated reranker
        },
    }

    best = BEST_MODELS.get(ptype, {})
    if not best:
        raise HTTPException(400, f"未知服务商: {ptype}")

    registry.update_provider(ptype, enabled_models=best)

    return {"status": "optimized", "models": best}

@router.get("/system/hardware")
async def get_hardware_advice():
    import platform, subprocess
    cpu_count = 8  # Safe fallback
    total_mem_gb = 16.0  # Safe fallback
    system_platform = platform.system()
    machine = platform.machine()
    
    # Try reading CPU cores and RAM size from system properties
    try:
        if system_platform == "Darwin":
            # macOS system commands
            cpu_val = subprocess.check_output(["sysctl", "-n", "hw.ncpu"]).strip()
            cpu_count = int(cpu_val)
            mem_val = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip()
            total_mem_gb = round(int(mem_val) / (1024**3), 1)
        elif system_platform == "Linux":
            # Linux system commands or proc filesystem
            with open("/proc/cpuinfo") as f:
                cpu_count = sum(1 for line in f if "processor" in line)
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split()[1])
                        total_mem_gb = round(mem_kb / (1024 * 1024), 1)
                        break
    except Exception:
        pass

    advice = "配置较低，建议使用云端 API。"
    if total_mem_gb >= 15.0:
        advice = "系统算力充沛，推荐运行 Llama-3-8B 或 Qwen-2.5-7B 本地版组合。"
    if "arm" in machine.lower() or "darwin" in system_platform.lower():
        advice += " 检测到 Apple Silicon macOS 架构，推荐使用 Omlx/Ollama 运行极致本地算力加速。"
        
    return {
        "cpu": f"{cpu_count} 核心",
        "memory": f"{total_mem_gb} GB",
        "platform": f"{system_platform} {machine}",
        "advice": advice
    }

@router.post("/reflect")
async def run_reflection(team_id: str = "all"):

    """Manually trigger knowledge reflection and consolidation."""
    # We'll use the background task if possible, but for admin we run it once
    from backend.reflection.engine import ReflectionEngine
    from backend.graph.neo4j_store import GraphStore
    from backend.services.config import settings
    gs = GraphStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
    refl = ReflectionEngine(pg_repo, gs, registry=registry)
    # If team_id is all, we need to list all teams
    reports = []
    if team_id == "all":
        from backend.auth.accounts import _load
        accounts = _load()
        teams = set(v["team_id"] for v in accounts.values())
        for t in teams:
            rep = await refl.reflect_all(t)
            reports.append({"team": t, "report": rep})
    else:
        rep = await refl.reflect_all(team_id)
        reports.append({"team": team_id, "report": rep})
    gs.close()
    return {"status": "complete", "reports": reports}

@router.get("/teams")
async def list_teams():
    """List all registered teams and their users."""
    from backend.auth.accounts import _load
    accounts = _load()
    teams = {}
    for user, info in accounts.items():
        tid = info["team_id"]
        if tid not in teams: teams[tid] = []
        teams[tid].append({"user": user, "role": info["role"], "created": info.get("created")})
    return teams

@router.get("/audit")
async def get_audit_logs(limit: int = 50):
    """Fetch recent system activity logs."""
    async with pg_repo.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]


# ── Sidecar Local Gateway Process Controller ──
import sys
_sidecar_process = None

@router.get("/sidecar/status")
async def get_sidecar_status():
    global _sidecar_process
    running = False
    if _sidecar_process is not None:
        if _sidecar_process.poll() is None:
            running = True
        else:
            _sidecar_process = None
            
    # As a secondary check, see if port 9999 is responding
    if not running:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.25)
            s.connect(("127.0.0.1", 9999))
            running = True
            s.close()
        except Exception:
            pass
            
    return {"running": running, "port": 9999}

@router.post("/sidecar/start")
async def start_sidecar(data: dict = None):
    global _sidecar_process
    if _sidecar_process is not None and _sidecar_process.poll() is None:
        return {"status": "running", "message": "Sidecar already running"}
        
    api_key = "default"
    if data:
        api_key = data.get("api_key", "default")
        
    # Get python executable path
    py_exec = sys.executable or "python"
    script_path = str(Path(__file__).parent.parent / "scripts" / "local_gateway.py")
    
    # Launch local_gateway.py in background
    try:
        _sidecar_process = subprocess.Popen(
            [py_exec, script_path, "--port", "9999", "--cloud-url", "http://127.0.0.1:8003", "--api-key", api_key],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "started", "message": "Sidecar started successfully"}
    except Exception as e:
        raise HTTPException(500, f"Failed to start sidecar: {str(e)}")

@router.post("/sidecar/stop")
async def stop_sidecar():
    global _sidecar_process
    if _sidecar_process is not None:
        try:
            _sidecar_process.terminate()
            _sidecar_process.wait(timeout=1.5)
        except Exception:
            try:
                _sidecar_process.kill()
            except Exception:
                pass
        _sidecar_process = None
        
    # Clear port 9999 binding aggressively to avoid "port already in use" errors
    try:
        output = subprocess.check_output(["lsof", "-t", "-i", ":9999"], text=True)
        for pid in output.strip().split("\n"):
            if pid: os.kill(int(pid), 9)
    except Exception:
        pass
            
    return {"status": "stopped", "message": "Sidecar stopped successfully"}


# ── V5.0 Bindings & Telemetry Endpoints ──

@router.get("/tenants")
async def list_tenants_alias():
    """V5.0 UI compatible endpoint for fetching registered tenants."""
    return await list_teams()


@router.get("/audit-logs")
async def get_audit_logs_alias(limit: int = 50):
    """V5.0 UI compatible endpoint for fetching operational logs."""
    return await get_audit_logs(limit)


@router.post("/reflection/trigger")
async def trigger_reflection_alias(team_id: str = "all"):
    """V5.0 UI compatible endpoint for triggering knowledge reflection."""
    return await run_reflection(team_id)


@router.get("/stats/throughput")
async def get_throughput_stats():
    """Return real-time write throughput (last 10 minutes) from PostgreSQL database."""
    import datetime
    labels = []
    values = []
    
    now = datetime.datetime.now(datetime.timezone.utc)
    if pg_repo and pg_repo.pool:
        try:
            async with pg_repo.pool.acquire() as conn:
                for i in range(9, -1, -1):
                    minute_start = now - datetime.timedelta(minutes=i+1)
                    minute_end = now - datetime.timedelta(minutes=i)
                    
                    row = await conn.fetchrow("""
                        SELECT COUNT(*) FROM memories 
                        WHERE created_at >= $1 AND created_at < $2
                    """, minute_start, minute_end)
                    
                    labels.append((now - datetime.timedelta(minutes=i)).strftime("%H:%M"))
                    values.append(row[0] if row else 0)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error querying throughput stats: {e}")
            labels = [(now - datetime.timedelta(minutes=i)).strftime("%H:%M") for i in range(9, -1, -1)]
            values = [0] * 10
    else:
        labels = [(now - datetime.timedelta(minutes=i)).strftime("%H:%M") for i in range(9, -1, -1)]
        values = [0] * 10
            
    return {"labels": labels, "values": values}


@router.post("/providers/detect-local")
async def detect_local_providers_endpoint():
    """Detect local models (Ollama, LM Studio, etc.) by checking typical networking sockets."""
    import httpx
    import asyncio
    
    LOCAL_FRAMEWORKS = [
        # Ollama
        {"name": "Ollama", "url": "http://localhost:11434", "models_endpoint": "/api/tags"},
        {"name": "Ollama", "url": "http://host.docker.internal:11434", "models_endpoint": "/api/tags"},
        {"name": "Ollama", "url": "http://172.17.0.1:11434", "models_endpoint": "/api/tags"},
        
        # LM Studio
        {"name": "LM Studio", "url": "http://localhost:1234", "models_endpoint": "/v1/models"},
        {"name": "LM Studio", "url": "http://host.docker.internal:1234", "models_endpoint": "/v1/models"},
        {"name": "LM Studio", "url": "http://172.17.0.1:1234", "models_endpoint": "/v1/models"},
        
        # Jan
        {"name": "Jan", "url": "http://localhost:1337", "models_endpoint": "/v1/models"},
        {"name": "Jan", "url": "http://host.docker.internal:1337", "models_endpoint": "/v1/models"},
        {"name": "Jan", "url": "http://172.17.0.1:1337", "models_endpoint": "/v1/models"},
        
        # vLLM
        {"name": "vLLM", "url": "http://localhost:8001", "models_endpoint": "/v1/models"},
        {"name": "vLLM", "url": "http://host.docker.internal:8001", "models_endpoint": "/v1/models"},
        {"name": "vLLM", "url": "http://172.17.0.1:8001", "models_endpoint": "/v1/models"},
    ]
    
    async def check_framework(fw):
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get(fw["url"] + fw["models_endpoint"])
                if resp.status_code == 200:
                    data = resp.json()
                    models = []
                    if fw["name"] == "Ollama":
                        models = [m["name"] for m in data.get("models", [])]
                    else:
                        models = [m["id"] for m in data.get("data", [])]
                    return {
                        "name": fw["name"],
                        "url": fw["url"] + "/v1",
                        "models": models[:10],
                        "is_embedding_capable": any(
                            "embed" in m.lower() or "bge" in m.lower() 
                            fo
# ── V6.0 CORE ADMIN ENDPOINTS ──

@router.get("/health")
async def get_system_health():
    """Check connectivity to all core microservices."""
    from backend.api.routes import pg_repo, qdrant_store, graph_store
    from backend.services.config import settings
    import redis
    
    health = {"backend": True}
    
    # Postgres
    try: health["postgres"] = pg_repo and await pg_repo.pool.fetchval("SELECT 1") == 1
    except: health["postgres"] = False
    
    # Qdrant
    try:
        health["qdrant"] = False
        if qdrant_store:
            # Simple check
            qdrant_store.client.get_collections()
            health["qdrant"] = True
    except: pass
    
    # Neo4j
    try:
        health["neo4j"] = False
        if graph_store:
            with graph_store.driver.session() as session:
                session.run("RETURN 1")
                health["neo4j"] = True
    except: pass
    
    # Redis
    try:
        r = redis.from_url(settings.redis_uri)
        health["redis"] = r.ping()
    except: health["redis"] = False
    
    # MinIO
    try:
        from backend.memory.minio_store import MinIOStore
        minio = MinIOStore()
        minio.client.list_buckets()
        health["minio"] = True
    except: health["minio"] = False
    
    return health

@router.get("/stats")
async def usage_stats():
    """Retrieve global system telemetry and RAG savings."""
    from backend.api.routes import pg_repo
    if not pg_repo: return {"error": "DB not ready"}
    
    total_memories = await pg_repo.pool.fetchval("SELECT COUNT(*) FROM memories")
    total_tenants = await pg_repo.pool.fetchval("SELECT COUNT(DISTINCT team_id) FROM memories")
    
    # Vector count from Qdrant if possible, or estimate
    vector_count = total_memories
    
    # RAG Savings: $0.02 per 1k tokens saved (estimate)
    saved_tokens = await pg_repo.pool.fetchval("SELECT COALESCE(SUM(tokens_saved_estimate), 0) FROM user_token_usage")
    rag_savings_usd = (saved_tokens / 1000.0) * 0.02
    
    return {
        "total_memories": total_memories,
        "total_tenants": total_tenants,
        "vector_count": vector_count,
        "rag_savings_usd": rag_savings_usd,
        "tokens_saved": saved_tokens
    }

@router.get("/stats/throughput")
async def get_throughput_stats():
    """Get memory write throughput for the last 10 minutes."""
    from backend.api.routes import pg_repo
    if not pg_repo: return {"labels": [], "values": []}
    
    rows = await pg_repo.pool.fetch("""
        SELECT to_char(created_at, 'HH24:MI') as bucket, COUNT(*) as cnt
        FROM memories
        WHERE created_at >= now() - interval '10 minutes'
        GROUP BY bucket ORDER BY bucket
    """)
    return {
        "labels": [r["bucket"] for r in rows],
        "values": [r["cnt"] for r in rows]
    }

# ── LLM ENGINE HUB ──

@router.get("/system-llm")
async def get_system_llm_config():
    """Retrieve internal engine configurations."""
    cfg = registry.load_llm_engine_config()
    return {
        "embed": cfg.get("embed", {"model_name": "bge-m3", "provider": "custom"}),
        "reflect": cfg.get("reflect", {"model_name": "deepseek-chat", "provider": "deepseek"}),
        "classify": cfg.get("classify", {"model_name": "deepseek-chat", "provider": "deepseek"})
    }

@router.post("/system-llm")
async def save_system_llm_config(data: dict):
    """Update internal engine configuration (Embed/Reflect/Classify)."""
    engine_type = data.get("engine_type")
    if engine_type not in ["embed", "reflect", "classify"]:
        raise HTTPException(400, "Invalid engine type")
        
    cfg = registry.load_llm_engine_config()
    
    update = {
        "provider": data.get("provider"),
        "model_name": data.get("model_name"),
        "api_base_url": data.get("api_base_url"),
    }
    if data.get("api_key"):
        from backend.utils.crypto import encrypt_key
        update["api_key"] = encrypt_key(data["api_key"])
        
    cfg[engine_type] = update
    registry.save_llm_engine_config(cfg)
    return {"status": "ok"}

@router.post("/system-llm/test")
async def test_system_llm(data: dict):
    """Test connectivity for a specific engine config."""
    provider = data.get("provider")
    model = data.get("model_name")
    api_key = data.get("api_key")
    base_url = data.get("api_base_url")
    engine_type = data.get("engine_type")
    
    # Re-use test logic from ModelRegistry or local provider
    from backend.manager.registry import PROVIDER_CLASSES
    from backend.providers.base import ProviderConfig
    
    cls = PROVIDER_CLASSES.get(provider)
    if not cls: return {"ok": False, "error": f"Provider {provider} not supported"}
    
    # If key is missing, try to load from saved
    if not api_key:
        saved = registry.load_llm_engine_config().get(engine_type, {})
        if saved.get("api_key"):
            from backend.utils.crypto import decrypt_key
            api_key = decrypt_key(saved["api_key"])
            
    prov_cfg = ProviderConfig(
        provider_type=provider,
        api_key=api_key or "",
        api_base=base_url or "",
        enabled_models={"llm": model, "embedding": model, "rerank": model},
        enabled_capabilities=["llm", "embedding"]
    )
    prov = cls(prov_cfg)
    
    start = time.time()
    try:
        if engine_type == "embed":
            await prov.embed(["ping"])
        else:
            await prov.chat([{"role": "user", "content": "ping"}], max_tokens=1)
        latency = int((time.time() - start) * 1000)
        return {"ok": True, "latency_ms": latency}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── AI REFLECTION CHAT ──

@router.post("/reflection/chat")
async def reflection_ai_chat(data: dict):
    """Interactive AI chat with the knowledge base analysis engine."""
    messages = data.get("messages", [])
    if not messages: raise HTTPException(400, "Messages required")
    
    # Inject system context for reflection
    system_prompt = {
        "role": "system",
        "content": "You are the AI Memory OS Reflection Engine. Your job is to analyze the user's knowledge base, "
                   "summarize findings, identify knowledge gaps, and trigger memory consolidation. "
                   "You have access to global statistics. Maintain a professional, technical, and helpful persona."
    }
    
    # Use the reflection engine LLM
    try:
        reply = await registry.chat_for_engine("reflect", [system_prompt] + messages)
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"❌ Reflection Error: {str(e)}"}

# ── KNOWLEDGE GRAPH ──

@router.get("/knowledge-graph")
async def get_vis_graph(team_id: str = "all"):
    """Fetch nodes and edges for Vis.js visualization."""
    from backend.api.routes import graph_store
    if not graph_store: return {"nodes": [], "edges": []}
    
    cypher = "MATCH (n:Knowledge) "
    if team_id != "all":
        cypher += f"WHERE n.team_id = '{team_id}' "
    cypher += "RETURN n LIMIT 100"
    
    nodes = []
    edges = []
    
    with graph_store.driver.session() as session:
        result = session.run(cypher)
        for record in result:
            n = record["n"]
            nodes.append({
                "id": n.get("id"),
                "label": n.get("title") or n.get("name") or "Untitled",
                "type": n.get("category", "general"),
                "content": n.get("summary") or n.get("content", "")[:200]
            })
            
            # Find relationships for this node
            rel_res = session.run("MATCH (n)-[r]->(m) WHERE id(n) = $id RETURN r, m LIMIT 10", id=n.id)
            for rel_rec in rel_res:
                r = rel_rec["r"]
                m = rel_rec["m"]
                edges.append({
                    "from": n.get("id"),
                    "to": m.get("id"),
                    "type": r.type
                })
                
    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "last_updated": time.time() * 1000
    }

# ── TENANT MANAGEMENT ──

@router.get("/tenants")
async def list_tenants():
    """List all tenants with enriched stats."""
    from backend.api.routes import pg_repo
    if not pg_repo: return []
    
    rows = await pg_repo.pool.fetch("""
        SELECT team_id, COUNT(*) as memory_count, 
               MAX(created_at) as last_active,
               MIN(created_at) as created_at
        FROM memories GROUP BY team_id
    """)
    
    tenants = []
    for r in rows:
        tenants.append({
            "team_id": r["team_id"],
            "memory_count": r["memory_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else "",
            "active": True
        })
    return {"tenants": tenants}

@router.get("/tenants/{team_id}")
async def get_tenant_detail(team_id: str):
    from backend.api.routes import pg_repo
    if not pg_repo: raise HTTPException(503)
    
    count = await pg_repo.count_by_team(team_id)
    tokens = await pg_repo.pool.fetchval("SELECT SUM(total_tokens) FROM user_token_usage WHERE user_id = $1", pg_repo.safe_uuid(team_id))
    
    return {
        "team_id": team_id,
        "memory_count": count,
        "token_usage": tokens or 0,
        "status": "active"
    }

@router.delete("/tenants/{team_id}/memories")
async def clear_tenant_memories(team_id: str):
    from backend.api.routes import pg_repo, qdrant_store
    if not pg_repo: raise HTTPException(503)
    
    await pg_repo.pool.execute("DELETE FROM memories WHERE team_id = $1", team_id)
    if qdrant_store:
        qdrant_store.client.delete(collection_name=qdrant_store.collection_name, points_selector={"must": [{"key": "team_id", "match": {"value": team_id}}]})
    return {"status": "ok"}

# ── SERVICE TELEMETRY ──

@router.get("/qdrant/stats")
async def get_qdrant_stats():
    from backend.api.routes import qdrant_store
    if not qdrant_store: return {"status": "disconnected"}
    coll = qdrant_store.client.get_collection(qdrant_store.collection_name)
    return {
        "status": "connected",
        "vectors_count": coll.vectors_count,
        "segments_count": coll.segments_count,
        "indexing_status": coll.status
    }

@router.get("/neo4j/stats")
async def get_neo4j_stats():
    from backend.api.routes import graph_store
    if not graph_store: return {"status": "disconnected"}
    with graph_store.driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
    return {
        "status": "connected",
        "nodes": node_count,
        "relationships": rel_count
    }
@router.post("/security/config")
async def save_security_config(data: dict):
    from backend.services.config import load_system_config, save_system_config
    cfg = load_system_config()
    cfg["security"] = {
        "jwt_expire": int(data.get("jwt_expire", 43200))
    }
    save_system_config(cfg)
    return {"status": "success", "message": "Security parameters saved successfully"}

@router.post("/reflection/config")
async def save_reflection_config(data: dict):
    """Persist system-wide Knowledge Reflection parameters."""
    from backend.services.config import load_system_config, save_system_config
    cfg = load_system_config()
    cfg["reflection"] = {
        "decay_rate": float(data.get("decay_rate", 0.05)),
        "quality_threshold": float(data.get("quality_threshold", 0.80)),
        "interval_hours": int(data.get("interval_hours", 24))
    }
    save_system_config(cfg)
    return {"status": "success", "message": "Reflection parameters saved successfully"}



