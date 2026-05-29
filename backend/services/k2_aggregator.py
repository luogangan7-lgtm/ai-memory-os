"""K2 Knowledge Aggregator — topic splitting + semantic grouping for public knowledge pool.

Design:
  Phase 1 – LLM categorizes new knowledge into topics (real-time, on internalization)
  Phase 2 – When a topic exceeds SPLIT_THRESHOLD (20), LLM auto-splits into sub-topics
  Phase 3 – Periodic HDBSCAN full reclustering (weekly background job)
"""
from __future__ import annotations
import uuid

from backend.memory.pg_repo import MemoryRepo
from backend.manager.registry import ModelRegistry
import json, re

SPLIT_THRESHOLD = 20  # entries per topic before auto-split


def _parse_json(raw: str) -> dict:
    """Robust JSON extraction from LLM output."""
    if not raw:
        return {}
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        m = re.search(r'\{[^{}]*\}', raw)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {}


async def categorize_and_topic_knowledge(repo: MemoryRepo) -> dict:
    """Real-time topic categorization for newly internalized knowledge entries."""
    result = {"categorized": 0, "new_topics": 0, "errors": 0}
    try:
        registry = ModelRegistry.get_instance()
        if not registry:
            return result

        async with repo.pool.acquire() as conn:
            uncategorized = await conn.fetch(
                """SELECT id, title, content FROM memories
                   WHERE team_id = 'public' AND source_type = 'knowledge'
                     AND (topic IS NULL OR topic = '' OR topic = 'general')
                   ORDER BY created_at DESC LIMIT 30""")

            if not uncategorized:
                return result

            existing_topics = await conn.fetch(
                """SELECT DISTINCT topic FROM memories
                   WHERE team_id = 'public' AND topic IS NOT NULL
                     AND topic != '' AND topic != 'general' AND topic != 'merged'""")
            known_topics = [r["topic"] for r in existing_topics]

            for row in uncategorized:
                try:
                    topic_prompt = (
                        f'Assign to ONE existing topic or create new (max 15 chars).\n'
                        f'Existing: {json.dumps(known_topics or ["None yet"])}\n'
                        f'Title: {row["title"][:100]}\n'
                        f'Content: {(row["content"] or "")[:500]}\n'
                        f'Reply ONLY JSON: {{"topic":"...","action":"assign"|"create"}}')

                    raw = await registry.chat_for_engine("classifier",
                        [{"role": "user", "content": topic_prompt}])

                    if not raw:
                        continue

                    parsed = _parse_json(raw)
                    topic = (parsed.get("topic") or "general")[:30]
                    action = parsed.get("action", "assign")

                    await conn.execute(
                        "UPDATE memories SET topic=$1, category=$1 WHERE id=$2",
                        topic, str(row["id"]))

                    if action == "create" and topic not in known_topics:
                        known_topics.append(topic)
                        result["new_topics"] += 1

                    result["categorized"] += 1
                except Exception as e:
                    print(f"[K2 categorize] {row['id'][:8]}: {e}")
                    result["errors"] += 1

        return result
    except Exception as e:
        print(f"[K2 categorize] fatal: {e}")
        return result


