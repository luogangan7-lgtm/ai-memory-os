"""Pipeline runner
from backend.memory.pg_repo import safe_uuid
 with queue-based high-concurrency support."""
from __future__ import annotations
import asyncio, logging, os
from backend.memory.pg_repo import MemoryRepo

logger = logging.getLogger("pipeline")
_repo: MemoryRepo | None = None
_cpu = os.cpu_count() or 4
_concurrency = int(os.getenv("PIPELINE_CONCURRENCY", str(_cpu * 4)))
_team_locks: dict[str, asyncio.Lock] = {}

def init(repo: MemoryRepo):
    global _repo; _repo = repo
    import backend.pipeline.l0_recorder as l0; l0.init(repo)
    import backend.pipeline.l1_extractor as l1; l1.init(repo)
    import backend.pipeline.l2_synthesizer as l2; l2.init(repo)
    import backend.pipeline.l3_persona as l3; l3.init(repo)

async def enqueue(team_id: str, session_id: str, messages: list[dict]) -> int | None:
    if _repo is None: return None
    from backend.pipeline.l0_recorder import record_conversation
    conv_id = await record_conversation(team_id, session_id, messages)
    if not conv_id: return None

    import json
    payload_json = json.dumps({"session_id": session_id, "conv_id": conv_id}, ensure_ascii=False)
    row = await _repo.pool.fetchrow(
        """INSERT INTO pipeline_queue (team_id, task_type, payload_json, status, created_at)
           VALUES ($1, 'memory_pipeline', $2::jsonb, 'pending', NOW()) RETURNING id""",
        team_id, payload_json
    )
    return row["id"] if row else None

async def _process_one(row):
    qid = row["id"]
    team = row["team_id"]
    task_type = row["task_type"]
    
    await _repo.pool.execute(
        "UPDATE pipeline_queue SET status='processing', started_at=NOW() WHERE id=$1", qid
    )
    
    lock = _team_locks.setdefault(team, asyncio.Lock())
    async with lock:
        try:
            if task_type == 'memory_pipeline':
                print(f"[pipeline-DEBUG] processing qid={qid} team={team}", flush=True)
                # Check if the user has an active LLM config
                has_llm = False
                from backend.api.user_providers import _user_llm_configs
                from backend.pipeline.llm_client import _DEFAULT_BASES
                user_cfg = _user_llm_configs.get(team, {})

                # A config is valid if it has an api_key AND either
                # an explicit base_url OR the provider has a known default base URL.
                def _cfg_valid(c: dict) -> bool:
                    key = c.get("api_key", "")
                    if not key:
                        return False
                    base = c.get("base_url", "") or ""
                    if base:
                        return True
                    provider = (c.get("provider") or "").lower()
                    return provider in _DEFAULT_BASES

                if _cfg_valid(user_cfg):
                    has_llm = True
                else:
                    try:
                        cfg = await _repo.get_active_user_provider_config(team)
                        if cfg and cfg.get("api_key"):
                            from backend.utils.crypto import decrypt
                            raw_key = cfg.get("api_key", "")
                            try:
                                raw_key = decrypt(raw_key) or raw_key
                            except Exception:
                                pass
                            cached_cfg = {
                                "provider": cfg.get("provider_name", ""),
                                "model": cfg.get("model_name", ""),
                                "api_key": raw_key,
                                "base_url": cfg.get("api_base_url", "") or "",
                            }
                            if _cfg_valid(cached_cfg):
                                has_llm = True
                                _user_llm_configs[team] = cached_cfg
                                _user_llm_configs[str(safe_uuid(team))] = cached_cfg
                    except Exception as e:
                        logger.warning(f"[runner] Failed to load user provider config for {team}: {e}")

                # Fallback: try any active config if team-specific lookup failed
                print(f"[pipeline-DEBUG] has_llm={has_llm} team={team}", flush=True)
                if not has_llm:
                    try:
                        rows = await _repo.pool.fetch(
                            "SELECT * FROM user_provider_configs WHERE is_active=true AND api_key IS NOT NULL AND api_key != '' AND (user_id=$1 OR user_id=$2) ORDER BY updated_at DESC LIMIT 1",
                            team, str(safe_uuid(team))
                        )
                        if rows:
                            r = dict(rows[0])
                            from backend.utils.crypto import decrypt
                            raw_key = r.get("api_key", "")
                            try: raw_key = decrypt(raw_key) or raw_key
                            except: pass
                            fallback = {
                                "provider": r.get("provider_name", ""),
                                "model": r.get("model_name", ""),
                                "api_key": raw_key,
                                "base_url": r.get("api_base_url", "") or "",
                            }
                            if _cfg_valid(fallback):
                                has_llm = True
                                _user_llm_configs[team] = fallback
                                _user_llm_configs[str(safe_uuid(team))] = fallback
                                logger.info(f"[runner] Using fallback LLM config for {team}: {fallback['provider']}/{fallback['model']}")
                    except Exception as e:
                        logger.warning(f"[runner] Fallback LLM lookup failed for {team}: {e}")

                print(f"[pipeline-DEBUG] has_llm={has_llm} team={team}", flush=True)
                if not has_llm:
                    logger.info(f"User {team} has no active LLM config. Pausing pipeline task {qid} with 'waiting_key' status.")
                    await _repo.pool.execute(
                        "UPDATE pipeline_queue SET status='waiting_key', started_at=NULL WHERE id=$1", qid
                    )
                    return

                import json
                payload = json.loads(row["payload_json"]) if isinstance(row["payload_json"], str) else row["payload_json"]
                conv_id = payload.get("conv_id")
                session_id = payload.get("session_id", "")
                if conv_id:
                    from backend.pipeline.l1_extractor import extract_from_conversation, store_facts
                    facts, l1_tokens = await extract_from_conversation(conv_id, team)
                    if facts:
                        if hasattr(_repo, 'increment_pipeline_usage'):
                            await _repo.increment_pipeline_usage(team, 'L1', l1_tokens)
                        aids = await store_facts(team, facts, session_id)
                        
                        from backend.pipeline.l2_synthesizer import synthesize
                        from backend.pipeline.l3_persona import generate
                        
                        async def run_l2():
                            _, l2_tokens = await synthesize(team, aids)
                            if hasattr(_repo, 'increment_pipeline_usage'):
                                await _repo.increment_pipeline_usage(team, 'L2', l2_tokens)
                                
                        async def run_l3():
                            _, l3_tokens = await generate(team)
                            if hasattr(_repo, 'increment_pipeline_usage'):
                                await _repo.increment_pipeline_usage(team, 'L3', l3_tokens)
                                
                        await asyncio.gather(run_l2(), run_l3(), return_exceptions=True)
            elif task_type == 'embedding_rebuild':
                # Rebuild embeddings for memory ids
                import json
                payload = json.loads(row["payload_json"]) if isinstance(row["payload_json"], str) else row["payload_json"]
                mids = payload.get("ids", [])
                if mids:
                    from backend.api.routes import ingestion, registry
                    if ingestion:
                        for mid in mids:
                            try:
                                mem = await _repo.pool.fetchrow("SELECT * FROM memories WHERE id = $1", mid)
                                if mem:
                                    await ingestion.ingest(
                                        content=mem["content"],
                                        memory_id=str(mem["id"]),
                                        team_id=mem["team_id"],
                                        workspace_id=mem["workspace_id"],
                                        embedding_fn=registry.embed_single,
                                        title=mem["title"],
                                        category=mem["category"],
                                        memory_type=mem["memory_type"],
                                        agent_id=mem.get("agent_id", "default")
                                    )
                            except Exception as ex:
                                logger.error(f"Failed to rebuild embedding for memory {mid}: {ex}")

            await _repo.pool.execute(
                "UPDATE pipeline_queue SET status='done', completed_at=NOW() WHERE id=$1", qid
            )
        except Exception as e:
            logger.error(f"Pipeline error processing row {qid}: {e}", exc_info=True)
            await _repo.pool.execute(
                "UPDATE pipeline_queue SET status='failed', completed_at=NOW() WHERE id=$1", qid
            )

