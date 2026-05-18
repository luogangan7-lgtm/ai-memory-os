"""Pipeline runner with queue-based high-concurrency support."""
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

async def enqueue(team_id: str, session_id: str, messages: list[dict]) -> str | None:
    if _repo is None: return None
    import uuid
    qid = str(uuid.uuid4())
    await _repo.pool.execute(
        """INSERT INTO pipeline_queue (id, team_id, layer, input_ids, status)
           VALUES ($1, $2, 'L1', $3::uuid[], 'pending')""", qid, team_id, [qid])
    from backend.pipeline.l0_recorder import record_conversation
    cid = await record_conversation(team_id, session_id, messages)
    if cid:
        await _repo.pool.execute("UPDATE pipeline_queue SET input_ids=$1 WHERE id=$2", [cid], qid)
    return qid

async def _process_one(row):
    team, qid = row["team_id"], row["id"]
    await _repo.pool.execute("UPDATE pipeline_queue SET status='processing' WHERE id=$1", qid)
    lock = _team_locks.setdefault(team, asyncio.Lock())
    async with lock:
        try:
            cids = row["input_ids"] or []
            if cids:
                from backend.pipeline.l1_extractor import extract_from_conversation, store_facts
                facts = await extract_from_conversation(cids[0], team)
                if facts:
                    aids = await store_facts(team, facts, "")
                    from backend.pipeline.l2_synthesizer import synthesize
                    from backend.pipeline.l3_persona import generate
                    asyncio.create_task(synthesize(team, aids))
                    asyncio.create_task(generate(team))
            await _repo.pool.execute("UPDATE pipeline_queue SET status='done', finished_at=NOW() WHERE id=$1", qid)
        except Exception as e:
            retries = (row["retry_count"] or 0) + 1
            if retries <= 3:
                await _repo.pool.execute(
                    "UPDATE pipeline_queue SET status='pending', retry_count=$1, error_msg=$2 WHERE id=$3",
                    retries, str(e)[:500], qid)
            else:
                await _repo.pool.execute(
                    "UPDATE pipeline_queue SET status='failed', error_msg=$1, finished_at=NOW() WHERE id=$2",
                    str(e)[:500], qid)

async def process_queue():
    """Background worker: parallel processing of pending tasks."""
    if _repo is None: return
    while True:
        try:
            rows = await _repo.pool.fetch(
                "SELECT * FROM pipeline_queue WHERE status='pending' ORDER BY scheduled_at LIMIT $1", _concurrency)
            if not rows:
                await asyncio.sleep(3); continue
            tasks = [asyncio.create_task(_process_one(r)) for r in rows]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            await asyncio.sleep(5)

_background_task: asyncio.Task | None = None

def start_worker():
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
