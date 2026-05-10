# AI Memory OS - Context Engineering (dedup, conflict, compress)
from __future__ import annotations
from typing import Any

def deduplicate(results: list[dict], threshold: float = 0.95) -> list[dict]:
    """Remove near-identical results."""
    seen, out = set(), []
    for r in results:
        key = r.get("payload", r).get("text", "")[:80]
        if key not in seen:
            seen.add(key); out.append(r)
    return out

def detect_conflicts(memories: list[dict]) -> list[dict]:
    """Find conflicting memories (same topic, opposite sentiment)."""
    conflicts = []
    for i, a in enumerate(memories):
        for b in memories[i+1:]:
            if a.get("topic") and a["topic"] == b.get("topic"):
                if _has_contradiction(a.get("content",""), b.get("content","")):
                    conflicts.append({"a": a.get("id"), "b": b.get("id"), "topic": a["topic"]})
    return conflicts

def _has_contradiction(t1: str, t2: str) -> bool:
    neg = {"not", "no", "never", "don't", "cannot", "wrong", "incorrect", "false", "\u4e0d", "\u6ca1", "\u9519", "\u7981\u6b62"}
    words1, words2 = set(t1.lower().split()), set(t2.lower().split())
    has_neg_1 = bool(words1 & neg)
    has_neg_2 = bool(words2 & neg)
    overlap = len(words1 & words2) / max(len(words1 | words2), 1)
    return overlap > 0.3 and (has_neg_1 != has_neg_2)

def compress_context(results: list[dict], max_tokens: int = 3000) -> str:
    """Compress search results into a structured context for LLM."""
    parts = []
    token_est = 0
    for r in results[:20]:
        p = r.get("payload", r)
        text = f"[Title: {p.get('title','')}] {p.get('text','')[:500]}"
        est = len(text) // 3
        if token_est + est > max_tokens: break
        parts.append(text); token_est += est
    return chr(10) + "---" + chr(10) + (chr(10) + "---" + chr(10)).join(parts)
