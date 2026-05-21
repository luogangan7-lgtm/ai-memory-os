"""User Provider API — per-user LLM config for pipeline usage."""
from fastapi import APIRouter, HTTPException, Depends
from backend.auth.middleware import get_current_team
from backend.utils.crypto import encrypt, decrypt

router = APIRouter(prefix="/user/llm", tags=["user_llm"])
_user_llm_configs: dict[str, dict] = {}

@router.get("")
async def get_user_llm(team_id: str = Depends(get_current_team)):
    # Try DB first, fallback to memory
    try:
        from backend.api.routes import pg_repo
        if pg_repo:
            cfg = await pg_repo.get_active_user_provider_config(team_id)
            if cfg:
                return {
                    "provider": cfg.get("provider_name", ""),
                    "model": cfg.get("model_name", ""),
                    "has_key": True,
                    "api_key": decrypt(cfg.get("api_key", "")),
                    "base_url": cfg.get("api_base_url", "")
                }
    except Exception:
        pass
    # Fallback to in-memory
    cfg = _user_llm_configs.get(team_id, {})
    return {"provider": cfg.get("provider", ""), "model": cfg.get("model", ""), "has_key": bool(cfg.get("api_key"))}

@router.post("")
async def save_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    # Save to memory for pipeline access (store under both team_id string and UUID keys)
    cfg = {
        "provider": data.get("provider", ""),
        "model": data.get("model", ""),
        "api_key": data.get("api_key", ""),
        "base_url": data.get("base_url", ""),
    }
    _user_llm_configs[team_id] = cfg
    from backend.memory.pg_repo import safe_uuid
    _user_llm_configs[str(safe_uuid(team_id))] = cfg
    # Persist to database for proxy gateway
    try:
        from backend.api.routes import pg_repo
        if pg_repo:
            await pg_repo.save_user_provider_config(
                user_id=team_id,
                provider_name=data.get("provider", ""),
                api_key=encrypt(data.get("api_key", "")),
                api_base_url=data.get("base_url", ""),
                model_name=data.get("model", ""),
                is_active=True
            )
    except Exception as e:
        print(f"save_user_provider_config failed: {e}")

    # Check if there are any pending memories for this user
    try:
        from backend.api.routes import pg_repo
        from backend.pipeline.runner import enqueue as enqueue_pipeline
        import asyncio
        if pg_repo and pg_repo.pool:
            async with pg_repo.pool.acquire() as conn:
                rows = await conn.fetch("SELECT id, content FROM memories WHERE team_id=$1 AND (source_type='human' OR memory_type='chat') AND metadata->>'pending_pipeline' = 'true'", team_id)
                for r in rows:
                    asyncio.create_task(
                        enqueue_pipeline(
                            team_id=team_id,
                            session_id=team_id,
                            messages=[{"role": "user", "content": r["content"]}]
                        )
                    )
                    await conn.execute("UPDATE memories SET metadata = jsonb_set(metadata, '{pending_pipeline}', 'false'::jsonb) WHERE id=$1", r["id"])
    except Exception as e:
        print(f"Failed to enqueue pending memories: {e}")

    # Update waiting_key tasks in pipeline_queue to pending
    try:
        from backend.api.routes import pg_repo
        from backend.memory.pg_repo import safe_uuid
        if pg_repo:
            if hasattr(pg_repo, "db_path"):  # SQLite
                import aiosqlite
                async with aiosqlite.connect(pg_repo.db_path) as db:
                    await db.execute(
                        "UPDATE pipeline_queue SET status='pending' WHERE (team_id=? OR team_id=?) AND status='waiting_key'",
                        (team_id, str(safe_uuid(team_id)))
                    )
                    await db.commit()
            elif pg_repo.pool:  # PostgreSQL
                async with pg_repo.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE pipeline_queue SET status='pending' WHERE (team_id=$1 OR team_id=$2) AND status='waiting_key'",
                        team_id, str(safe_uuid(team_id))
                    )
    except Exception as e:
        print(f"Failed to resume waiting_key tasks: {e}")

    return {"status": "saved", "team_id": team_id}

@router.post("/test")
async def test_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    import httpx
    key = data.get("api_key", "")
    base = data.get("base_url", "")
    model = data.get("model", "")
    if not key or not base:
        raise HTTPException(400, "API Key and Base URL required")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{base}/chat/completions", json={
                "model": model, "messages": [{"role":"user","content":"hi"}], "max_tokens":5
            }, headers={"Authorization": f"Bearer {key}"})
            return {"connected": r.status_code == 200, "status": r.status_code}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.get("/pipeline/status")
