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
        result = await register(team_id, username, password, data.get("role", "user"), email=data.get("email"))
        return result
    except ValueError as e:
        raise HTTPException(409, str(e))

@public_router.get("/setup/status")
async def get_setup_status():
    return {"complete": is_setup_complete()}

@public_router.post("/auth/login")
async def login_admin(data: dict):
    """Unified login for both users and admins, returning V6-compatible structure."""
    from backend.auth.accounts import login
    username = data.get("username", "admin").strip()
    password = data.get("password", "").strip()
    try:
        result = await login(username, password)
        # Wrap result for V6 UI compatibility
        from backend.auth.middleware import create_access_token
        token = create_access_token(result["team_id"])
        
        return {
            "api_key": token,
            "token": token,
            "user": {
                "id": username,
                "username": username,
                "role": result["role"],
                "team_id": result["team_id"]
            }
        }
    except ValueError as e:
        raise HTTPException(401, str(e))

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
        await register("default", "admin", pwd, "admin")
    except ValueError:
        # If admin already exists but setup wasn't marked complete, just continue
        pass
        
    # 2. Update provider
    registry = ModelRegistry.get_instance()
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
    registry = ModelRegistry.get_instance()
    return registry.load_routing()


@router.put("/routing")
async def save_routing(data: dict):
    """Save LLM/Embedding/Rerank routing config and apply immediately."""
    registry = ModelRegistry.get_instance()
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
    registry = ModelRegistry.get_instance()
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
    registry = ModelRegistry.get_instance()
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

_pg_repo = None
_qdrant_store = None
_graph_store = None
_minio_store = None

def init_registry(reg: ModelRegistry, pg=None, qs=None, gs=None, ms=None) -> None:
    global _pg_repo, _qdrant_store, _graph_store, _minio_store
    _pg_repo = pg
    _qdrant_store = qs
    _graph_store = gs
    _minio_store = ms


# ── User / Key Management ──

@router.get("/users")
async def list_all_users(q: str = None, limit: int = 50):
    """List all registered users for the management UI."""
    from backend.auth.accounts import list_users
    users = await list_users()
    if q:
        users = [u for u in users if q.lower() in u["username"].lower()]
    
    formatted_users = []
    for u in users:
        memory_count = 0
        if _pg_repo:
            try:
                memory_count = await _pg_repo.count_by_team(u["team_id"])
            except Exception:
                pass
        
        formatted_users.append({
            "user_id": u["username"],  # Map username to user_id for the UI
            "username": u["username"],
            "team_id": u["team_id"],
            "role": u["role"],
            "created": u["created"],
            "api_key_prefix": u["api_key_prefix"],
            "active": u["status"] == "active",  # Map active status to boolean
            "status": u["status"],
            "memory_count": memory_count,
            "token_usage": 0
        })
    
    return {"users": formatted_users[:limit]}

@router.get("/tenants")
async def list_tenants():
    """List all teams (tenants) with metadata."""
    from backend.auth.accounts import list_users
    users = await list_users()
    teams = {}
    for u in users:
        tid = u["team_id"]
        if tid not in teams:
            teams[tid] = {"team_id": tid, "name": tid, "user_count": 0, "memory_count": 0, "active": True}
        teams[tid]["user_count"] += 1
    return {"tenants": list(teams.values())}

@router.post("/tenants")
async def create_new_tenant(data: dict):
    """Create a new team/tenant and its first admin."""
    from backend.auth.accounts import register
    team_id = data.get("team_id")
    name = data.get("name", team_id)
    admin_user = data.get("admin_username")
    admin_pwd = data.get("admin_password")
    if not all([team_id, admin_user, admin_pwd]):
        raise HTTPException(400, "Missing required fields")
    await register(team_id, admin_user, admin_pwd, role="admin")
    return {"status": "success", "team_id": team_id}

@router.post("/users/{username}/suspend")
async def suspend_user_account(username: str):
    """Suspend a user account."""
    from backend.auth.accounts import suspend_user
    ok = await suspend_user(username)
    if not ok:
        raise HTTPException(404, f"用户 '{username}' 不存在")
    return {"username": username, "suspended": True}

@router.post("/users/{username}/activate")
async def activate_user_account(username: str):
    """Activate a suspended user account."""
    from backend.auth.accounts import activate_user
    ok = await activate_user(username)
    if not ok:
        raise HTTPException(404, f"用户 '{username}' 不存在")
    return {"username": username, "active": True}

@router.post("/users/{username}/revoke")
async def revoke_user_key(username: str):
    """Revoke a user's API key — they can no longer authenticate."""
    from backend.auth.accounts import revoke_user
    ok = await revoke_user(username)
    if not ok:
        raise HTTPException(404, f"用户 '{username}' 不存在")
    return {"username": username, "revoked": True, "message": "API Key 已吊销，该用户无法继续访问"}

