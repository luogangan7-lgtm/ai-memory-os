"""One-time migration: rebuild public knowledge Qdrant vectors.
docker compose exec backend python scripts/fix_public_pool_vectors.py
"""
import asyncio

async def fix():
    from backend.api.routes import pg_repo, qdrant_store, registry
    qdrant_store.ensure_collection("memory_team_public")
    async with pg_repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, title, content, topic FROM memories "
            "WHERE team_id = 'public' AND source_type = 'knowledge' "
            "ORDER BY created_at")
    print(f"Entries: {len(rows)}")
    ok = 0
    for row in rows:
        try:
            text = (row["title"] or "") + " " + (row["content"] or "")[:500]
            if len(text.strip()) < 20: continue
            vector = await registry.embed_single(text[:1000])
            qdrant_store.client.upsert(collection_name="memory_team_public",
                points=[{"id": str(row["id"]), "vector": vector,
                    "payload": {"memory_id": str(row["id"]), "title": row["title"] or "",
                        "text": text[:500], "source_type": "knowledge",
                        "topic": row["topic"] or "", "team_id": "public"}}])
            ok += 1
            if ok % 50 == 0: print(f"  {ok}/{len(rows)}...")
        except Exception as e:
            print(f"  FAIL: {str(e)[:60]}")
    print(f"Done: {ok}/{len(rows)}")

if __name__ == "__main__":
    asyncio.run(fix())
