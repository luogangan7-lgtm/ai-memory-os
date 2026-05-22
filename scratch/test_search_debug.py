import sys
sys.path.append("/Volumes/data/ai-memory-os")
import asyncio
import os
import logging
logging.basicConfig(level=logging.INFO)

from backend.manager.registry import ModelRegistry
from backend.services.config import load_system_config, settings
from backend.memory.retrieval import RetrievalPipeline
from backend.memory.qdrant_store import QdrantStore
from backend.graph.neo4j_store import GraphStore

async def main():
    reg = ModelRegistry.get_instance()
    
    # 1. Test embedding
    print("\n--- 1. Testing Embedding ---")
    query = "vector similarity"
    try:
        vec = await reg.embed_single(query)
        print(f"Success: Embedding vector length = {len(vec)}, first 5 values = {vec[:5]}")
    except Exception as e:
        print(f"Embedding failed: {e}")
        return

    # 2. Test Qdrant Search
    print("\n--- 2. Testing Qdrant Store ---")
    
    # Let's read connection settings
    print(f"Connecting to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
    qdrant = QdrantStore(host=settings.qdrant_host, port=settings.qdrant_port)
    graph = GraphStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
    
    try:
        # Check collections
        collections = qdrant.client.get_collections()
        print(f"Qdrant collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print(f"Qdrant client failed: {e}")
        return
        
    try:
        # Do raw hybrid search
        results = qdrant.hybrid_search(
            query_vector=vec,
            query_text=query,
            team_id="testteam",
            workspace_id="default",
            top_k=30,
        )
        print(f"Raw Qdrant results count: {len(results)}")
        for i, r in enumerate(results):
            payload = r.get("payload", {})
            print(f"  [{i}] ID: {r['id']}, Score: {r['score']:.4f}, Title: {payload.get('title')}, Content: {payload.get('text')[:30]}...")
    except Exception as e:
        print(f"Qdrant hybrid_search failed: {e}")
        return

    # 3. Test Reranking
    print("\n--- 3. Testing Reranking ---")
    if len(results) == 0:
        print("No raw results to rerank.")
        return
        
    seen = {}
    for r in results:
        mid = r["payload"].get("memory_id", r["id"])
        if mid not in seen or r["score"] > seen[mid]["score"]:
            seen[mid] = r
    deduped = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    
    docs = [r["payload"].get("text", "") for r in deduped]
    try:
        reranked = await reg.rerank(query, docs, top_n=len(docs))
        print(f"Reranking succeeded. Results:")
        for r in reranked:
            idx = r['index']
            print(f"  Doc index {idx} ({deduped[idx]['payload'].get('title')}): score {r['score']:.4f}")
    except Exception as e:
        print(f"Reranking failed: {e}")
        
    # 4. Run full retrieval pipeline
    print("\n--- 4. Running Full Retrieval Pipeline ---")
    pipeline = RetrievalPipeline(qdrant, graph)
    
    final_results = await pipeline.search(
        query=query,
        embedding_fn=reg.embed_single,
        team_id="testteam",
        workspace_id="default",
        top_k=3,
        use_rerank=True,
        rerank_fn=reg.rerank
    )
    print(f"Full search with rerank (threshold filter) returns {len(final_results)} results:")
    for r in final_results:
        print(f"  Score: {r['score']:.4f}, Title: {r['payload'].get('title')}")
        
    final_results_no_rerank = await pipeline.search(
        query=query,
        embedding_fn=reg.embed_single,
        team_id="testteam",
        workspace_id="default",
        top_k=3,
        use_rerank=False,
        rerank_fn=None
    )
    print(f"\nFull search without rerank returns {len(final_results_no_rerank)} results:")
    for r in final_results_no_rerank:
        print(f"  Score: {r['score']:.4f}, Title: {r['payload'].get('title')}")

if __name__ == "__main__":
    asyncio.run(main())
