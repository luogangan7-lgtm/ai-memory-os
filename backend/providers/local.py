# AI Memory OS — Local BM25 Provider (Zero-Dependency Hashing Vectorizer)
from __future__ import annotations
import math, re, hashlib
from typing import Any, Optional

def tokenize(text: str) -> list[str]:
    """Tokenize English words and Chinese characters for hybrid search."""
    tokens = []
    # English/Numbers
    for m in re.finditer(r'[a-zA-Z0-9]+', text):
        tokens.append(m.group(0).lower())
    # Chinese Han characters
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            tokens.append(char)
    return tokens

class BM25Backend:
    """Base class for BM25 sparse embedding backends."""
    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

class PurePythonBM25(BM25Backend):
    """High-performance zero-dependency Feature Hashing Sparse Vectorizer.
    Perfectly consistent across environments, requires no vocabulary storage."""
    name = "pure_python_bm25"

    def __init__(self, num_features: int = 30000):
        self.num_features = num_features

    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for text in texts:
            tokens = tokenize(text)
            if not tokens:
                results.append({"indices": [], "values": []})
                continue
            
            # Count term frequencies
            counts: dict[int, int] = {}
            for t in tokens:
                # Deterministic hashing using sha256 to ensure perfect consistency
                h = hashlib.sha256(t.encode("utf-8")).hexdigest()
                idx = int(h[:8], 16) % self.num_features
                counts[idx] = counts.get(idx, 0) + 1
            
            # Convert to sparse representation sorted by indices (required by Qdrant)
            sorted_indices = sorted(list(counts.keys()))
            # Apply standard BM25/TF-IDF log scaling
            values = [float(round(1.0 + math.log(counts[idx]), 4)) for idx in sorted_indices]
            
            results.append({
                "indices": sorted_indices,
                "values": values,
            })
        return results

# Global singleton
_bm25_backend: Optional[BM25Backend] = PurePythonBM25()

def get_bm25() -> Optional[BM25Backend]:
    """Get the active BM25 backend."""
    global _bm25_backend
    if _bm25_backend is None:
        _bm25_backend = PurePythonBM25()
    return _bm25_backend

def encode_sparse(texts: list[str]) -> Optional[list[dict[str, Any]]]:
    """Encode texts to sparse vectors using the zero-dependency backend."""
    bm25 = get_bm25()
    return bm25.encode(texts) if bm25 else None
