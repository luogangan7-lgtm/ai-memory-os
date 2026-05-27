"""Document processor — two-tier: T1 system vectorization, T2 user LLM deep processing."""
import re, hashlib, uuid, json
from pathlib import Path

async def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == '.pdf':
        import PyPDF2
        reader = PyPDF2.PdfReader(file_path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix in ('.md', '.markdown', '.txt'):
        return Path(file_path).read_text(encoding='utf-8', errors='ignore')
    raise ValueError(f"Unsupported: {suffix}")

def semantic_chunks(text: str, chunk_size: int = 600, overlap: int = 80) -> list[dict]:
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    chunks = []
    current_chunk: list[str] = []
    current_len = 0
    chunk_index = 0
    for para in paragraphs:
        # Use character count for CJK text, word count for Latin
        has_cjk = bool(re.search(r'[一-鿿㐀-䶿]', para))
        para_len = len(para) if has_cjk else len(para.split())
        if current_len + para_len > chunk_size and current_chunk:
            chunks.append({"index": chunk_index, "content": "\n\n".join(current_chunk), "word_count": current_len})
            chunk_index += 1
            overlap_para = current_chunk[-1] if current_chunk else ""
            current_chunk = [overlap_para, para] if overlap_para else [para]
            current_len = len(overlap_para.split()) + para_len
        else:
            current_chunk.append(para)
            current_len += para_len
    if current_chunk:
        chunks.append({"index": chunk_index, "content": "\n\n".join(current_chunk), "word_count": current_len})
    return chunks

async def process_tier1(file_path: str, team_id: str, doc_id: str, doc_title: str, pg_repo, qdrant_store, registry) -> dict:
    """Tier 1: extract text → chunk → embed → store. System cost, immediate."""
    text = await extract_text(file_path)
    if not text.strip(): return {"success": False, "error": "Empty document"}
    chunks = semantic_chunks(text)
    if not chunks: return {"success": False, "error": "No content"}
    stored = 0
    for ch in chunks:
        content_hash = hashlib.md5(ch["content"].encode()).hexdigest()
        async with pg_repo.pool.acquire() as conn:
            dup = await conn.fetchval("SELECT id FROM memories WHERE team_id=$1 AND dedup_hash=$2", team_id, content_hash)
            if dup: stored += 1; continue
            mid = str(uuid.uuid4())
            await conn.execute("""INSERT INTO memories (id, team_id, agent_id, title, content, source_type, layer, category, dedup_hash)
                VALUES ($1,$2,'system',$3,$4,'document','DOC','文档知识',$5)""",
                mid, team_id, f"{doc_title} [ch{ch['index']+1}]", ch["content"][:5000], content_hash)
            try:
                vec = await registry.embed_single(ch["content"][:1000])
                qdrant_store._ensure_collection(f"memory_team_{team_id}")
                qdrant_store.client.upsert(collection_name=f"memory_team_{team_id}", points=[{
                    "id": mid, "vector": vec,
                    "payload": {"memory_id": mid, "text": ch["content"][:500], "source_type": "document", "layer": "DOC", "doc_id": doc_id, "team_id": team_id}
                }])
            except: pass
            stored += 1
    return {"success": True, "tier": 1, "chunks": len(chunks), "stored": stored}


# ── T2: User LLM Deep Processing ──────────────────────────────────────────

T2_DEEP_ANALYSIS_PROMPT = """你是一个文档深度分析助手。请仔细阅读以下文档，输出严格的 JSON：
{"summary": "200-400字摘要", "key_topics": ["主题"], "entities": [{"name": "名称", "type": "person/organization/concept/tool/event/place/other", "description": "一句话描述"}]}
不要 markdown 代码块。"""

async def process_tier2(doc_id: str, doc_title: str, team_id: str, pg_repo, qdrant_store, registry) -> dict:
    """Tier 2: auto-match user LLM → deep analysis → store summary + entities + relations."""
    import httpx
    from backend.graph.neo4j_store import GraphStore

    # Step 0: Auto-match user LLM config
    llm_cfg = None
    try:
        llm_cfg = await pg_repo.get_active_user_provider_config(team_id)
    except Exception:
        pass

    if not llm_cfg or not llm_cfg.get("api_key"):
        return {"tier": 2, "skipped": True, "reason": "no_llm_config"}

    api_key = llm_cfg["api_key"]
    base_url = (llm_cfg.get("api_base_url") or "").rstrip("/")
    model = llm_cfg.get("model_name", "deepseek-chat")

    # Step 1: Read document content from T1 (main record)
    doc_text = ""
    try:
        async with pg_repo.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT content FROM memories WHERE id=$1", doc_id)
            if row and row["content"]:
                doc_text = row["content"]
            else:
                # Fallback: search by filename in chunks
                rows = await conn.fetch(
                    "SELECT content FROM memories WHERE team_id=$1 AND source_type='document' AND title LIKE $2 ORDER BY created_at LIMIT 1",
                    team_id, f"%{doc_title}%")
                if rows:
                    doc_text = rows[0]["content"]
    except Exception as e:
        return {"tier": 2, "error": f"read_doc_failed: {e}"}

    if not doc_text or len(doc_text.strip()) < 50:
        return {"tier": 2, "skipped": True, "reason": "doc_too_short"}

    # Step 2: Call user LLM for deep analysis (user cost)
    truncated = doc_text[:12000]  # respect context window
    prompt = f"{T2_DEEP_ANALYSIS_PROMPT}\n\n=== 文档内容 ===\n{truncated}"

    analysis = None
    raw_json = ""
    try:
        _timeout = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)
        async with httpx.AsyncClient(timeout=_timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a document analyst. Output only JSON, no markdown."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                headers={"Authorization": f"Bearer {api_key}"}
            )
        if resp.status_code == 200:
            raw_json = resp.json()["choices"][0]["message"]["content"]
            from backend.utils.response import clean_llm_content
            raw_json = clean_llm_content(raw_json).strip()
            # Parse JSON response
            if raw_json.startswith("```"):
                raw_json = raw_json.split("```")[1]
                if raw_json.startswith("json"):
                    raw_json = raw_json[4:]
            raw_json = raw_json.strip()
            analysis = json.loads(raw_json)
        elif resp.status_code in (401, 403):
            return {"tier": 2, "error": f"llm_auth_failed_http_{resp.status_code}"}
        else:
            return {"tier": 2, "error": f"llm_http_{resp.status_code}", "detail": (raw_json if isinstance(raw_json, str) else str(raw_json))[:200]}
    except json.JSONDecodeError:
        # Fallback: store raw text as summary
        analysis = {"summary": raw_json[:500], "key_topics": [], "entities": []}
    except Exception as e:
        return {"tier": 2, "error": f"llm_call_failed: {e}"}

    if not analysis:
        return {"tier": 2, "error": "empty_analysis"}

    # Step 3: Store summary as L2 memory
    summary_id = str(uuid.uuid4())
    summary_text = analysis.get("summary", "")[:5000]
    key_topics = analysis.get("key_topics", [])
    entities = analysis.get("entities", [])
    dedup = hashlib.md5(summary_text.encode()).hexdigest()

    try:
        async with pg_repo.pool.acquire() as conn:
            # Check if already processed (dedup)
            existing = await conn.fetchval(
                "SELECT id FROM memories WHERE team_id=$1 AND dedup_hash=$2 AND source_type='doc_summary'",
                team_id, dedup)
            if existing:
                return {"tier": 2, "skipped": True, "reason": "already_processed", "existing_id": existing}

            await conn.execute(
                """INSERT INTO memories (id, team_id, agent_id, title, content, summary, source_type, layer, category, dedup_hash)
                   VALUES ($1,$2,'system',$3,$4,$5,'doc_summary','L2','文档摘要',$6)""",
                summary_id, team_id, f"[摘要] {doc_title}", summary_text, summary_text, dedup)

        # Vectorize summary
        try:
            vec = await registry.embed_single(summary_text[:1000])
            qdrant_store._ensure_collection(f"memory_team_{team_id}")
            qdrant_store.client.upsert(collection_name=f"memory_team_{team_id}", points=[{
                "id": summary_id, "vector": vec,
                "payload": {"memory_id": summary_id, "text": summary_text[:500],
                            "source_type": "doc_summary", "layer": "L2",
                            "doc_id": doc_id, "team_id": team_id, "key_topics": key_topics}
            }])
        except Exception as e:
            print(f"[Doc T2] vectorize summary failed: {e}")

    except Exception as e:
        return {"tier": 2, "error": f"store_summary_failed: {e}"}

    # Step 4: Write entities to Neo4j knowledge graph
    neo_count = 0
    try:
        neo = GraphStore()
        # Create memory node for the document
        await neo.create_memory_node(doc_id, doc_title, "文档知识", "document")
        # Create memory node for the summary
        await neo.create_memory_node(summary_id, f"[摘要] {doc_title}", "文档摘要", "summary")
        await neo.create_semantic_relation(doc_id, summary_id, "GENERALIZES", team_id)

        for ent in entities[:15]:  # max 15 entities
            ent_name = ent.get("name", "")
            ent_type = ent.get("type", "concept")
            ent_desc = ent.get("description", "")
            if not ent_name:
                continue
            # Store each entity as a Memory node (reuse existing schema)
            ent_id = str(uuid.uuid4())
            await neo.create_memory_node(ent_id, ent_name, ent_type, "entity")
            # Link entity to document
            await neo.create_semantic_relation(doc_id, ent_id, "HAS_ENTITY", team_id)
            neo_count += 1
    except Exception as e:
        print(f"[Doc T2] Neo4j entity write failed (non-fatal): {e}")

    # Step 5: Semantic relations - find similar memories via Qdrant
    rel_count = 0
    try:
        vec = await registry.embed_single(summary_text[:1000])
        similar = qdrant_store.hybrid_search(vec, summary_text[:300], team_id=team_id, top_k=5)
        neo = GraphStore()
        for sim in similar:
            sim_id = sim.get("payload", {}).get("memory_id", "")
            if sim_id and sim_id != summary_id and sim_id != doc_id:
                try:
                    await neo.create_semantic_relation(summary_id, sim_id, "RELATES_TO", team_id)
                    rel_count += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"[Doc T2] Semantic relations failed (non-fatal): {e}")

    return {
        "tier": 2,
        "success": True,
        "summary_id": summary_id,
        "key_topics": key_topics,
        "entities_count": len(entities),
        "neo4j_entities": neo_count,
        "relations": rel_count,
    }
