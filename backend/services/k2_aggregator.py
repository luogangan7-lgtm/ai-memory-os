"""K2 Knowledge Aggregator — merges related public knowledge into composite entries."""
from __future__ import annotations
import logging
from backend.memory.pg_repo import MemoryRepo
from backend.pipeline.llm_client import call_llm

async def aggregate_public_knowledge(repo: MemoryRepo) -> int:
    """Find related public knowledge and merge via LLM into composite entries."""
    merged = 0
    try:
        async with repo.pool.acquire() as conn:
            # Find topics with 2+ public knowledge entries
            rows = await conn.fetch("""
                SELECT COALESCE(topic, category) as topic, array_agg(id) as ids, 
                       array_agg(content) as contents,
                       array_agg(title) as titles, count(*) as cnt
                FROM memories 
                WHERE team_id = 'public'
                GROUP BY COALESCE(topic, category) HAVING count(*) >= 2
                ORDER BY cnt DESC LIMIT 20
            """)
            
            for r in rows:
                if r["cnt"] < 2:
                    continue
                # Call LLM to merge
                pieces = []
                for t, c in zip(r["titles"], r["contents"]):
                    pieces.append(f"## {t}\n{c[:500]}")
                prompt = "Merge the following related knowledge entries into ONE comprehensive article. Keep all key facts, remove redundancy, organize logically:\n\n" + "\n---\n".join(pieces)
                
                result, tokens = await call_llm(prompt, "public", "reflection")
                if not result:
                    continue
                
                # Create merged entry
                merged_title = result.split("\n")[0][:100] if result else "Merged Knowledge"
                import uuid
                mid = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO memories (id, team_id, title, content, source_type, lifecycle_stage, topic, importance, category)
                    VALUES ($1, 'public', $2, $3, 'knowledge', 'longterm', 'merged', 0.9, 'knowledge')
                """, mid, merged_title[:100], result[:5000])
                
                # Mark originals as merged
                for old_id in r["ids"]:
                    await conn.execute("""
                        UPDATE memories SET importance = importance * 0.3, 
                        metadata = metadata || '{"merged_into": "$1"}'
                        WHERE id = $2
                    """, mid, old_id)
                
                merged += 1
                print(f"Merged {r['cnt']} entries into {mid}: {merged_title[:50]}")
        
        return merged
    except Exception as e:
        print(f"K2 aggregation failed: {e}")
        return 0