import time
_last_zombie_check = 0

async def process_queue():
    """Background worker: parallel processing of pending tasks."""
    if _repo is None: return
    global _last_zombie_check
    while True:
        try:
            # Self-healing: recover tasks stuck in processing for >15 minutes
            now = time.time()
            if now - _last_zombie_check > 300: # Every 5 minutes
                _last_zombie_check = now
                res = await _repo.pool.execute(
                    "UPDATE pipeline_queue SET status='pending', started_at=NULL WHERE status='processing' AND started_at < NOW() - INTERVAL '15 minutes'"
                )
                if res and res != "UPDATE 0":
                    logger.warning(f"Recovered zombie pipeline tasks: {res}")

            rows = await _repo.pool.fetch(
                "SELECT * FROM pipeline_queue WHERE status='pending' ORDER BY created_at LIMIT $1", _concurrency)
            if not rows:
                await asyncio.sleep(3); continue
            tasks = [asyncio.create_task(_process_one(r)) for r in rows]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Queue processor error: {e}", exc_info=True)
            await asyncio.sleep(5)


_background_task: asyncio.Task | None = None

def start_worker():
    print('[pipeline] start_worker() called', flush=True)
    global _background_task
    if _background_task is None or _background_task.done():
        _background_task = asyncio.create_task(process_queue())
        logger.info(f"Pipeline worker started (up to {_concurrency} concurrent, per-team serialized)")


async def mark_dead(item_id: str, error: str, team_id: str):
    """Mark a pipeline job as dead after max retries."""
    try:
        from backend.api.db_helper import get_db_conn
        conn = await get_db_conn()
        await conn.execute(
            "UPDATE pipeline_queue SET status='dead', error_msg=$1, completed_at=NOW() WHERE id=$2",
            error, item_id)
        await conn.close()
        print(f"[pipeline] DEAD LETTER: job={item_id} team={team_id} error={error}")
    except Exception as e:
        print(f"[pipeline] Failed to mark dead: {e}")
