# AI Memory OS — Knowledge Internalization Service
# Automatically evaluates if personal memories should be promoted to Common Knowledge.

from __future__ import annotations
import re
_SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"bearer [a-zA-Z0-9_\-\.]{20,}",
    r"[a-f0-9]{32}",
    r"api[ _]?key[:\s]*[a-zA-Z0-9_\-]{10,}",
    r"api[ _]?token[:\s]*[a-zA-Z0-9_\-]{10,}",
    r"password[:\s]*\S{6,}",
    r"secret[:\s]*\S{6,}",
    r"token[:\s]*[a-zA-Z0-9_\-\.]{20,}",
    r"cfat_[a-zA-Z0-9_\-]{20,}",
    r"mos_[a-f0-9]{16,}",
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
    r"@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
    r"1[3-9]\\d{9}",                      # Chinese mobile
    r"\\d{15,18}",                        # ID card
    r"\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",  # IP
    r"地址|电话|手机|姓名",                 # personal info markers
    r"微信|QQ|wechat",                     # social contact

]

def _contains_secrets(text):
    if not text: return False
    for pattern in _SECRET_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


import logging
import json
from datetime import datetime, timezone
from backend.memory.pg_repo import MemoryRepo
from backend.services.config import settings
from backend.memory.retrieval import RetrievalPipeline
from backend.manager.registry import ModelRegistry


async def _llm_quality_gate(pg, team_id: str, title: str, content: str) -> bool:
    """Use user's LLM to evaluate if content is knowledge-worthy for internalization."""
    try:
        provider = await pg.get_active_user_provider_config(team_id)
        if not provider:
            return True  # No LLM configured → fall through to existing checks
    except Exception:
        return True

    prompt = f"""You are a knowledge quality evaluator. Determine if the following user content is suitable for public knowledge base internalization.

Good for internalization:
- Technical insights, architecture decisions, best practices
- Bug fixes with clear root cause and solution
- Project conventions, configuration knowledge
- Domain expertise and research findings
- Tutorials and how-to guides

NOT suitable (personal/private):
- Personal chat, greetings, casual conversation
- Private API keys, passwords, tokens
- Personal contact information
- Work-in-progress notes without conclusions
- User-specific preferences of low general value

Content title: {title}
Content: {content[:1000]}

Reply with ONLY a JSON object: {{"quality_score": 0.0-1.0, "decision": "approve"|"reject", "reason": "brief reason (max 30 chars)"}}"""

    import httpx, json
    try:
        base_url = (provider.get("api_base_url") or "").rstrip("/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {provider['api_key']}"},
                json={
                    "model": provider.get("model_name", "gpt-3.5-turbo"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.1
                }
            )
        if resp.status_code != 200:
            return True  # LLM unavailable → allow through

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        score = float(result.get("quality_score", 0.5))
        return score >= 0.5  # Threshold: >=0.5 qualifies
    except Exception:
        return True  # On any error, allow through (don't block internalization)


