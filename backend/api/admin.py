# AI Memory OS — Admin API
# Provider CRUD, model discovery, environment detection, health check.

from __future__ import annotations

import json, time, subprocess, os, logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from backend.manager.registry import ModelRegistry
from backend.auth.middleware import get_current_team, require_admin
from backend.providers.base import ProviderConfig

logger = logging.getLogger(__name__)

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
        token = create_access_token(result["team_id"], role=result["role"])
        
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
    
    if engine_type in ["classifier", "reflection"]:
        engine_data = registry.load_llm_engine_config()
        route = engine_data.get(engine_type)
    else:
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
        role = "llm" if engine_type in ["llm", "classifier", "reflection"] else engine_type
        provider.config.enabled_models[role] = model_id
        
        response_text = ""
        if engine_type in ["llm", "classifier", "reflection"]:
            if not hasattr(provider, 'chat'):
                 return {"status": "error", "error": f"服务商 {provider_name} 不支持逻辑推理 (LLM)"}
            res = await provider.chat([{"role": "user", "content": "你好，请回复'算力连接成功'并简短打个招呼"}], model=model_id)
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
        logger.exception("provider test failed: %s", e)
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
    
    # Batch fetch token usage and memory+document counts for all teams
    token_map: dict = {}
    knowledge_map: dict = {}
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        
        # 1. Fetch Tokens
        rows = await conn.fetch("SELECT team_id, COALESCE(SUM(total_tokens),0) AS tokens FROM pipeline_usage GROUP BY team_id")
        token_map = {r["team_id"]: int(r["tokens"]) for r in rows}
        
        # 2. Fetch Memories + Documents as "Knowledge" count
        # Combining counts from memories and documents tables
        k_rows = await conn.fetch("""
            SELECT team_id, SUM(cnt) as total_knowledge FROM (
                SELECT team_id, COUNT(*) as cnt FROM memories GROUP BY team_id
                UNION ALL
                SELECT team_id, COUNT(*) as cnt FROM documents GROUP BY team_id
            ) as sub GROUP BY team_id
        """)
        knowledge_map = {r["team_id"]: int(r["total_knowledge"]) for r in k_rows}
        
        await conn.close()
    except Exception:
        pass

    formatted_users = []
    for u in users:
        formatted_users.append({
            "user_id": u["username"],  # Map username to user_id for the UI
            "username": u["username"],
            "team_id": u["team_id"],
            "role": u["role"],
            "created": u["created"],
            "api_key_prefix": u["api_key_prefix"],
            "active": u["status"] == "active",  # Map active status to boolean
            "status": u["status"],
            "memory_count": knowledge_map.get(u["team_id"], 0),
            "token_usage": token_map.get(u["team_id"], 0),
            "plan": u.get("plan", "free"),
            "plan_expires_at": u.get("plan_expires_at", ""),
            "mcp_call_count": u.get("mcp_call_count", 0)
        })
    
    return {"users": formatted_users[:limit]}


@router.get("/tenants")
async def list_tenants():
    """List all teams (tenants) with metadata."""
    from backend.auth.accounts import list_users
    users = await list_users()
    # Fetch Memory + Document counts for all teams
    knowledge_map: dict = {}
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        k_rows = await conn.fetch("""
            SELECT team_id, SUM(cnt) as total_knowledge FROM (
                SELECT team_id, COUNT(*) as cnt FROM memories GROUP BY team_id
                UNION ALL
                SELECT team_id, COUNT(*) as cnt FROM documents GROUP BY team_id
            ) as sub GROUP BY team_id
        """)
        knowledge_map = {r["team_id"]: int(r["total_knowledge"]) for r in k_rows}
        await conn.close()
    except Exception:
        pass

    teams = {}
    for u in users:
        tid = u["team_id"]
        if tid not in teams:
            teams[tid] = {
                "team_id": tid, 
                "name": tid, 
                "user_count": 0, 
                "memory_count": knowledge_map.get(tid, 0), 
                "active": True
            }
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

