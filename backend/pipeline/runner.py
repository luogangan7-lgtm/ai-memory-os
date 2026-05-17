"""Pipeline runner: orchestrates L0→L1→L2→L3 processing."""
from __future__ import annotations
import asyncio, logging
from backend.memory.pg_repo import MemoryRepo
from backend.pipeline.l0_recorder import record_conversation
from backend.pipeline.l1_extractor import extract_from_conversation, store_facts
from backend.pipeline.l2_synthesizer import synthesize
from backend.pipeline.l3_persona import generate

logger = logging.getLogger("pipeline")
_repo: MemoryRepo | None = None

def init(repo: MemoryRepo):
    global _repo
    _repo = repo
    import backend.pipeline.l0_recorder as l0; l0.init(repo)
    import backend.pipeline.l1_extractor as l1; l1.init(repo)
    import backend.pipeline.l2_synthesizer as l2; l2.init(repo)
    import backend.pipeline.l3_persona as l3; l3.init(repo)

async def process_conversation(team_id: str, session_id: str, messages: list[dict]) -> list[str]:
    logger.info(f"Pipeline L0→L3 started for {team_id}/{session_id}")
    conv_id = await record_conversation(team_id, session_id, messages)
    if not conv_id: return []
    
    facts = await extract_from_conversation(conv_id, team_id)
    if not facts:
        await _repo.pool.execute(
            "UPDATE pipeline_conversations SET processed_l1=TRUE WHERE id=$1", conv_id)
        return []
    
    atom_ids = await store_facts(team_id, facts, session_id)
    await _repo.pool.execute(
        "UPDATE pipeline_conversations SET processed_l1=TRUE WHERE id=$1", conv_id)
    
    _ = asyncio.create_task(synthesize(team_id, atom_ids))
    _ = asyncio.create_task(generate(team_id))
    
    logger.info(f"Pipeline L0→L1 done for {team_id}/{session_id} ({len(facts)} facts, L2/L3 async)")
    return atom_ids