class InternalizationService:
    def __init__(self, pg: MemoryRepo, retrieval: RetrievalPipeline, registry: ModelRegistry):
        self.pg = pg
        self.retrieval = retrieval
        self.registry = registry

    async def evaluate_and_promote(self, team_id: str):
        """Scan recent agent memories and promote high-value, unique ones to knowledge."""
        # Database compatibility layer
        is_sqlite = hasattr(self.pg, "db_path")
        
        if is_sqlite:
            import aiosqlite
            db_conn = await aiosqlite.connect(getattr(self.pg, "db_path"))
            db_conn.row_factory = aiosqlite.Row
            cursor = await db_conn.execute("""
                SELECT id, title, content, category, importance, metadata 
                FROM memories 
                WHERE source_type IN ('agent', 'human', 'document') 
                AND (json_extract(metadata, '$.internalized') IS NOT TRUE)
                ORDER BY created_at DESC
                LIMIT 20
            """)
            rows = await cursor.fetchall()
        else:
            pool_conn = await self.pg.pool.acquire()
            rows = await pool_conn.fetch("""
                SELECT id, title, content, category, importance, metadata 
                FROM memories 
                WHERE team_id = $1
                AND source_type IN ('agent', 'human', 'document') 
                AND (metadata->>'internalized')::boolean IS NOT TRUE
                ORDER BY created_at DESC
                LIMIT 20
            """, team_id)

        promoted_count = 0
        try:
            for r in rows:
                mid = r["id"]
                content = r["content"] or ""
                importance = r["importance"]
                if importance is None:
                    importance = 0.5
                title = r["title"] or ""
                if _contains_secrets(content) or _contains_secrets(title):
                    continue

                # 2. Quality & Redundancy Check
                min_len = int(settings.internalize_min_content_length)
                if len(content) < min_len and importance < 0.8:
                    continue

                if not self.retrieval or not self.registry:
                    # If pipelines are missing (e.g. during simple reflection), skip deeper checks
                    is_redundant = False
                    is_valuable = importance > 0.5 and len(content) > 100
                else:
                    # Search existing public knowledge
                    results = await self.retrieval.search(
                        query=content[:500], 
                        embedding_fn=self.registry.embed_single,
                        team_id=team_id,
                        source_type_filter="knowledge",
                        top_k=3
                    )
                    is_redundant = any(res["score"] > settings.internalize_similarity_threshold for res in results)
                    is_valuable = importance > 0.5 and len(content) > 100
                
                llm_approved = await _llm_quality_gate(self.pg, team_id, title, content)
                if not is_redundant and is_valuable and llm_approved:
                    # 4. Promote to Knowledge with a small importance boost
                    new_importance = min(1.0, importance + 0.1)
                    logging.info(f"Internalizing memory {mid}: {title}")

                    # Extract metadata fields
                    cat = r["category"] or "general"
                    metadata_val = r["metadata"]
                    if isinstance(metadata_val, str):
                        try:
                            meta = json.loads(metadata_val)
                        except Exception:
                            meta = {}
                    else:
                        meta = metadata_val or {}
                    subcat = meta.get("subcategory") or ""
                    topic_val = meta.get("topic") or ""

                    if is_sqlite:
                        # Update metadata in SQLite
                        meta["internalized"] = True
                        meta["internalized_at"] = datetime.now(timezone.utc).isoformat()
                        await db_conn.execute("""
                            UPDATE memories 
                            SET source_type = 'knowledge', importance = ?, metadata = ?,
                                team_id = 'public'
                            WHERE id = ?
                        """, (new_importance, json.dumps(meta), mid))
                    else:
                        await pool_conn.execute("""
                            UPDATE memories 
                            SET source_type = 'knowledge',
                                team_id = 'public',
                                category = $3,
                                subcategory = $4,
                                topic = $5,
                                importance = $2,
                                metadata = metadata || '{"internalized": true, "internalized_at": "now"}'
                            WHERE id = $1
                        """, mid, new_importance, cat, subcat, topic_val)

                    # Re-index vector into public Qdrant collection
                    if self.retrieval and hasattr(self.retrieval, 'qdrant') and self.registry:
                        try:
                            qs = self.retrieval.qdrant
                            qs.ensure_collection("memory_team_public")
                            # Re-embed content for public pool
                            vec = await self.registry.embed_single(title[:500] + " " + content[:500])
                            qs.client.upsert(
                                collection_name="memory_team_public",
                                points=[{
                                    "id": mid,
                                    "vector": vec,
                                    "payload": {
                                        "memory_id": mid,
                                        "title": title,
                                        "text": content[:500],
                                        "source_type": "knowledge",
                                        "topic": topic_val or cat or "",
                                        "team_id": "public"
                                    }
                                }]
                            )
                        except Exception as e:
                            logging.warning(f"Failed to index public vector for {mid}: {e}")

                    promoted_count += 1
                else:
                    # Mark as evaluated but not promoted
                    if is_sqlite:
                        meta = json.loads(r["metadata"]) if r["metadata"] else {}
                        meta["internalized"] = False
                        await db_conn.execute("UPDATE memories SET metadata = ? WHERE id = ?", (json.dumps(meta), mid))
                    else:
                        await pool_conn.execute("""
                            UPDATE memories 
                            SET metadata = metadata || '{"internalized": false}'
                            WHERE id = $1
                        """, mid)
            
            if is_sqlite: await db_conn.commit()
        finally:
            if is_sqlite: await db_conn.close()
            else: await self.pg.pool.release(pool_conn)
            
        return promoted_count
