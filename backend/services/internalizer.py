# AI Memory OS — Knowledge Internalization Service
# Automatically evaluates if personal memories should be promoted to Common Knowledge.

from __future__ import annotations
import logging
import json
from datetime import datetime, timezone
from backend.memory.pg_repo import MemoryRepo
from backend.services.config import settings
from backend.memory.retrieval import RetrievalPipeline
from backend.manager.registry import ModelRegistry

class InternalizationService:
    def __init__(self, pg: MemoryRepo, retrieval: RetrievalPipeline, registry: ModelRegistry):
        self.pg = pg
        self.retrieval = retrieval
        self.registry = registry

    async def evaluate_and_promote(self, team_id: str):
        """Scan recent agent memories and promote high-value, unique ones to knowledge."""
        # Database compatibility layer
        is_sqlite = hasattr(self.pg, "db_path")
        
        if is_sqlite:
            import aiosqlite
            db_conn = await aiosqlite.connect(self.pg.db_path)
            db_conn.row_factory = aiosqlite.Row
            cursor = await db_conn.execute("""
                SELECT id, title, content, category, importance, metadata 
                FROM memories 
                WHERE source_type IN ('agent', 'human', 'document') 
                AND (json_extract(metadata, '$.internalized') IS NOT TRUE)
                LIMIT 50
            """)
            rows = await cursor.fetchall()
        else:
            pool_conn = await self.pg.pool.acquire()
            rows = await pool_conn.fetch("""
                SELECT id, title, content, category, importance, metadata 
                FROM memories 
                WHERE source_type IN ('agent', 'human', 'document') 
                AND (metadata->>'internalized')::boolean IS NOT TRUE
                LIMIT 50
            """)

        promoted_count = 0
        try:
            for r in rows:
                mid, content, importance = r["id"], r["content"], r["importance"]
                
                # 2. Quality & Redundancy Check
                min_len = int(settings.internalize_min_content_length)
                if len(content) < min_len and importance < 0.8:
                    continue

                if not self.retrieval or not self.registry:
                    # If pipelines are missing (e.g. during simple reflection), skip deeper checks
                    is_redundant = False
                    is_valuable = importance > 0.7 and len(content) > 200
                else:
                    # Search existing public knowledge
                    results = await self.retrieval.search(
                        query=content[:500], 
                        embedding_fn=self.registry.embed_single,
                        team_id=team_id,
                        source_type_filter="knowledge",
                        top_k=3
                    )
                    is_redundant = any(res["score"] > settings.internalize_similarity_threshold for res in results)
                    is_valuable = importance > 0.7 and len(content) > 200
                
                if not is_redundant and is_valuable:
                    # 4. Promote to Knowledge with a small importance boost
                    new_importance = min(1.0, importance + 0.1)
                    logging.info(f"Internalizing memory {mid}: {r['title']}")
                    if is_sqlite:
                        # Update metadata in SQLite
                        meta = json.loads(r["metadata"]) if r["metadata"] else {}
                        meta["internalized"] = True
                        meta["internalized_at"] = datetime.now(timezone.utc).isoformat()
                        await db_conn.execute("""
                            UPDATE memories 
                            SET source_type = 'knowledge', importance = ?, metadata = ?,
                                team_id = 'public'
                            WHERE id = ?
                        """, (new_importance, json.dumps(meta), mid))
                    else:
                        await pool_conn.execute("""
                            UPDATE memories 
                            SET source_type = 'knowledge',
                                team_id = 'public',
                                importance = $2,
                                metadata = metadata || '{"internalized": true, "internalized_at": "now"}'
                            WHERE id = $1
                        """, mid, new_importance)

                    promoted_count += 1
                else:
                    # Mark as evaluated but not promoted
                    if is_sqlite:
                        meta = json.loads(r["metadata"]) if r["metadata"] else {}
                        meta["internalized"] = False
                        await db_conn.execute("UPDATE memories SET metadata = ? WHERE id = ?", (json.dumps(meta), mid))
                    else:
                        await pool_conn.execute("""
                            UPDATE memories 
                            SET metadata = metadata || '{"internalized": false}'
                            WHERE id = $1
                        """, mid)
            
            if is_sqlite: await db_conn.commit()
        finally:
            if is_sqlite: await db_conn.close()
            else: await self.pg.pool.release(pool_conn)
            
        return promoted_count
