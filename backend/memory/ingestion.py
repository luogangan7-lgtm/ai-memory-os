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
    """Orchestrates: parse -> clean -> chunk -> embed -> store (Qdrant + PostgreSQL)."""

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
        """Run the full ingestion pipeline for a single memory.
        
        Writes to BOTH Qdrant (vector search) AND PostgreSQL (memories + chunks tables).
        """
        chunks = self.chunker.chunk(content)
        results: list[dict] = []
        title = kwargs.get("title", "")
        source_type = kwargs.get("source_type", "document")
        category = kwargs.get("category", "general")

        # ── Step 1: Write memory record to PostgreSQL ──────────────────────
        try:
            from backend.api.db_helper import get_db_conn
            conn = await get_db_conn()
            await conn.execute(
                """INSERT INTO memories
                   (id, team_id, workspace_id, title, content, layer, source_type, category, confidence, created_at)
                   VALUES ($1, $2, $3, $4, $5, 'L0', $6, $7, 1.0, NOW())
                   ON CONFLICT (id) DO NOTHING""",
                memory_id, team_id, workspace_id,
                title or "Untitled",
                content[:4000],   # store first 4000 chars as preview
                source_type, category
            )
            await conn.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to insert memory {memory_id} into PG: {e}")

        # ── Step 2: Embed & upsert each chunk to Qdrant + chunks table ─────
        for i, chunk_text in enumerate(chunks):
            # Truncate to ~7000 chars (~5000 tokens for Chinese) to avoid API limits
            safe_text = chunk_text[:7000]
            vector = await embedding_fn(safe_text)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{memory_id}_{i}"))

            # Write to Qdrant
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
                    "title": title,
                    "category": category,
                    "source_type": source_type,
                    "memory_type": kwargs.get("memory_type", "general"),
                    "agent_id": kwargs.get("agent_id", ""),
                    "confidence": 1.0,
                },
            )

            # Write chunk record to PostgreSQL
            try:
                from backend.api.db_helper import get_db_conn
                conn = await get_db_conn()
                await conn.execute(
                    """INSERT INTO chunks
                       (id, memory_id, chunk_index, content, token_count, qdrant_point_id, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, NOW())
                       ON CONFLICT DO NOTHING""",
                    str(uuid.uuid4()), memory_id, i,
                    chunk_text[:8000],
                    self.chunker._estimate_tokens(chunk_text),
                    point_id
                )
                await conn.close()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to insert chunk {i} for {memory_id}: {e}")

            results.append({
                "chunk_index": i,
                "point_id": point_id,
                "token_estimate": self.chunker._estimate_tokens(chunk_text),
            })

        return results
