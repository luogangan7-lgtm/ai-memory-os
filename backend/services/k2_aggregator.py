"""K2 Knowledge Aggregator — merges related public knowledge via LLM semantic grouping."""
from __future__ import annotations
import uuid

from backend.memory.pg_repo import MemoryRepo
from backend.manager.registry import ModelRegistry
import json, re

async def aggregate_public_knowledge(repo: MemoryRepo) -> int:
    merged = 0
    try:
        async with repo.pool.acquire() as conn:
            all_rows = await conn.fetch("""
                SELECT id, title, content FROM memories 
                WHERE team_id = 'public' AND topic != 'merged'
                ORDER BY created_at DESC LIMIT 20
            """)
            if len(all_rows) < 2:
                return 0

            # Phase 1: LLM semantic grouping by title
            titles = [str(i) + ": " + r["title"][:80] for i, r in enumerate(all_rows)]
            title_list = "\n".join(titles)
            group_prompt = 'Group these titles by topic similarity. Return ONLY JSON: {"groups": [[0,3], [1,2,5], ...]}. Only groups of 2+. Skip unrelated.\n\n' + title_list
            
            registry = ModelRegistry.get_instance()
            print(f"[K2] Phase 1: sending {len(all_rows)} titles to classifier...")
            result = await registry.chat_for_engine("classifier", [{"role": "user", "content": group_prompt}])
            print(f"[K2] Phase 1 result: {repr(result)[:200]}")
            if not result:
                return 0
            
            # Parse LLM response for groups
            try:
                groups = json.loads(result).get("groups", [])
            except:
                m = re.search(r'\{[^{}]*"groups"\s*:\s*\[[^\]]+\][^\}]*\}', result)
                groups = json.loads(m.group()).get("groups", []) if m else []
            
            if not groups:
                return 0
            
            # Phase 2: Merge each group
            for group_ids in groups:
                if len(group_ids) < 2:
                    continue
                items = [(all_rows[int(i)]["id"], all_rows[int(i)]["title"], all_rows[int(i)]["content"]) 
                         for i in group_ids if i < len(all_rows)]
                if len(items) < 2:
                    continue
                
                pieces = "\n---\n".join(f"## {t}\n{c[:500]}" for _, t, c in items)
                merge_prompt = "Merge these related knowledge entries into ONE article. Keep all facts, remove duplicates:\n\n" + pieces
                
                print(f"[K2] Phase 2: merging {len(items)} entries...")
                merged_text = await registry.chat_for_engine("reflection", [{"role": "user", "content": merge_prompt}])
                if not merged_text:
                    continue
                
                mid = uuid.uuid4()
                merged_title = merged_text.split("\n")[0][:100]
                await conn.execute("""
                    INSERT INTO memories (id, team_id, title, content, source_type, lifecycle_stage, topic, importance, category)
                    VALUES ($1, 'public', $2, $3, 'knowledge', 'longterm', 'merged', 0.9, 'knowledge')
                """, mid, merged_title[:100], merged_text[:5000])
                
                for old_id, _, _ in items:
                    await conn.execute(
                        "UPDATE memories SET importance = importance * 0.3, metadata = metadata || jsonb_build_object('merged_into', $1::text) WHERE id = $2",
                        mid, old_id)
                
                merged += 1
                print(f"[K2] Merged {len(items)} entries -> {mid}: {merged_title[:50]}")
        
        return merged
    except Exception as e:
        import traceback
        print(f"[K2] Failed: {e}")
        traceback.print_exc()
        return 0
