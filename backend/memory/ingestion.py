# AI Memory OS — Ingestion Pipeline
# Blueprint Section 9

from __future__ import annotations

import re
import uuid
from typing import Optional


class SemanticChunker:
    """Splits text into semantic chunks by paragraphs and boundaries."""

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 64):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, text: str) -> list[str]:
        sections = re.split(r"\n\n+", text)
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue
            st = self._estimate_tokens(section)

            if current_tokens + st > self.max_tokens and current:
                chunks.append("\n\n".join(current))
                if len(current) > 1:
                    current = current[-1:]
                    current_tokens = self._estimate_tokens(current[0])
                else:
                    current = []
                    current_tokens = 0

            current.append(section)
            current_tokens += st

        if current:
            chunks.append("\n\n".join(current))

        return chunks if chunks else [text]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        other = len(text) - cjk
        return int(cjk / 1.5 + other / 4.0)


class IngestionPipeline:
    """Orchestrates: parse -> clean -> chunk -> embed -> store."""

    def __init__(self, qdrant_store, chunker: Optional[SemanticChunker] = None):
        self.qdrant = qdrant_store
        self.chunker = chunker or SemanticChunker()

    async def ingest(
        self,
        content: str,
        memory_id: str,
        team_id: str,
        workspace_id: str,
        embedding_fn,  # callable: (text) -> list[float]
        **kwargs,
    ) -> list[dict]:
        """Run the full ingestion pipeline for a single memory."""
        chunks = self.chunker.chunk(content)
        results: list[dict] = []

        for i, chunk_text in enumerate(chunks):
            # Truncate to ~7000 chars (~5000 tokens for Chinese) to avoid API limits
            safe_text = chunk_text[:7000]
            vector = await embedding_fn(safe_text)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{memory_id}_{i}"))
            self.qdrant.upsert(
                point_id=point_id,
                vector=vector,
                text=chunk_text,
                payload={
                    "memory_id": memory_id,
                    "team_id": team_id,
                    "workspace_id": workspace_id,
                    "chunk_index": i,
                    "text": chunk_text,
                    "title": kwargs.get("title", ""),
                    "category": kwargs.get("category", ""),
                    "memory_type": kwargs.get("memory_type", "general"),
                    "agent_id": kwargs.get("agent_id", ""),
                },
            )
            results.append({
                "chunk_index": i,
                "point_id": point_id,
                "token_estimate": self.chunker._estimate_tokens(chunk_text),
            })

        return results