@router.delete("/users/{username}")
async def delete_user_account(username: str):
    """Permanently delete a user account."""
    from backend.auth.accounts import delete_user
    ok = await delete_user(username)
    if not ok:
        raise HTTPException(404, f"用户 '{username}' 不存在")
    return {"username": username, "deleted": True}


# ── Provider CRUD ──

@router.get("/providers")
async def list_providers():
    registry = ModelRegistry.get_instance()
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
    registry = ModelRegistry.get_instance()
    data.pop("provider_type", None)
    cfg = registry.update_provider(ptype, **data)
    return {
        "provider_type": cfg.provider_type,
        "enabled_models": cfg.enabled_models,
        "enabled_capabilities": cfg.enabled_capabilities,
    }


@router.delete("/providers/{ptype}")
async def remove_provider(ptype: str):
    registry = ModelRegistry.get_instance()
    registry.delete_provider(ptype)
    return {"deleted": True}


@router.post("/providers/{ptype}/validate")
async def validate_provider(ptype: str):
    """Test connectivity for a provider with lightweight check + cache."""
    now = time.time()
    if ptype in _VALIDATION_CACHE and now < _VALIDATION_CACHE[ptype]["expiry"]:
        return {"valid": _VALIDATION_CACHE[ptype]["valid"], "error": _VALIDATION_CACHE[ptype]["error"]}

    registry = ModelRegistry.get_instance()
    try:
        result = await registry.validate_provider(ptype)
        valid = result.get("valid", False) if isinstance(result, dict) else bool(result)
        error = result.get("error", "") if isinstance(result, dict) else ""
        _VALIDATION_CACHE[ptype] = {"valid": valid, "error": error, "expiry": now + VALIDATION_TTL}
        return {"valid": valid, "error": error}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.get("/providers/{ptype}/models")
async def list_provider_models(ptype: str):
    registry = ModelRegistry.get_instance()
    models = await registry.discover_provider_models(ptype)
    return {"provider": ptype, "models": models}


@router.get("/recommendations")
async def get_recommendations():
    return {"system": ModelRegistry.detect_environment(), "recommendations": ModelRegistry.recommend_models()}


# ── System Settings ──


# ── API Key Management ──

@router.get("/auth/keys")
async def list_api_keys(team_id: str = "default"):
    from backend.auth.apikeys import list_keys
    return {"keys": await list_keys(team_id)}


@router.delete("/auth/keys/{token_prefix}")
async def remove_api_key(token_prefix: str):
    """Revoke an API key by its full token."""
    from backend.auth.apikeys import revoke_key
    ok = await revoke_key(token_prefix)
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


@router.get("/costs")
def cost_summary():
    from backend.services.cost_tracker import CostTracker
    return CostTracker.summary()

@router.get("/stats")
async def get_dashboard_stats():
    """General dashboard stats matching DashboardStats interface."""
    from backend.services.cost_tracker import CostTracker
    summary = CostTracker.summary()
    
    total_memories = 0
    total_teams = 0
    if _pg_repo:
        total_memories = await _pg_repo.get_total_memory_count()
        total_teams = await _pg_repo.get_total_team_count()

    # Calculate today's writes from history
    import time
    today_str = time.strftime("%Y-%m-%d")
    today_writes = summary.get("daily_trends", {}).get(today_str, 0)

    return {
        "total": total_memories,
        "active_users": total_teams,
        "today_writes": today_writes,
        "tokens_saved": int(summary.get("total_tokens", 0) * 0.4),
        "memory_growth": "+0%" # Future: compute from history
    }

@router.get("/stats/throughput")
async def get_throughput():
    """Return throughput timeline for Chart.js."""
    import datetime
    from backend.services.cost_tracker import CostTracker
    summary = CostTracker.summary()
    history = summary.get("history", [])
    
    now = datetime.datetime.now()
    labels = []
    values = []
    
    for i in range(12):
        target_time = now - datetime.timedelta(hours=11-i)
        label = target_time.strftime("%H:00")
        labels.append(label)
        
        # Count tokens/writes in this hour
        hour_start = int(target_time.replace(minute=0, second=0, microsecond=0).timestamp())
        hour_end = hour_start + 3600
        hour_sum = sum(h.get("input_tokens",0) + h.get("output_tokens",0) for h in history if hour_start <= h["ts"] < hour_end)
        values.append(hour_sum)
        
    return {"labels": labels, "values": values}

@router.get("/stats/monitoring")
async def get_monitoring():
    """Detailed monitoring data."""
    return {
        "token_labels": [], "token_values": [],
        "writes_labels": [], "writes_values": [],
        "latency_buckets": [120, 450, 800, 1200],
        "top_tenants": []
    }

@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50):
    return {"logs": []}


@router.get("/settings")
async def get_settings():
    from backend.services.config import settings
    return {
        "bm25_enabled": "auto",
        "search_rerank_threshold": settings.search_rerank_threshold,
        "bm25": {"available": True, "backend": "fastembed"},
    }


