# AI Memory OS — Retrieval Pipeline
# Blueprint Section 10 / 14 / 15

from __future__ import annotations

from typing import Any, Callable, Optional


class RetrievalPipeline:
    """Orchestrates: query -> hybrid search -> rerank -> compile."""

    def __init__(self, qdrant_store, graph_store):
        self.qdrant = qdrant_store
        self.graph = graph_store

    async def search(
        self,
        query: str,
        embedding_fn: Callable,
        team_id: str = "default",
        workspace_id: str = "default",
        top_k: int = 10,
        use_rerank: bool = True,
        rerank_fn: Optional[Callable] = None,
        use_graph: bool = False,
        min_confidence: float = 0.0,
        source_type_filter: str = None,
    ) -> list[dict[str, Any]]:
        query_vector = await embedding_fn(query)

        # Phase 1: Hybrid retrieval (overfetch for rerank)
        results = self.qdrant.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            team_id=team_id,
            workspace_id=workspace_id,
            top_k=top_k * 3 if use_rerank else top_k,
            source_type=source_type_filter,
        )


        # Deduplicate by memory_id
        seen: dict[str, dict[str, Any]] = {}
        for r in results:
            mid = r["payload"].get("memory_id", r["id"])
            if mid not in seen or r["score"] > seen[mid]["score"]:
                seen[mid] = r

        deduped = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

        # Phase 2: Cross-encoder reranker (replaces simple boost)
        if use_rerank and rerank_fn is not None and len(deduped) > 0:
            try:
                docs = [r["payload"].get("text", "") for r in deduped]
                import logging
                _log = logging.getLogger(__name__)
                _log.info(f"Reranking {len(docs)} docs with query: {query[:50]}")
                reranked = await rerank_fn(query, docs, top_n=min(top_k, len(docs)))
                _log.info(f"Reranked: {[(r['index'], round(r['score'], 3)) for r in reranked]}")
                # Map reranker results back
                rerank_map = {item["index"]: item["score"] for item in reranked}
                for i, r in enumerate(deduped):
                    if i in rerank_map:
                        r["score"] = rerank_map[i]
                deduped.sort(key=lambda x: x["score"], reverse=True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Reranker failed: {e}")
                # Fallback: keep RRF scores as-is
                pass

        deduped = deduped[:top_k]

        # Confidence threshold filter
        deduped = [
            r for r in deduped
            if float(r["payload"].get("confidence", 0)) >= min_confidence
        ]

        # Rerank threshold filter (only apply if reranker is used)
        if use_rerank and rerank_fn is not None:
            from backend.services.config import settings
            deduped = [
                r for r in deduped
                if float(r.get("score", 1.0)) >= getattr(settings, "search_rerank_threshold", 0.85)
            ]

        # Phase 3: Graph enrichment
        if use_graph and deduped:
            memory_ids = [r["payload"]["memory_id"] for r in deduped]
            try:
                graph_ctxs = await self.graph.find_related(memory_ids, top_k=top_k)
                for r in deduped:
                    r["graph_context"] = [
                        g for g in graph_ctxs
                        if g.get("source") == r["payload"]["memory_id"]
                        or g.get("target") == r["payload"]["memory_id"]
                    ]
            except Exception:
                for r in deduped:
                    r["graph_context"] = []

        # Section 11: Context Engineering - dedup + compress
        from backend.memory.context_engineer import deduplicate
        deduped = deduplicate(deduped)
        return deduped