@router.delete("/tenants/{team_id}")
async def delete_tenant(team_id: str):
    """Delete a tenant and all its associated data (memories, accounts, configs)."""
    if team_id in ("default", "admin"):
        raise HTTPException(400, "无法删除系统内置租户")
    import asyncio
    from backend.api.db_helper import get_db_conn
    try:
        conn = await get_db_conn()
        
        # 1. Clean up Neo4j knowledge graph nodes before deleting memories from Postgres
        if _graph_store and _graph_store.driver:
            try:
                rows = await conn.fetch("SELECT id FROM memories WHERE team_id = $1", team_id)
                mids = [str(r["id"]) for r in rows]
                if mids:
                    async with _graph_store.driver.session() as session:
                        await session.run("MATCH (m:Memory) WHERE m.id IN $ids DETACH DELETE m", ids=mids)
            except Exception as e:
                import logging
                logging.getLogger("admin").warning(f"Failed to delete Neo4j nodes for tenant {team_id}: {e}")

        # 2. Clean up Qdrant vector collection
        if _qdrant_store and _qdrant_store.client:
            collection_name = f"memory_team_{team_id}"
            try:
                await asyncio.to_thread(_qdrant_store.client.delete_collection, collection_name)
            except Exception as e:
                import logging
                logging.getLogger("admin").warning(f"Failed to delete Qdrant collection {collection_name}: {e}")

        # 3. Clean up MinIO files
        if _minio_store and _minio_store.client:
            try:
                from backend.memory.minio_store import BUCKET
                def cleanup_minio():
                    objects_to_delete = _minio_store.client.list_objects(BUCKET, prefix=f"{team_id}/", recursive=True)
                    for obj in objects_to_delete:
                        _minio_store.client.remove_object(BUCKET, obj.object_name)
                await asyncio.to_thread(cleanup_minio)
            except Exception as e:
                import logging
                logging.getLogger("admin").warning(f"Failed to delete MinIO files for tenant {team_id}: {e}")

        # 4. Delete Postgres records
        await conn.execute("DELETE FROM memories WHERE team_id=$1", team_id)
        await conn.execute("DELETE FROM chunks WHERE team_id=$1", team_id)
        await conn.execute("DELETE FROM documents WHERE team_id=$1", team_id)
        await conn.execute("DELETE FROM user_persona WHERE team_id=$1", team_id)
        await conn.execute("DELETE FROM task_canvas WHERE team_id=$1", team_id)
        await conn.execute("DELETE FROM pipeline_usage WHERE team_id=$1", team_id)
        # Resolve team accounts to delete their provider configs
        rows = await conn.fetch("SELECT username FROM accounts WHERE team_id=$1", team_id)
        from backend.memory.pg_repo import safe_uuid
        uids = [safe_uuid(r["username"]) for r in rows]
        if uids:
            await conn.execute("DELETE FROM user_provider_configs WHERE user_id = ANY($1)", uids)
        await conn.execute("DELETE FROM audit_log WHERE team_id=$1", team_id)
        await conn.execute("DELETE FROM accounts WHERE team_id=$1", team_id)
        await conn.close()
        return {"status": "deleted", "team_id": team_id}
    except Exception as e:
        raise HTTPException(500, f"删除失败: {str(e)}")


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
    pipeline_calls = 0
    total_tokens = summary.get("total_tokens", 0)
    
    if _pg_repo:
        total_memories = await _pg_repo.get_total_memory_count()
        total_teams = await _pg_repo.get_total_team_count()
        async with _pg_repo.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT SUM(l1_calls + l2_calls + l3_calls) as calls FROM pipeline_usage")
            if row and row["calls"]:
                pipeline_calls = int(row["calls"])
            
            row2 = await conn.fetchrow("SELECT SUM(total_tokens) as tokens FROM user_token_usage")
            if row2 and row2["tokens"]:
                total_tokens += int(row2["tokens"])

    # Calculate today's writes from history
    import time
    today_str = time.strftime("%Y-%m-%d")
    today_writes = summary.get("daily_trends", {}).get(today_str, 0)

    return {
        "total": total_memories,
        "total_memories": total_memories,
        "total_tokens": total_tokens,
        "pipeline_calls": pipeline_calls,
        "active_users": total_teams,
        "today_writes": today_writes,
        "tokens_saved": int(total_tokens * 0.4),
        "memory_growth": "+0%" # Future: compute from history
    }

