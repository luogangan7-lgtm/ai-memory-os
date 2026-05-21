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

    def __init__(self, qdrant_store, chunker: Optional[SemanticChunker] = None, pg_repo = None):
        self.qdrant = qdrant_store
        self.chunker = chunker or SemanticChunker()
        self.pg_repo = pg_repo

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

        # Clear existing chunks for this memory_id if pg_repo is available
        if self.pg_repo:
            try:
                if hasattr(self.pg_repo, "db_path"):  # SQLite
                    import aiosqlite
                    async with aiosqlite.connect(self.pg_repo.db_path) as db:
                        await db.execute("DELETE FROM chunks WHERE memory_id = ?", (memory_id,))
                        await db.commit()
                else:  # PostgreSQL
                    from backend.memory.pg_repo import safe_uuid
                    async with self.pg_repo.pool.acquire() as conn:
                        await conn.execute("DELETE FROM chunks WHERE memory_id = $1", safe_uuid(memory_id))
            except Exception as e:
                import logging
                logging.getLogger("ingestion").warning(f"Failed to clear existing chunks for {memory_id}: {e}")

        for i, chunk_text in enumerate(chunks):
            # Truncate to ~7000 chars (~5000 tokens for Chinese) to avoid API limits
            safe_text = chunk_text[:7000]
            vector = await embedding_fn(safe_text)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{memory_id}_{i}"))
            self.qdrant.upsert(
                point_id=point_id,
                vector=vector,
                text=chunk_text,
                team_id=team_id,
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

            token_count = self.chunker._estimate_tokens(chunk_text)

            # Insert chunk into database chunks table
            if self.pg_repo:
                try:
                    await self.pg_repo.insert_chunk(
                        memory_id=memory_id,
                        chunk_index=i,
                        content=chunk_text,
                        token_count=token_count,
                        qdrant_point_id=point_id
                    )
                except Exception as db_err:
                    import logging
                    logging.getLogger("ingestion").error(f"Failed to save chunk {i} to database for memory {memory_id}: {db_err}")

            results.append({
                "chunk_index": i,
                "point_id": point_id,
                "token_estimate": token_count,
            })

        return results

