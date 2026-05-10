# AI Memory OS — Knowledge Internalization Service
# Automatically evaluates if personal memories should be promoted to Common Knowledge.

from __future__ import annotations
import logging
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
        async with self.pg.pool.acquire() as conn:
            # 1. Fetch recent agent memories that haven't been evaluated
            rows = await conn.fetch("""
                SELECT id, title, content, category, importance 
                FROM memories 
                WHERE source_type = 'agent' 
                AND (metadata->>'internalized')::boolean IS NOT TRUE
                LIMIT 50
            """)
            
            promoted_count = 0
            for r in rows:
                mid, content, importance = r["id"], r["content"], r["importance"]
                
                # 2. Quality & Redundancy Check
                # Skip very short memories (not enough knowledge density)
                if len(content) < str(settings.internalize_min_content_length) and importance < 0.8:
                    continue

                # Search existing public knowledge
                results = await self.retrieval.search(
                    query=content[:500], 
                    embedding_fn=self.registry.embed_single,
                    team_id=team_id,
                    source_type_filter="knowledge",
                    top_k=3
                )
                
                is_redundant = any(res["score"] > settings.internalize_similarity_threshold for res in results)
                is_valuable = importance > 0.5 or len(content) > 300
                
                if not is_redundant and is_valuable:
                    # 4. Promote to Knowledge with a small importance boost
                    new_importance = min(1.0, importance + 0.1)
                    logging.info(f"Internalizing memory {mid}: {r['title']}")
                    await conn.execute("""
                        UPDATE memories 
                        SET source_type = 'knowledge',
                            importance = $2,
                            metadata = metadata || '{"internalized": true, "internalized_at": "now"}'
                        WHERE id = $1
                    """, mid, new_importance)

                    promoted_count += 1
                else:
                    # Mark as evaluated but not promoted
                    await conn.execute("""
                        UPDATE memories 
                        SET metadata = metadata || '{"internalized": false}'
                        WHERE id = $1
                    """, mid)
            
            return promoted_count
