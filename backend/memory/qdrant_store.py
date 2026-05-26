# AI Memory OS — Qdrant Vector Store (Dense + Sparse Hybrid)
# Blueprint Section 27 / 14

from __future__ import annotations

from typing import Any, Optional
import asyncio

from qdrant_client import QdrantClient, models

from backend.providers.local import get_bm25, encode_sparse


DEFAULT_COLLECTION_NAME = "memory_team_default"
VECTOR_SIZE = 1024
DISTANCE_METRIC = models.Distance.COSINE


class QdrantStore:
    """Vector store with dense + optional sparse hybrid index with per-team physical isolation."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self._bm25 = get_bm25()
        self._ensure_collection(DEFAULT_COLLECTION_NAME)

    def _ensure_collection(self, collection_name: str) -> None:
        try:
            self.client.get_collection(collection_name)
        except Exception:
            kwargs: dict = {
                "collection_name": collection_name,
                "vectors_config": {
                    "": models.VectorParams(
                        size=VECTOR_SIZE,
                        distance=DISTANCE_METRIC,
                    )
                },
            }
            if self._bm25 is not None:
                kwargs["sparse_vectors_config"] = {
                    "bm25": models.SparseVectorParams(
                        modifier=models.Modifier.IDF,
                    )
                }
            self.client.create_collection(**kwargs)

    async def async_upsert(
        self, point_id: str, vector: list[float],
        payload: dict[str, Any], text: str = "",
        team_id: str = "default",
    ) -> None:
        return await asyncio.to_thread(self.upsert, point_id, vector, payload, text, team_id)

    def upsert(
        self, point_id: str, vector: list[float],
        payload: dict[str, Any], text: str = "",
        team_id: str = "default",
    ) -> None:
        collection_name = f"memory_team_{team_id}"
        self._ensure_collection(collection_name)
        vectors: dict = {"": vector}
        if self._bm25 is not None and text:
            sparse = encode_sparse([text])
            if sparse and sparse[0]:
                vectors["bm25"] = models.SparseVector(**sparse[0])
        self.client.upsert(
            collection_name=collection_name,
            points=[models.PointStruct(id=point_id, vector=vectors, payload=payload)],
        )

    async def async_hybrid_search(
        self, query_vector: list[float], query_text: str,
        team_id: str = "default", workspace_id: str = "default",
        top_k: int = 10, source_type: str = None
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.hybrid_search, query_vector, query_text, team_id, workspace_id, top_k, source_type)

    def hybrid_search(
        self, query_vector: list[float], query_text: str,
        team_id: str = "default", workspace_id: str = "default",
        top_k: int = 10, source_type: str = None
    ) -> list[dict[str, Any]]:
        collection_name = f"memory_team_{team_id}"
        self._ensure_collection(collection_name)

        must = []
        # Fix: "default" 是全局空间，无需过滤；只在明确指定非默认 workspace 时才过滤
        if workspace_id and workspace_id != "default":
            must.append(models.FieldCondition(
                key="workspace_id", match=models.MatchValue(value=workspace_id)))
        if source_type:
            must.append(models.FieldCondition(
                key="source_type", match=models.MatchValue(value=source_type)))
        
        qdrant_filter = models.Filter(must=must) if must else None

        prefetch = [
            models.Prefetch(query=query_vector, using="", limit=top_k * 2),
        ]

        if self._bm25 is not None:
            sparse = encode_sparse([query_text])
            if sparse and sparse[0]:
                prefetch.append(models.Prefetch(
                    query=models.SparseVector(**sparse[0]),
                    using="bm25", limit=top_k * 2,
                ))

        results = self.client.query_points(
            collection_name=collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=qdrant_filter,
            with_payload=True, limit=top_k,
        )

        return [{"id": h.id, "score": h.score, "payload": h.payload or {}} for h in results.points]

    def delete(self, point_id: str, team_id: str = "default") -> None:
        collection_name = f"memory_team_{team_id}"
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=[point_id]),
        )