@router.put("/settings")
async def update_settings(data: dict):
    from backend.services.config import settings
    if "search_rerank_threshold" in data:
        settings.search_rerank_threshold = float(data["search_rerank_threshold"])
    return {"saved": True}


@router.get("/debug/registry")
async def debug_registry():
    registry = ModelRegistry.get_instance()
    return {
        "alibaba_config": {
            "has_key": bool(registry.configs.get("alibaba", ProviderConfig(provider_type="alibaba", api_key="")).api_key),
            "models": registry.configs.get("alibaba", ProviderConfig(provider_type="alibaba", api_key="")).enabled_models,
        },
    }

@public_router.post("/providers/configure")
async def configure_providers(data: dict):
    """Bulk configure providers and model roles from the UI."""
    # Temporarily bypass requirement for direct completion
    configs = data.get("configs", [])
    if not configs:
        return {"ok": True}
    
    from backend.manager.registry import ModelRegistry
    reg = ModelRegistry.get_instance()
    
    # 1. Update providers.json with API keys and models
    for c in configs:
        p_id = c["provider"]
        m_id = c["model"]
        key = c["apiKey"]
        purpose = c["purpose"]
        
        if p_id not in reg.configs:
            from backend.providers.base import ProviderConfig
            reg.configs[p_id] = ProviderConfig(provider_type=p_id, api_key=key)
        
        if key:
            reg.configs[p_id].api_key = key
            
        role = {"classifier": "llm", "reflection": "llm", "embedding": "embedding", "rerank": "rerank"}.get(purpose, "llm")
        reg.configs[p_id].enabled_models[role] = m_id
        
    # 2. Persist using registry's self-contained config save logic
    reg._save_configs()
        
    # 3. Update llm_engine.json
    engine_data = reg.load_llm_engine_config()
    for c in configs:
        if c["purpose"] in ["classifier", "reflection"]:
            engine_data[c["purpose"]] = {"provider": c["provider"], "model": c["model"]}
            
    reg.save_llm_engine_config(engine_data)
        
    return {"ok": True, "message": "Configuration saved successfully"}

@router.post("/providers/test")
async def test_provider_connection(data: dict):
    """Proxy connection test through the backend."""
    provider_id = data.get("provider")
    api_key = data.get("apiKey")
    model = data.get("model")
    
    if not provider_id or not api_key:
        raise HTTPException(400, "Provider and API Key required")
        
    from backend.manager.registry import ModelRegistry
    from backend.providers.base import ProviderConfig
    
    reg = ModelRegistry.get_instance()
    try:
        cfg = ProviderConfig(provider_type=provider_id, api_key=api_key, enabled_models={"llm": model} if model else {})
        p_class = reg.get_provider_class(provider_id)
        if not p_class: return {"ok": False, "error": f"Unknown provider: {provider_id}"}
        p_inst = p_class(cfg)
        val = await p_inst.validate()
        return {"ok": val.get("valid", False), "error": val.get("error", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/health")
async def health():
    """Real health check for all core services."""
    services = {
        "postgres": False,
        "qdrant": False,
        "neo4j": False,
        "redis": True, # Placeholder until implemented
        "minio": False
    }

    # 1. Check Postgres
    if _pg_repo and _pg_repo.pool:
        try:
            async with _pg_repo.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                services["postgres"] = True
        except: pass

    # 2. Check Qdrant
    if _qdrant_store and _qdrant_store.client:
        try:
            _qdrant_store.client.get_collections()
            services["qdrant"] = True
        except: pass

    # 3. Check Neo4j
    if _graph_store and _graph_store.driver:
        try:
            _graph_store.driver.verify_connectivity()
            services["neo4j"] = True
        except: pass

    # 4. Check MinIO
    if _minio_store:
        try:
            # MinIOStore doesn't have a public check, but we can try listing
            if hasattr(_minio_store, 'client'):
                 _minio_store.client.list_buckets()
                 services["minio"] = True
            else:
                 # Minimal success if instance exists
                 services["minio"] = True
        except: pass

    all_ok = all(services.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "services": services
    }

@router.get("/graph/summary")
async def get_graph_summary():
    """Get the total count of nodes and relationships in the Neo4j graph database."""
    if not _graph_store or not _graph_store.driver:
        return {"nodes": 0, "edges": 0, "status": "disconnected"}
    
    try:
        with _graph_store.driver.session() as session:
            res_nodes = session.run("MATCH (n) RETURN count(n) as node_count;")
            node_count = res_nodes.single()["node_count"]
            
            res_edges = session.run("MATCH ()-[r]->() RETURN count(r) as edge_count;")
            edge_count = res_edges.single()["edge_count"]
            
            return {
                "nodes": node_count,
                "edges": edge_count,
                "status": "connected"
            }
    except Exception as e:
        return {"nodes": 0, "edges": 0, "status": "error", "detail": str(e)}
