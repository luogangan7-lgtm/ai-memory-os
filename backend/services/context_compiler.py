# AI Memory OS — Context Compiler Service
# Purges redundant text, compresses fillers, and packages dense knowledge to save LLM tokens.

from __future__ import annotations

import re
from typing import Any, List, Dict


class ContextCompiler:
    """Advanced Context Compiler that filters, deduplicates, and compresses retrieved memory chunks."""

    @staticmethod
    def is_filler_query(query: str) -> bool:
        """Determines if a query is a simple greeting or filler that doesn't need knowledge injection."""
        q = query.lower().strip("?.! ")
        fillers = {
            "hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "sup", "yo", "thanks", "thank you", "bye", "goodbye",
            "你好", "您好", "哈喽", "早上好", "中午好", "下午好", "晚上好", "谢谢", "再见", "拜拜"
        }
        return q in fillers

    @staticmethod
    def compress_text(text: str) -> str:
        """Removes repetitive connector phrases and redundant spacing to compress token count."""
        # Clean double spaces and linebreaks
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove verbose filler phrases that do not add semantic value
        redundant_phrases = [
            r"(?i)\bplease note that\b",
            r"(?i)\bas we discussed earlier\b",
            r"(?i)\bas previously mentioned\b",
            r"(?i)\bin this section we will discuss\b",
            r"(?i)\bthis document describes how\b",
            r"(?i)\bthe purpose of this is to\b",
        ]
        for phrase in redundant_phrases:
            text = re.sub(phrase, "", text)
            
        # Clean up any leftover double punctuation or spaces
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\s*\.\s*', '. ', text)
        return re.sub(r'\s+', ' ', text).strip()

    @classmethod
    def compile_context(
        cls,
        vector_results: List[Dict[str, Any]],
        query: str,
        max_tokens: int = 2500
    ) -> str:
        """Deduplicates, compresses, and packages retrieved vector and graph results into a high-density prompt."""
        if cls.is_filler_query(query):
            return ""

        compiled_chunks = []
        seen_texts = set()
        token_estimate = 0

        # Process each result chunk
        for item in vector_results:
            payload = item.get("payload", item)
            text = payload.get("text", payload.get("content", "")).strip()
            title = payload.get("title", "").strip()
            memory_type = payload.get("source_type", "knowledge").strip()

            if not text:
                continue

            # Standardize and deduplicate
            normalized_text = re.sub(r'\s+', ' ', text.lower())[:100]
            if normalized_text in seen_texts:
                continue
            seen_texts.add(normalized_text)

            # Compress text
            compressed = cls.compress_text(text)
            
            # Format graph context if present
            graph_info = ""
            if "graph_context" in item and item["graph_context"]:
                relations = []
                for g in item["graph_context"]:
                    source = g.get("source_name", "Unknown")
                    rel = g.get("type", "RELATED_TO")
                    target = g.get("target_name", "Unknown")
                    relations.append(f"({source})-[{rel}]->({target})")
                if relations:
                    graph_info = f"\n  [Graph Relations]: {', '.join(relations[:5])}"

            # Estimate token (roughly 3 characters per token for English, 1 per character for Chinese)
            est_tokens = len(compressed) // 3 + len(title) // 3 + 10
            if token_estimate + est_tokens > max_tokens:
                break

            header = f"[{memory_type.upper()}] {title}" if title else f"[{memory_type.upper()}]"
            chunk_str = f"- {header}: {compressed}{graph_info}"
            compiled_chunks.append(chunk_str)
            token_estimate += est_tokens

        if not compiled_chunks:
            return ""

        # High-density packaging
        prompt = (
            "[SYSTEM KNOWLEDGE BASE - AUTOMATIC INJECTION]\n"
            "Use the following authentic historical memory/knowledge to enrich context:\n" +
            "\n".join(compiled_chunks) +
            "\n[END OF KNOWLEDGE BASE]\n"
        )
        return prompt