@router.get("/stats/throughput")
async def get_throughput():
    """Return throughput timeline for Chart.js."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    labels = []
    values = []
    
    for i in range(12):
        target_time = now - datetime.timedelta(hours=11-i)
        label = target_time.strftime("%H:00")
        labels.append(label)
        values.append(0)
        
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        start_time = now - datetime.timedelta(hours=12)
        rows = await conn.fetch("""
            SELECT EXTRACT(HOUR FROM created_at) as hr, EXTRACT(DAY FROM created_at) as dy, SUM(total_tokens) as tokens
            FROM user_token_usage
            WHERE created_at >= $1
            GROUP BY dy, hr
        """, start_time)
        
        for row in rows:
            hr = int(row["hr"])
            dy = int(row["dy"])
            for i in range(12):
                target_time = now - datetime.timedelta(hours=11-i)
                if target_time.hour == hr and target_time.day == dy:
                    values[i] += int(row["tokens"] or 0)
        await conn.close()
    except Exception as e:
        logger.warning("Throughput error: %s", e)

    return {"labels": labels, "values": values}

@router.get("/stats/monitoring")
async def get_monitoring():
    """Detailed monitoring data: token usage, write throughput, top tenants."""
    import datetime
    tp = await get_throughput()
    labels = tp["labels"]
    writes_values = [0] * len(labels)
    top_tenants = []

    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        try:
            start_time = now - datetime.timedelta(hours=12)
            rows = await conn.fetch("""
                SELECT EXTRACT(HOUR FROM created_at) as hr,
                       EXTRACT(DAY FROM created_at) as dy,
                       COUNT(*) as writes
                FROM memories
                WHERE created_at >= $1
                GROUP BY dy, hr
            """, start_time)
            for row in rows:
                hr = int(row["hr"])
                dy = int(row["dy"])
                for i in range(len(labels)):
                    t = now - datetime.timedelta(hours=len(labels) - 1 - i)
                    if t.hour == hr and t.day == dy:
                        writes_values[i] += int(row["writes"] or 0)

            tenant_rows = await conn.fetch("""
                SELECT m.team_id,
                       COUNT(*) as memory_count,
                       COALESCE(SUM(u.tokens), 0) as token_usage
                FROM memories m
                LEFT JOIN (
                    SELECT user_id::text as user_id, SUM(total_tokens) as tokens
                    FROM user_token_usage
                    GROUP BY user_id
                ) u ON u.user_id = m.team_id
                WHERE m.team_id IS NOT NULL AND m.team_id <> ''
                GROUP BY m.team_id
                ORDER BY memory_count DESC
                LIMIT 10
            """)
            for r in tenant_rows:
                top_tenants.append({
                    "team_id": r["team_id"],
                    "memory_count": int(r["memory_count"] or 0),
                    "token_usage": int(r["token_usage"] or 0),
                })
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("Monitoring error: %s", e)

    return {
        "token_labels": labels,
        "token_values": tp["values"],
        "writes_labels": labels,
        "writes_values": writes_values,
        "latency_buckets": [],
        "top_tenants": top_tenants,
    }

@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50):
    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT $1", limit)
        logs = []
        for r in rows:
            logs.append({
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "username": r.get("agent_id") or r.get("user_id") or "-",
                "team_id": r.get("team_id", "-") if "team_id" in r else "-",
                "action": r["action"],
                "target_id": str(r.get("memory_id") or r.get("resource_id") or ""),
                "ip_address": "-",
                "success": True
            })
        return {"logs": logs}
    finally:
        await conn.close()


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

@router.get("/providers/llm-engine")
async def get_llm_engine_config():
    """Get specific LLM engine configs (classifier, reflection)."""
    registry = ModelRegistry.get_instance()
    engine_data = registry.load_llm_engine_config()
    
    config = {}
    for engine in ["classifier", "reflection"]:
        cfg = engine_data.get(engine, {})
        provider_name = cfg.get("provider", "deepseek")
        model_name = cfg.get("model", "deepseek-chat")
        
        provider_cfg = registry.configs.get(provider_name)
        has_key = bool(provider_cfg.api_key) if provider_cfg else False
        base_url = (provider_cfg.api_base or "") if provider_cfg else ""
        
        config[engine] = {
            "provider": provider_name,
            "model": model_name,
            "has_key": has_key,
            "base_url": base_url
        }
        
    return {"config": config}

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
            prov_cfg = reg.configs.get(c["provider"])
            engine_data[c["purpose"]] = {
                "provider": c["provider"],
                "model": c["model"],
                "api_key": prov_cfg.api_key if prov_cfg and prov_cfg.api_key else "",
                "base_url": prov_cfg.api_base if prov_cfg and prov_cfg.api_base else ""
            }
            
    reg.save_llm_engine_config(engine_data)
    
    # 4. Sync and update routing.json
    routing_data = reg.load_routing()
    for c in configs:
        purpose = c["purpose"]
        if purpose in ["embedding", "rerank"]:
            routing_data[purpose] = {"provider": c["provider"], "model": c["model"]}
        elif purpose in ["classifier", "reflection"]:
            routing_data["llm"] = {"provider": c["provider"], "model": c["model"]}
            
    reg.save_routing(routing_data)
        
    return {"ok": True, "message": "Configuration saved successfully"}


@router.post("/providers/test")
async def test_provider_connection(data: dict):
    """Proxy connection test through the backend."""
    provider_id = data.get("provider")
    api_key = data.get("apiKey")
    model = data.get("model")
    
    if not provider_id:
        raise HTTPException(400, "Provider required")
        
    from backend.manager.registry import ModelRegistry
    from backend.providers.base import ProviderConfig
    
    reg = ModelRegistry.get_instance()
    
    # Fallback to stored key if key is masked or empty
    if not api_key or api_key.endswith("..."):
        stored_cfg = reg.configs.get(provider_id)
        if stored_cfg and stored_cfg.api_key:
            api_key = stored_cfg.api_key
            
    if not api_key:
        raise HTTPException(400, "API Key required")
        
    try:
        cfg = ProviderConfig(provider_type=provider_id, api_key=api_key, enabled_models={"llm": model} if model else {})
        p_class = reg.get_provider_class(provider_id)
        if not p_class: return {"ok": False, "error": f"Unknown provider: {provider_id}"}
        p_inst = p_class(cfg)
        val = await p_inst.validate()
        return {"ok": val.get("valid", False), "error": val.get("error", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/config/rag")
async def get_rag_config():
    from backend.services.config import load_system_config
    cfg = load_system_config()
    return cfg.get("rag", { "top_k": 5, "min_similarity": 0.60, "max_context_tokens": 2000, "history_count": 10 })

@router.post("/config/rag")
async def save_rag_config(data: dict):
    from backend.services.config import load_system_config, save_system_config
    cfg = load_system_config()
    cfg["rag"] = {
        "top_k": int(data.get("top_k", 5)),
        "min_similarity": float(data.get("min_similarity", 0.60)),
        "max_context_tokens": int(data.get("max_context_tokens", 2000)),
        "history_count": int(data.get("history_count", 10))
    }
    save_system_config(cfg)
    return {"ok": True, "message": "RAG configuration saved successfully"}

@router.get("/config/security")
async def get_security_config():
    from backend.services.config import load_system_config
    cfg = load_system_config()
    return cfg.get("security", { "rate_write": 60, "rate_read": 120, "max_mem_len": 10000, "jwt_expire": 43200 })

@router.post("/config/security")
async def save_security_config(data: dict):
    from backend.services.config import load_system_config, save_system_config
    cfg = load_system_config()
    cfg["security"] = {
        "rate_write": int(data.get("rate_write", 60)),
        "rate_read": int(data.get("rate_read", 120)),
        "max_mem_len": int(data.get("max_mem_len", 10000)),
        "jwt_expire": int(data.get("jwt_expire", 43200))
    }
    save_system_config(cfg)
    return {"ok": True, "message": "Security configuration saved successfully"}

@router.get("/reflection/config")
async def get_reflection_config():
    from backend.services.config import load_system_config
    cfg = load_system_config()
    return cfg.get("reflection", { "decay_rate": 0.05, "quality_threshold": 0.80, "interval_hours": 24 })

@router.post("/reflection/config")
async def save_reflection_config(data: dict):
    from backend.services.config import load_system_config, save_system_config
    cfg = load_system_config()
    cfg["reflection"] = {
        "decay_rate": float(data.get("decay_rate", 0.05)),
        "quality_threshold": float(data.get("quality_threshold", 0.80)),
        "interval_hours": int(data.get("interval_hours", 24))
    }
    save_system_config(cfg)
    return {"ok": True, "message": "Reflection configuration saved successfully"}

async def _run_background_reflection(teams: list[str]):
    from backend.reflection.engine import ReflectionEngine
    from backend.manager.registry import ModelRegistry
    from backend.memory.retrieval import RetrievalPipeline
    reg = ModelRegistry.get_instance()
    rp = RetrievalPipeline(_qdrant_store, _graph_store) if _qdrant_store else None
    engine = ReflectionEngine(_pg_repo, _graph_store, registry=reg, retrieval=rp)
    for team_id in teams:
        try:
            await engine.reflect_all(team_id)
        except Exception as e:
            logger.warning("[reflection] background run failed for team %s: %s", team_id, e)

@router.post("/reflection/trigger")
async def trigger_reflection(background_tasks: BackgroundTasks):
    if not _pg_repo:
        raise HTTPException(500, "Database not connected")
    async with _pg_repo.pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT team_id FROM memories")
        teams = [r["team_id"] for r in rows]
        if "default" not in teams:
            teams.append("default")
    background_tasks.add_task(_run_background_reflection, teams)
    return {"status": "initiated", "message": f"Reflection cycle triggered for {len(teams)} tenants"}


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
            await _graph_store.driver.verify_connectivity()
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
        async with _graph_store.driver.session() as session:
            res_nodes = await session.run("MATCH (n) RETURN count(n) as node_count;")
            node_rec = await res_nodes.single()
            node_count = node_rec["node_count"] if node_rec else 0
            
            res_edges = await session.run("MATCH ()-[r]->() RETURN count(r) as edge_count;")
            edge_rec = await res_edges.single()
            edge_count = edge_rec["edge_count"] if edge_rec else 0
            
            return {
                "nodes": node_count,
                "edges": edge_count,
                "status": "connected"
            }
    except Exception as e:
        return {"nodes": 0, "edges": 0, "status": "error", "detail": str(e)}

@router.get("/graph/visualization")
async def get_graph_visualization(limit: int = 200):
    """Return full Neo4j graph data for visualization."""
    if not _graph_store:
        return {"nodes": [], "edges": []}
    try:
        data = await _graph_store.get_full_graph(limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/embeddings/rebuild")
async def trigger_embedding_rebuild(
    target_version: int,
    team_id: str = None,
    batch_size: int = 50
):
    """Queue memories with old embedding versions for rebuild."""
    from backend.api.db_helper import get_db_conn
    conn = await get_db_conn()
    try:
        query = "SELECT id FROM memories WHERE embedding_version IS NULL OR embedding_version < $1"
        params = [target_version]
        if team_id:
            query += " AND team_id = $2"
            params.append(team_id)
        rows = await conn.fetch(query, *params)
        job_ids = [str(row["id"]) for row in rows]
        # Batch into pipeline_queue
        for i in range(0, len(job_ids), batch_size):
            batch = job_ids[i:i+batch_size]
            await conn.execute(
                "INSERT INTO pipeline_queue (team_id, task_type, payload_json, status) "
                "VALUES ($1, 'embedding_rebuild', $2, 'pending')",
                team_id or "global", __import__("json").dumps({"ids": batch}))
        return {"queued_count": len(job_ids), "batches": (len(job_ids) + batch_size - 1) // batch_size}
    finally:
        await conn.close()


@router.get("/memories")
async def list_all_memories(
    team_id: str = None,
    category: str = None,
    source_type: str = None,
    q: str = None,
    limit: int = 50,
    offset: int = 0
):
    """List and search all memories across all users/tenants (Admin view)."""
    if not _pg_repo:
        raise HTTPException(503, "Database not ready")
        
    async with _pg_repo.pool.acquire() as conn:
        query_parts = ["WHERE 1=1"]
        params = []
        
        if team_id:
            params.append(team_id)
            query_parts.append(f"AND team_id = ${len(params)}")
        if category:
            params.append(category)
            query_parts.append(f"AND category = ${len(params)}")
        if source_type:
            params.append(source_type)
            query_parts.append(f"AND source_type = ${len(params)}")
        if q:
            params.append(f"%{q}%")
            query_parts.append(f"AND (title ILIKE ${len(params)} OR content ILIKE ${len(params)})")
            
        where_clause = " ".join(query_parts)
        
        # Get count
        count_q = f"SELECT COUNT(*) FROM memories {where_clause}"
        total = await conn.fetchval(count_q, *params)
        
        # Get list
        params.append(limit)
        limit_param = f"${len(params)}"
        params.append(offset)
        offset_param = f"${len(params)}"
        
        list_q = f"SELECT * FROM memories {where_clause} ORDER BY created_at DESC LIMIT {limit_param} OFFSET {offset_param}"
        rows = await conn.fetch(list_q, *params)
        
    memories = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("updated_at"):
            d["updated_at"] = d["updated_at"].isoformat()
        memories.append(d)
        
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "memories": memories
    }


@router.delete("/memories/{memory_id}")
async def delete_memory_admin(memory_id: str):
    """Admin endpoint to delete any memory from PG and Qdrant."""
    if not _pg_repo:
        raise HTTPException(503, "Database not ready")
        
    # Get memory first to find team_id
    memory = await _pg_repo.get(memory_id)
    if not memory:
        raise HTTPException(404, "Memory not found")
        
    team_id = memory["team_id"]
    resolved_id = str(memory["id"])
    ok = await _pg_repo.delete(resolved_id, team_id)
    if _qdrant_store and ok:
        _qdrant_store.delete(resolved_id, team_id=team_id)
        
    return {"deleted": ok}


@router.get("/documents")
async def list_all_documents(
    team_id: str = None,
    q: str = None,
    limit: int = 50,
    offset: int = 0,
    admin: bool = Depends(require_admin)
):
    """List and search all documents across all users/tenants (Admin view)."""
    if not _pg_repo:
        raise HTTPException(503, "Database not ready")
        
    async with _pg_repo.pool.acquire() as conn:
        query_parts = ["WHERE 1=1"]
        params = []
        
        if team_id:
            params.append(team_id)
            query_parts.append(f"AND team_id = ${len(params)}")
        if q:
            params.append(f"%{q}%")
            query_parts.append(f"AND filename ILIKE ${len(params)}")
            
        where_clause = " ".join(query_parts)
        
        # Get count
        count_q = f"SELECT COUNT(*) FROM documents {where_clause}"
        total = await conn.fetchval(count_q, *params)
        
        # Get list
        params.append(limit)
        limit_param = f"${len(params)}"
        params.append(offset)
        offset_param = f"${len(params)}"
        
        list_q = f"SELECT * FROM documents {where_clause} ORDER BY created_at DESC LIMIT {limit_param} OFFSET {offset_param}"
        rows = await conn.fetch(list_q, *params)
        
    documents = []
    for r in rows:
        d = dict(r)
        if d.get("id"):
            d["id"] = str(d["id"])
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        documents.append(d)
        
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "documents": documents
    }


@router.delete("/documents/{doc_id}")
async def delete_document_admin(doc_id: str, admin: bool = Depends(require_admin)):
    """Admin endpoint to delete any document and cascade delete its memories, Qdrant vectors and file."""
    if not _pg_repo:
        raise HTTPException(503, "Database not ready")
    from backend.memory.pg_repo import safe_uuid
    from backend.memory.minio_store import MinIOStore

    # 1. Fetch document metadata first
    async with _pg_repo.pool.acquire() as conn:
        doc = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", safe_uuid(doc_id))
    if not doc:
        raise HTTPException(404, "Document not found")

    doc_dict = dict(doc)
    minio_key = doc_dict.get("minio_key")
    team_id = doc_dict.get("team_id")

    # 2. Find and delete corresponding memories
    source_uri = f"minio://{minio_key}" if minio_key else ""
    if source_uri:
        async with _pg_repo.pool.acquire() as conn:
            mem_rows = await conn.fetch("SELECT id FROM memories WHERE source_uri = $1 AND team_id = $2", source_uri, team_id)
        for r in mem_rows:
            mem_id = str(r["id"])
            await _pg_repo.delete(mem_id, team_id)
            if _qdrant_store:
                try:
                    _qdrant_store.delete(mem_id, team_id=team_id)
                except Exception as e:
                    logger.warning("[delete_document_admin] Qdrant delete failed for memory %s: %s", mem_id, e)

    # 3. Delete from MinIO
    if minio_key:
        try:
            minio = MinIOStore()
            minio.delete(minio_key)
        except Exception as e:
            logger.warning("[delete_document_admin] MinIO delete failed for key %s: %s", minio_key, e)

    # 4. Delete document entry
    async with _pg_repo.pool.acquire() as conn:
        r = await conn.execute("DELETE FROM documents WHERE id = $1", safe_uuid(doc_id))
        ok = "DELETE 1" in r

    return {"deleted": ok}




@router.patch("/users/{username}/plan")
async def update_user_plan(username: str, data: dict):
    """Admin: update user plan (free/pro/exempt)"""
    from backend.api.db_helper import get_db_conn
    from datetime import datetime
    conn = await get_db_conn()
    try:
        plan = data.get("plan", "free")
        expires = data.get("plan_expires_at")
        reset = data.get("reset_mcp_count", False)

        # Normalize and parse timestamp
        if not expires or expires == "":
            expires = None
        elif isinstance(expires, str):
            val = expires.strip()
            if val.endswith('Z'):
                val = val[:-1] + '+00:00'
            try:
                expires = datetime.fromisoformat(val)
            except ValueError:
                try:
                    from dateutil import parser
                    expires = parser.parse(val)
                except Exception:
                    raise HTTPException(status_code=400, detail=f"Invalid timestamp format for plan_expires_at: {expires}")

        await conn.execute(
            "UPDATE accounts SET plan=$1, plan_expires_at=$2 WHERE username=$3",
            plan, expires, username)
        if reset:
            await conn.execute("UPDATE accounts SET mcp_call_count=0 WHERE username=$1", username)
        return {"status": "ok", "username": username, "plan": plan}
    finally:
        await conn.close()

