"""Document processor — two-tier: T1 system vectorization, T2 user LLM deep processing."""
import re, hashlib, uuid
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
        para_len = len(para.split())
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