async def split_oversized_topics(repo: MemoryRepo) -> dict:
    """Auto-split topics that exceed SPLIT_THRESHOLD into sub-topics."""
    result = {"scanned": 0, "split": 0}
    try:
        registry = ModelRegistry.get_instance()
        if not registry:
            return result

        async with repo.pool.acquire() as conn:
            topic_counts = await conn.fetch(
                """SELECT topic, COUNT(*) as cnt FROM memories
                   WHERE team_id = 'public' AND topic IS NOT NULL
                     AND topic != '' AND topic != 'general' AND topic != 'merged'
                   GROUP BY topic HAVING COUNT(*) >= $1""",
                SPLIT_THRESHOLD)

            result["scanned"] = len(topic_counts)

            for tc in topic_counts:
                topic = tc["topic"]
                entries = await conn.fetch(
                    """SELECT id, title, content FROM memories
                       WHERE team_id = 'public' AND topic = $1
                       ORDER BY importance DESC LIMIT 50""",
                    topic)

                if len(entries) < 3:
                    continue

                entries_list = "\n".join(
                    f"- [{r['title'][:80]}] {r['content'][:200]}" for r in entries
                )

                split_prompt = (
                    f'Split these {len(entries)} items under topic "{topic}" '
                    f'into 2-4 sub-topics (max 12 chars each).\n\n{entries_list}\n\n'
                    f'Reply ONLY JSON: {{"subtopics": ["sub1","sub2"], '
                    f'"assignments": {{"0":"sub1","1":"sub1","2":"sub2"}}}}')

                raw = await registry.chat_for_engine("classifier",
                    [{"role": "user", "content": split_prompt[:8000]}])

                if not raw:
                    continue

                parsed = _parse_json(raw)
                subtopics = parsed.get("subtopics", [])
                assignments = parsed.get("assignments", {})

                if not subtopics or not assignments:
                    continue

                for i_str, sub in assignments.items():
                    try:
                        idx = int(i_str)
                        if idx < len(entries) and sub in subtopics:
                            new_topic = f"{topic}/{sub}"[:50]
                            await conn.execute(
                                "UPDATE memories SET topic=$1, subcategory=$2 WHERE id=$3",
                                new_topic, sub, entries[idx]["id"])
                    except (ValueError, IndexError):
                        continue

                result["split"] += 1
                print(f"[K2 split] Topic '{topic}' -> {subtopics}")

        return result
    except Exception as e:
        print(f"[K2 split] fatal: {e}")
        return result


async def aggregate_public_knowledge(repo: MemoryRepo) -> int:
    """Legacy: Run full K2 pipeline (categorize + split). Kept for backward compat."""
    merged = 0
    try:
        registry = ModelRegistry.get_instance()
        if not registry:
            return 0

        async with repo.pool.acquire() as conn:
            all_rows = await conn.fetch(
                """SELECT id, title, content FROM memories
                   WHERE team_id = 'public' AND topic != 'merged'
                   ORDER BY created_at DESC LIMIT 20""")

            if len(all_rows) < 2:
                return 0

            # Phase 1: LLM semantic grouping by title
            titles = [str(i) + ": " + r["title"][:80] for i, r in enumerate(all_rows)]
            title_list = "\n".join(titles)
            group_prompt = (
                'Group these titles by topic similarity. '
                'Return ONLY JSON: {"groups": [[0,3], [1,2,5], ...]}. '
                'Only groups of 2+. Skip unrelated.\n\n' + title_list)

            print(f"[K2] Phase 1: sending {len(all_rows)} titles...")
            result_text = await registry.chat_for_engine(
                "classifier", [{"role": "user", "content": group_prompt}])
            print(f"[K2] Phase 1 result: {repr(result_text)[:200]}")

            if not result_text:
                return 0

            parsed = _parse_json(result_text)
            groups = parsed.get("groups", [])

            if not groups:
                return 0

            for group_ids in groups:
                if len(group_ids) < 2:
                    continue
                items = [
                    (all_rows[int(i)]["id"], all_rows[int(i)]["title"], all_rows[int(i)]["content"])
                    for i in group_ids if i < len(all_rows)
                ]
                if len(items) < 2:
                    continue

                pieces = "\n---\n".join(f"## {t}\n{c[:500]}" for _, t, c in items)
                merge_prompt = (
                    "Merge these related knowledge entries into ONE article. "
                    "Keep all facts, remove duplicates:\n\n" + pieces)

                print(f"[K2] Phase 2: merging {len(items)} entries...")
                merged_text = await registry.chat_for_engine(
                    "reflection", [{"role": "user", "content": merge_prompt}])

                if not merged_text:
                    continue

                mid = uuid.uuid4()
                merged_title = merged_text.split("\n")[0][:100]
                await conn.execute(
                    """INSERT INTO memories (id, team_id, title, content, source_type,
                       lifecycle_stage, topic, importance, category)
                       VALUES ($1, 'public', $2, $3, 'knowledge', 'longterm',
                       'merged', 0.9, 'knowledge')""",
                    str(mid), merged_title[:100], merged_text[:5000])

                for old_id, _, _ in items:
                    await conn.execute(
                        "UPDATE memories SET importance = importance * 0.3, "
                        "metadata = metadata || jsonb_build_object('merged_into', $1::text) "
                        "WHERE id = $2",
                        str(mid), old_id)

                merged += 1
                print(f"[K2] Merged {len(items)} entries -> {mid}: {merged_title[:50]}")

        return merged
    except Exception as e:
        import traceback
        print(f"[K2] Failed: {e}")
        traceback.print_exc()
        return 0
