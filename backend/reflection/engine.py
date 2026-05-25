import logging

import asyncio, httpx, os
from datetime import datetime, timezone
from typing import Any
from backend.services.internalizer import InternalizationService
from backend.memory.lifecycle import compute_freshness, compute_next_stage

class ReflectionEngine:
    def __init__(self, pg_repo, graph_store, registry=None, retrieval=None):
        self.pg, self.graph = pg_repo, graph_store
        self.registry = registry
        self.retrieval = retrieval

    async def reflect_all(self, team_id="default"):
        import logging
        logging.getLogger("reflection").info("Cycle start: %s", team_id)
        rpt = {"stage_transitions":0,"freshness_updated":0,"duplicates_found":0,"summaries":0,"relations_found":0}
        rpt["stage_transitions"] = await self._auto_transition(team_id)
        rpt["freshness_updated"] = await self._decay_freshness(team_id)
        rpt["summaries"] = await self._summarize(team_id)
        # Run internalization (evaluate agent memories for promotion)
        try:
            internalizer = InternalizationService(self.pg, self.retrieval if hasattr(self, 'retrieval') else None, self.registry)
            rpt["internalized"] = await internalizer.evaluate_and_promote(team_id)
        except Exception as e:
            print(f"DEBUG: Internalization failed: {e}")
            rpt["internalized"] = 0
        rpt["crossref_boosted"] = await self._verify_crossref(team_id)
        rpt["auto_promoted"] = await self._auto_promote(team_id)
        rpt["relations_found"] = await self._discover_relations(team_id)
        # K2: aggregate public knowledge
        from backend.services.k2_aggregator import aggregate_public_knowledge
        rpt["knowledge_merged"] = await aggregate_public_knowledge(self.pg)
        rpt["duplicates_found"] = await self._dedup(team_id)
        return rpt
        logging.getLogger("reflection").info("Cycle done: %s", str(rpt))

    async def _auto_transition(self, team_id):
        n=0
        async with self.pg.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id,lifecycle_stage,importance,confidence,access_count,created_at FROM memories WHERE team_id=$1",team_id)
            for r in rows:
                row = dict(r)
                ns = compute_next_stage(row, row.get("lifecycle_stage","recent"))
                if ns.value != row["lifecycle_stage"]:
                    await conn.execute(
                        "UPDATE memories SET lifecycle_stage=$1,freshness=$2,updated_at=$3 WHERE id=$4",
                        ns.value, compute_freshness(row), datetime.now(timezone.utc), row["id"])
                    n+=1
        return n

    async def _decay_freshness(self, team_id):
        n=0
        async with self.pg.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id,created_at FROM memories WHERE team_id=$1",team_id)
            for r in rows:
                row = dict(r)
                await conn.execute("UPDATE memories SET freshness=$1 WHERE id=$2",compute_freshness(row),row["id"]); n+=1
        return n

    async def _summarize(self, team_id):
        n=0
        async with self.pg.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id,content FROM memories WHERE team_id=$1 AND summary IS NULL AND length(content)>2000 LIMIT 3",team_id)
            for r in rows:
                try:
                    s = None
                    if self.registry:
                        try:
                            s = await self.registry.chat_for_engine("reflection", [
                                {"role":"system","content":"Summarize in 2-3 short sentences."},
                                {"role":"user","content":r["content"][:3000]}
                            ], max_tokens=150)
                        except Exception as e:
                            print(f"DEBUG: Registry chat_for_engine ('reflection') failed: {e}, falling back to Dashscope.", flush=True)

                    if not s:
                        async with httpx.AsyncClient(timeout=30) as cl:
                            resp = await cl.post(
                                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                                json={"model":"qwen-turbo","messages":[
                                    {"role":"system","content":"Summarize in 2-3 short sentences."},
                                    {"role":"user","content":r["content"][:3000]}
                                ],"max_tokens":150},
                                headers={"Authorization":"Bearer " + os.environ.get("DASHSCOPE_API_KEY", "") + ""})
                            if resp.status_code==200:
                                s=resp.json()["choices"][0]["message"]["content"]

                    if s:
                        await conn.execute("UPDATE memories SET summary=$1,updated_at=$2 WHERE id=$3",s,datetime.now(timezone.utc),r["id"]); n+=1
                except: pass
        return n

    async def _verify_crossref(self, team_id):
        """Boost importance of memories with graph relations."""
        n=0
        if not self.graph: return 0
        async with self.pg.pool.acquire() as conn:
            # Simple logic: if has > 0 relations in graph, importance += 0.1
            rows = await conn.fetch("SELECT id FROM memories WHERE team_id=$1 AND COALESCE(importance, 0.5) < 0.9", team_id)
            for r in rows:
                # This is a placeholder for a more complex graph query
                await conn.execute("UPDATE memories SET importance=importance+0.05 WHERE id=$1", r["id"])
                n += 1
        return n

    async def _auto_promote(self, team_id):
        """Auto-categorize high-value memories as 'knowledge'."""
        n = 0
        async with self.pg.pool.acquire() as conn:
            # Promote high importance + high access to 'knowledge' source_type
            res = await conn.execute(
                "UPDATE memories SET source_type='knowledge', updated_at=$1 "
                "WHERE team_id=$2 AND COALESCE(importance, 0.5) > 0.7 AND access_count > 5 AND (source_type IS NULL OR source_type != 'knowledge')",
                datetime.now(timezone.utc), team_id
            )
            if "UPDATE" in res: n = int(res.split(" ")[1])
        return n


    async def _discover_relations(self, team_id):
        logging.getLogger("reflection").info("Relations discovery start: %s", team_id)
        n=0
        async with self.pg.pool.acquire() as conn:
            # DB-level join: find pairs with same topic
            rows = await conn.fetch(
                "SELECT a.id as id_a, b.id as id_b, a.topic "
                "FROM memories a JOIN memories b ON a.topic=b.topic "
                "WHERE a.team_id=$1 AND b.team_id=$1 AND a.id < b.id AND a.topic IS NOT NULL LIMIT 100",
                team_id)
            for r in rows:
                if self.graph:
                    try:
                        # Ensure nodes exist before creating relation
                        await self.graph.create_memory_node(r["id_a"], "","","")
                        await self.graph.create_memory_node(r["id_b"], "","","")
                        await self.graph.create_relation(r["id_a"], r["id_b"], "same_topic", 0.7)
                        n += 1
                    except: pass
                    import traceback; logging.getLogger("reflection").warning("Relation failed: %s", traceback.format_exc())
        return n

    async def _dedup(self, team_id):
        n=0
        async with self.pg.pool.acquire() as conn:
            rows=await conn.fetch("SELECT title,COUNT(*) as cnt FROM memories WHERE team_id=$1 GROUP BY title HAVING COUNT(*)>1",team_id)
            for r in rows:
                dupes=await conn.fetch("SELECT id FROM memories WHERE team_id=$1 AND title=$2 ORDER BY created_at",team_id,r["title"])
                for d in dupes[:-1]:
                    await conn.execute("UPDATE memories SET importance=importance*0.5,updated_at=$1 WHERE id=$2",datetime.now(timezone.utc),d["id"]); n+=1
        return n

    async def _detect_gaps(self, team_id: str) -> list[dict]:
        """Detect knowledge gaps (categories or topics with low/no coverage or low confidence)."""
        async with self.pg.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT category, COUNT(*) as count, AVG(confidence) as avg_confidence "
                "FROM memories "
                "WHERE team_id=$1 "
                "GROUP BY category",
                team_id
            )
            gaps = []
            for r in rows:
                if r["count"] < 3 or (r["avg_confidence"] and r["avg_confidence"] < 0.6):
                    gaps.append({
                        "category": r["category"],
                        "count": r["count"],
                        "avg_confidence": float(r["avg_confidence"]) if r["avg_confidence"] is not None else 0.0,
                        "reason": "Low memory density" if r["count"] < 3 else "Low average confidence"
                    })
            return gaps