async def get_pipeline_status(team_id: str = Depends(get_current_team)):
    """Return current team's L1→L3 pipeline job status.

    Shape:
      {
        counts: {pending, processing, done, failed, dead},
        recent: [{id, status, task_type, created_at, started_at, completed_at, error_msg}],
        last_completed_at, last_failed_at,
        in_flight: int,
        configured: bool   # whether the user has an LLM saved
      }
    """
    from backend.api.db_helper import get_db_conn

    configured = team_id in _user_llm_configs
    if not configured:
        try:
            from backend.api.routes import pg_repo
            if pg_repo:
                cfg = await pg_repo.get_active_user_provider_config(team_id)
                configured = bool(cfg)
        except Exception:
            pass

    counts = {"pending": 0, "processing": 0, "done": 0, "failed": 0, "dead": 0}
    recent: list[dict] = []
    last_completed_at = None
    last_failed_at = None

    try:
        conn = await get_db_conn()
        try:
            since_rows = await conn.fetch(
                """SELECT status, COUNT(*) AS n
                   FROM pipeline_queue
                   WHERE team_id = $1 AND created_at >= NOW() - INTERVAL '24 hours'
                   GROUP BY status""",
                team_id,
            )
            for r in since_rows:
                s = (r["status"] or "").lower()
                if s in counts:
                    counts[s] = int(r["n"] or 0)

            # Pull recent jobs (any status) — newest first
            cols = [c["column_name"] for c in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name='pipeline_queue'")]
            has_err = "error_msg" in cols
            err_select = ", error_msg" if has_err else ""
            rows = await conn.fetch(
                f"""SELECT id, status, task_type, payload_json,
                           created_at, started_at, completed_at{err_select}
                    FROM pipeline_queue
                    WHERE team_id = $1
                    ORDER BY created_at DESC
                    LIMIT 20""",
                team_id,
            )
            for r in rows:
                recent.append({
                    "id": str(r["id"]),
                    "status": r["status"],
                    "task_type": r["task_type"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                    "error_msg": (r["error_msg"] if has_err else None),
                })

            row_lc = await conn.fetchrow(
                "SELECT MAX(completed_at) AS t FROM pipeline_queue WHERE team_id=$1 AND status='done'",
                team_id,
            )
            if row_lc and row_lc["t"]:
                last_completed_at = row_lc["t"].isoformat()
            row_lf = await conn.fetchrow(
                "SELECT MAX(completed_at) AS t FROM pipeline_queue WHERE team_id=$1 AND status IN ('failed','dead')",
                team_id,
            )
            if row_lf and row_lf["t"]:
                last_failed_at = row_lf["t"].isoformat()
        finally:
            await conn.close()
    except Exception as e:
        return {
            "counts": counts, "recent": [], "last_completed_at": None,
            "last_failed_at": None, "in_flight": 0,
            "configured": configured, "error": str(e),
        }

    return {
        "counts": counts,
        "recent": recent,
        "last_completed_at": last_completed_at,
        "last_failed_at": last_failed_at,
        "in_flight": counts["pending"] + counts["processing"],
        "configured": configured,
    }


async def warm_up_llm_configs():
    """服务启动时从 DB 加载用户 LLM 配置到内存."""
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        rows = await conn.fetch(
            "SELECT user_id, provider_name, api_key, model_name, api_base_url "
            "FROM user_provider_configs WHERE is_active = TRUE")
        
        # Build mapping from UUID to team_id
        accounts_rows = await conn.fetch("SELECT team_id FROM accounts")
        await conn.close()
        
        from backend.memory.pg_repo import safe_uuid
        uuid_to_team = {str(safe_uuid(r["team_id"])): r["team_id"] for r in accounts_rows}
        
        for row in rows:
            uid_str = str(row["user_id"])
            cfg = {
                "provider": row["provider_name"] or "",
                "api_key": decrypt(row["api_key"] or ""),
                "model": row["model_name"] or "",
                "base_url": row.get("api_base_url", "") or "",
            }
            # Store under both UUID and team_id keys for compatibility
            _user_llm_configs[uid_str] = cfg
            team_id = uuid_to_team.get(uid_str)
            if team_id:
                _user_llm_configs[team_id] = cfg
                
        print(f"[warm-up] Loaded {len(rows)} user LLM configs into memory")
    except Exception as e:
        print(f"[warm-up] Failed: {e}")

