# AI Memory OS — Local BM25 Provider (Multi-Backend)
# Auto-selects: fastembed (Linux/Win) or sklearn (Mac/fallback)

from __future__ import annotations

import platform
import re
from typing import Any, Optional


class BM25Backend:
    """Base class for BM25 sparse embedding backends."""

    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError


class FastembedBM25(BM25Backend):
    """fastembed/Qdrant BM25 — onnxruntime-based, best quality."""

    name = "fastembed"

    def __init__(self):
        from fastembed import SparseTextEmbedding
        self._model = SparseTextEmbedding(model_name="Qdrant/bm25")

    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        results = []
        for sv in self._model.embed(texts):
            results.append({
                "indices": sv.indices.tolist(),
                "values": sv.values.tolist(),
            })
        return results



    """scikit-learn TfidfVectorizer — persistent vocabulary."""
    name = "sklearn"
    _vocab_file = None


    """scikit-learn TfidfVectorizer — pure Python, works everywhere."""

    name = "sklearn"

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b\w+\b",
        )

    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        matrix = self._vectorizer.fit_transform(texts)
        results = []
        for i in range(matrix.shape[0]):
            row = matrix[i].tocoo()
            results.append({
                "indices": row.col.tolist(),
                "values": row.data.tolist(),
            })
        return results


def _detect_best_bm25() -> Optional[BM25Backend]:
    """Auto-detect the best BM25 backend for this platform."""
    # Try fastembed first (best quality)
    try:
        import subprocess, sys
        r = subprocess.run(
            [sys.executable, "-c",
             "from fastembed import SparseTextEmbedding; SparseTextEmbedding(model_name='Qdrant/bm25')"],
            capture_output=True, timeout=5,
        )
        if r.returncode == 0:
            return FastembedBM25()
    except Exception:
        pass

    # Fallback: sklearn (always works, no native deps)
    try:
        return SklearnBM25()
    except Exception:
        pass

    return None


# Global singleton
_bm25_backend: Optional[BM25Backend] = None


def get_bm25() -> Optional[BM25Backend]:
    """Get or auto-detect the BM25 backend."""
    global _bm25_backend
    if _bm25_backend is None:
        _bm25_backend = _detect_best_bm25()
    return _bm25_backend


def encode_sparse(texts: list[str]) -> Optional[list[dict[str, Any]]]:
    """Encode texts to sparse vectors using the best available backend."""
    bm25 = get_bm25()
    return bm25.encode(texts) if bm25 else None
