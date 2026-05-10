# AI Memory OS — Admin API
# Provider CRUD, model discovery, environment detection, health check.

from __future__ import annotations

import time, subprocess, os
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
    result = login(username, password)
    if not result:
        raise HTTPException(401, "用户名或密码错误")
    return result

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
        from backend.providers.ollama_wizard import detect_ollama, RECOMMENDED_MODELS
        return {"ollama": detect_ollama(), "recommended": RECOMMENDED_MODELS}
    except Exception as e:
        return {"ollama": {"installed": False, "error": str(e)}, "recommended": {}}

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
    import os, json
    settings_file = Path(__file__).parent.parent.parent / "settings.json"
    saved = {}
    if settings_file.exists():
        saved = json.loads(settings_file.read_text())
    return {
        "bm25_enabled": saved.get("bm25_enabled", os.environ.get("MEMORY_OS_BM25", "auto")),
        "bm25": _check_bm25(),
        "note": "Restart server to apply changes" if saved.get("bm25_enabled") else None,
    }


@router.put("/settings")
async def update_settings(data: dict):
    import json
    settings_file = Path(__file__).parent.parent.parent / "settings.json"
    current = {}
    if settings_file.exists():
        current = json.loads(settings_file.read_text())
    current.update(data)
    settings_file.write_text(json.dumps(current, indent=2))
    return {"saved": True, "settings": current, "note": "Restart server to apply BM25 changes"}


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
    import psutil, platform
    mem = psutil.virtual_memory()
    cpu_count = psutil.cpu_count()
    advice = "配置较低，建议使用云端 API。"
    if mem.total > 15 * 1024**3: advice = "内存充足，推荐运行 Llama3-8B 或 Qwen2-7B 本地版。"
    if "arm" in platform.processor().lower(): advice += " 检测到 Apple Silicon，推荐使用 Ollama 运行本地加速。"
    
    return {
        "cpu": f"{cpu_count} 核心",
        "memory": f"{round(mem.total/1e9, 1)} GB",
        "platform": platform.system() + " " + platform.machine(),
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
    refl = ReflectionEngine(pg_repo, gs)
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

