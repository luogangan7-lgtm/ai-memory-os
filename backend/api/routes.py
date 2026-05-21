# AI Memory OS - API Routes
# Blueprint Section 8

from __future__ import annotations

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from fastapi import UploadFile, File, Form

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)


from backend.auth.middleware import create_access_token, get_current_team, get_agent_id, get_user_context
from backend.memory.pg_repo import MemoryRepo
from backend.graph.neo4j_store import GraphStore
from backend.memory.ingestion import IngestionPipeline
from backend.memory.qdrant_store import QdrantStore
from backend.memory.retrieval import RetrievalPipeline
from backend.memory.file_ingest import extract_text
from backend.memory.minio_store import MinIOStore
from backend.memory.lifecycle import LifecycleStage, compute_next_stage, compute_freshness
from backend.reflection.engine import ReflectionEngine
from backend.services.classifier import classify_memory
from backend.models.schemas import (
    LifecycleTransitionRequest,
    GraphQueryRequest,
    GraphResponse,
    LongTermMemoryRequest,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStoreRequest,
)
from backend.services.config import settings
from backend.manager.registry import ModelRegistry

router = APIRouter()

qdrant_store: QdrantStore | None = None
graph_store: GraphStore | None = None
ingestion: IngestionPipeline | None = None
retrieval: RetrievalPipeline | None = None
pg_repo: MemoryRepo | None = None


registry: ModelRegistry | None = None


def init_stores(qs, gs, ip, rp, pg, reg):
    global qdrant_store, graph_store, ingestion, retrieval, pg_repo, registry
    qdrant_store = qs
    graph_store = gs
    ingestion = ip
    retrieval = rp
    pg_repo = pg
    registry = reg


# @router.get("/")
# async def root():
#     return {"status": "ok", "version": settings.version}




@router.post("/auth/send-code")
async def send_verification_code(data: dict):
    """Send a 6-digit verification code to the user's email."""
    email = (data.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")
    from backend.services.email_verify import send_code
    ok = await send_code(email)
    if not ok:
        raise HTTPException(500, "Failed to send code. Try again.")
    return {"sent": True, "message": "Verification code sent"}

@router.post("/auth/register")
async def register_user_endpoint(data: dict):
    from backend.auth.accounts import register
    try:
        username = data.get("username")
        password = data.get("password")
        email = (data.get("email") or "").strip()
        code = (data.get("code") or "").strip()
        team_id = data.get("team_id") or username or "default"
        
        if not email or not password:
            raise HTTPException(400, "Email and password required")
        
        # Verify email code
        from backend.services.email_verify import verify_code
        valid = await verify_code(email, code)
        if not valid:
            raise HTTPException(400, "Invalid or expired verification code")
            
        result = await register(team_id, username or email, password, "user", email=email)
        return {
            "status": "success", 
            "user_id": result["username"], 
            "team_id": team_id, 
            "email": email,
            "api_key": result["api_key"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/auth/token")
async def login_endpoint(data: dict):
    from backend.auth.accounts import login
    from backend.auth.middleware import create_access_token
    
    username_or_email = data.get("username") or data.get("email")
    password = data.get("password")
    
    try:
        acc = await login(username_or_email, password)
        token = create_access_token(acc["team_id"], role=acc["role"])
        import json as _json
        from fastapi.responses import JSONResponse
        data = {
            "access_token": token,
            "api_key": acc["api_key"],
            "team_id": acc["team_id"],
            "username": acc["username"]
        }
        resp = JSONResponse(content=data)
        resp.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=86400
        )
        return resp
    except Exception as e:
        raise HTTPException(401, str(e))





@router.post("/auth/logout")
async def logout_endpoint():
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"status": "logged_out"})
    resp.delete_cookie("access_token")
    return resp


@router.post("/memory/promote")
async def promote_to_knowledge(
    data: dict,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id),
):
    """Promote an agent's personal memory to team knowledge."""
    if not pg_repo: raise HTTPException(503)
    mid = data.get("memory_id", "")
    if not mid: raise HTTPException(400, "memory_id required")
    
    memory = await pg_repo.get(mid)
    if not memory: raise HTTPException(404)
    
    # Clear agent_id to make it team knowledge (visible to all)
    async with pg_repo.pool.acquire() as conn:
        await conn.execute(
            "UPDATE memories SET agent_id = '', lifecycle_stage = 'longterm', "
            "importance = GREATEST(importance, 0.8), updated_at = $2 WHERE id = $1",
            mid, datetime.now(timezone.utc)
        )
    
    return {"memory_id": mid, "promoted": True, "stage": "longterm"}

@router.post("/memory/remember")
async def remember(
    req: MemoryStoreRequest,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id),
):
    """Auto-store: agents call this after conversations. Quick store with auto-summary."""
    memory_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{team_id}:{agent_id}:{req.content[:100]}"))

    # Check if similar memory exists
    if pg_repo:
        existing = await pg_repo.get(memory_id)
        if existing:
            # Update access count and freshness
            await pg_repo.update_access(memory_id)
            return {"id": memory_id, "status": "updated"}

    # Auto-classify if category is generic
    auto_cat, auto_sub, auto_topic = req.category, req.subcategory, req.topic
    if (not auto_cat or auto_cat == "general") and (req.content or req.title):
        from backend.services.classifier import classify_memory
        clf = await classify_memory(req.content or "", req.title or "", registry)
        auto_cat, auto_sub, auto_topic = clf["category"], clf["subcategory"], clf["topic"]

    # Store new memory
    if pg_repo:
        await pg_repo.insert(
            id=memory_id, team_id=team_id, workspace_id=req.workspace_id,
            agent_id=agent_id, category=auto_cat, subcategory=auto_sub, topic=auto_topic,
            title=req.title or auto_topic or "Agent Memory", content=req.content,
            summary=req.summary, embedding_model=req.embedding_model,
            importance=req.importance, confidence=req.confidence,
            source_type=req.source_type or "agent", source_uri=req.source_uri,
            tags=req.tags, metadata=req.metadata,
        )
    if ingestion:
        try:
            await ingestion.ingest(
                content=req.content, memory_id=memory_id,
                team_id=team_id, workspace_id=req.workspace_id or agent_id,
                embedding_fn=registry.embed_single, category=auto_cat, 
                source_type=req.source_type or "agent",
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Ingestion failed for {memory_id} (will retry later): {e}"
            )

    return {"id": memory_id, "status": "stored"}

@router.get("/memory/recent")
async def list_recent_memories(
    team_id: str = Depends(get_current_team),
    limit: int = 24,
    filter: str = "all",
    category: str = None,
    source_type: str = None,
):
    """List recent memories with optional filtering."""
    if not pg_repo: raise HTTPException(503)
    rows = await pg_repo.list_recent(team_id, limit, filter, category, source_type)
    return rows



@router.patch("/memory/{memory_id}")
async def update_memory(
    memory_id: str,
    body: dict,
    team_id: str = Depends(get_current_team),
):
    """Update an existing memory (V6.0)."""
    if not pg_repo: raise HTTPException(503)
    ok = await pg_repo.update(memory_id, team_id, **body)
    if not ok: raise HTTPException(404, "Memory not found or not owned by you")
    return {"ok": True}

@router.post("/memory/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(None),
    source_type: str = Form("document"),
    importance: float = Form(0.5),
    tags: str = Form(""),
    team_id: str = Depends(get_current_team),
):
    """Upload a document, split/parse, classify, insert into memories & documents, and ingest into memory."""
    if not ingestion or not pg_repo:
        raise HTTPException(status_code=503, detail="Not ready")

    # 1. Read and Save to MinIO
    file_bytes = await file.read()
    memory_id = str(uuid.uuid4())
    object_name = f"{team_id}/docs/{memory_id}_{file.filename}"
    
    try:
        minio = MinIOStore()
        minio.upload(object_name, file_bytes, file.content_type or "application/octet-stream")
        source_uri = f"minio://{object_name}"
    except Exception:
        source_uri = file.filename

    # 2. Extract Text
    import tempfile
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        text = extract_text(tmp_path)
    finally:
        if os.path.exists(tmp_path): os.unlink(tmp_path)

    # 3. Classify Memory
    from backend.services.classifier import classify_memory
    clf = await classify_memory(text, file.filename, registry)
    final_category = category if category else clf["category"]

    # 4. Store in Postgres memories table (so it is searchable/viewable as a memory)
    await pg_repo.insert(
        id=memory_id, team_id=team_id, workspace_id="default",
        category=final_category, subcategory=clf["subcategory"], topic=clf["topic"],
        title=file.filename, content=text,
        embedding_model="text-embedding-v3",
        importance=importance, confidence=0.9,
        source_type=source_type, source_uri=source_uri,
        tags=tags.split(",") if tags else [],
        metadata={"filename": file.filename, "size": len(text)},
    )

    # 5. Ingest chunks into Vector Store and chunks table
    chunks_results = await ingestion.ingest(
        content=text, memory_id=memory_id,
        team_id=team_id, workspace_id="default",
        embedding_fn=registry.embed_single,
        title=file.filename, category=final_category, source_type=source_type,
    )

    # 6. Record Document Meta in Postgres documents table (for file tracking)
    await pg_repo.insert_document(
        team_id=team_id,
        filename=file.filename,
        minio_key=object_name,
        chunk_count=len(chunks_results) if chunks_results else 1,
        file_size=len(file_bytes),
        tags=tags.split(",") if tags else []
    )

    return {
        "id": memory_id,
        "filename": file.filename,
        "category": final_category,
        "status": "processed"
    }

@router.get("/memory/documents")
async def list_documents(team_id: str = Depends(get_current_team)):
    if not pg_repo: raise HTTPException(503)
    docs = await pg_repo.list_documents(team_id)
    return docs

@router.delete("/memory/documents/{doc_id}")
async def delete_document(doc_id: str, team_id: str = Depends(get_current_team)):
    if not pg_repo: raise HTTPException(503)
    from backend.memory.pg_repo import safe_uuid
    
    # 1. Fetch document metadata to find minio_key
    async with pg_repo.pool.acquire() as conn:
        doc = await conn.fetchrow("SELECT * FROM documents WHERE id = $1 AND team_id = $2", safe_uuid(doc_id), team_id)
    if not doc:
        raise HTTPException(404, "Document not found")
        
    doc_dict = dict(doc)
    minio_key = doc_dict.get("minio_key")
    
    # 2. Find and delete corresponding memories and their Qdrant vectors
    source_uri = f"minio://{minio_key}" if minio_key else ""
    if source_uri:
        async with pg_repo.pool.acquire() as conn:
            mem_rows = await conn.fetch("SELECT id FROM memories WHERE source_uri = $1 AND team_id = $2", source_uri, team_id)
        for r in mem_rows:
            mem_id = str(r["id"])
            await pg_repo.delete(mem_id, team_id)
            if qdrant_store:
                try:
                    await qdrant_store.delete(mem_id, team_id=team_id)
                except Exception as e:
                    logger.warning("[delete_document] Qdrant delete failed for memory %s: %s", mem_id, e)

    # 3. Delete from MinIO
    if minio_key:
        try:
            minio = MinIOStore()
            minio.delete(minio_key)
        except Exception as e:
            logger.warning("[delete_document] MinIO delete failed for key %s: %s", minio_key, e)

    # 4. Delete document entry from DB
    ok = await pg_repo.delete_document(doc_id, team_id)
    return {"ok": ok}



@router.get("/memory/{memory_id}")
async def get_memory_detail(
    memory_id: str,
    ctx: dict = Depends(get_user_context)
):
    """Get full memory detail by ID."""
    if not pg_repo: raise HTTPException(503, "Database not ready")
    memory = await pg_repo.get(memory_id)
    if not memory: raise HTTPException(404, "Memory not found")
    if memory["team_id"] != ctx["team_id"]:
        raise HTTPException(403, "Access denied")
    # Count chunks
    chunk_count = 0
    try:
        async with pg_repo.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) as c FROM chunks WHERE memory_id = $1", memory_id)
            chunk_count = row["c"] if row else 0
    except: pass
    return {**memory, "chunk_count": chunk_count}

@router.get("/memory/{memory_id}/chunks")
async def get_memory_chunks(
    memory_id: str,
    ctx: dict = Depends(get_user_context)
):
    """Get chunks for a memory."""
    if not pg_repo: raise HTTPException(503, "Database not ready")
    memory = await pg_repo.get(memory_id)
    if not memory: raise HTTPException(404, "Memory not found")
    if memory["team_id"] != ctx["team_id"]:
        raise HTTPException(403, "Access denied")
    async with pg_repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chunk_index, content, token_count FROM chunks WHERE memory_id = $1 ORDER BY chunk_index",
            memory_id
        )
    return [dict(r) for r in rows]
@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    ctx: dict = Depends(get_user_context)
):
    """Delete a memory entry with ownership check."""
    if not pg_repo: raise HTTPException(503)
    
    # 1. Fetch memory to check ownership
    memory = await pg_repo.get(memory_id)
    if not memory: raise HTTPException(404, "Memory not found")
    
    # 2. Check Permissions
    if memory["team_id"] != ctx["team_id"]:
        raise HTTPException(403, "Access denied")
        
    # 3. Perform deletion
    ok = await pg_repo.delete(memory_id, ctx["team_id"])
    if qdrant_store and ok:
        await qdrant_store.delete(memory_id, team_id=ctx["team_id"])
    return {"deleted": ok}


@router.get("/stats")
async def get_user_stats(team_id: str = Depends(get_current_team)):
    """Get stats for the current team's dashboard."""
    if not pg_repo: raise HTTPException(503)
    total = await pg_repo.count_by_team(team_id)

    total_tokens = 0
    pipeline_calls = 0
    new_today = 0
    total_documents = 0
    active_agents: list[str] = []
    try:
        from backend.memory.pg_repo import safe_uuid
        async with pg_repo.pool.acquire() as conn:
            tok_row = await conn.fetchrow(
                "SELECT COALESCE(SUM(total_tokens), 0) as t FROM user_token_usage WHERE user_id = $1",
                safe_uuid(team_id)
            )
            total_tokens = int(tok_row["t"]) if tok_row else 0

            pipe_row = await conn.fetchrow(
                "SELECT COALESCE(SUM(l1_calls + l2_calls + l3_calls), 0) as p FROM pipeline_usage WHERE team_id = $1",
                team_id
            )
            pipeline_calls = int(pipe_row["p"]) if pipe_row else 0

            # Memories added in the last 24 hours
            today_row = await conn.fetchrow(
                "SELECT COUNT(*) as n FROM memories WHERE team_id = $1 AND created_at >= now() - interval '24 hours'",
                team_id
            )
            new_today = int(today_row["n"]) if today_row else 0

            # Total uploaded documents
            doc_row = await conn.fetchrow(
                "SELECT COUNT(*) as n FROM documents WHERE team_id = $1",
                team_id
            )
            total_documents = int(doc_row["n"]) if doc_row else 0

            # Distinct non-default agents active in the last 7 days
            agent_rows = await conn.fetch(
                """SELECT DISTINCT agent_id FROM memories
                   WHERE team_id = $1
                     AND agent_id IS NOT NULL
                     AND agent_id NOT IN ('', 'default', 'system')
                     AND created_at >= now() - interval '7 days'
                   ORDER BY agent_id LIMIT 10""",
                team_id
            )
            active_agents = [r["agent_id"] for r in agent_rows]
    except Exception as e:
        logger.warning("[stats] %s", e)

    return {
        "total": total,
        "total_memories": total,
        "total_tokens": total_tokens,
        "pipeline_calls": pipeline_calls,
        "tokens_saved": total_tokens // 5,
        "new_today": new_today,
        "total_documents": total_documents,
        "active_agents": active_agents,
        "agent": 0,
    }

@router.post("/memory/store", response_model=MemoryResponse)
async def store_memory(
    req: MemoryStoreRequest,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id),
):
    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Enforce max memory length from security config
    from backend.services.config import load_system_config
    sys_config = load_system_config()
    max_mem_len = sys_config.get("security", {}).get("max_mem_len", 10000)
    if req.content and len(req.content) > max_mem_len:
        req.content = req.content[:max_mem_len]

    # Auto-classify if category not provided
    auto_category = req.category
    auto_subcategory = req.subcategory
    auto_topic = req.topic
    if not auto_category and (req.content or req.title):
        try:
            from backend.services.classifier import classify_memory
            clf = await classify_memory(req.content or "", req.title or "", registry)
            auto_category = clf["category"]
            auto_subcategory = clf["subcategory"]
            auto_topic = clf["topic"] or req.topic
        except Exception:
            pass

    # Determine actual agent_id: payload > token > "default"
    final_agent_id = req.agent_id if req.agent_id else (agent_id if agent_id else "default")

    # Check for active LLM configuration (any provider)
    has_llm = False
    if pg_repo:
        try:
            cfg = await pg_repo.get_active_user_provider_config(team_id)
            if not cfg:
                async with pg_repo.pool.acquire() as conn:
                    r = await conn.fetchrow(
                        "SELECT * FROM user_provider_configs WHERE is_active=true AND api_key IS NOT NULL AND api_key != '' AND (user_id=$1 OR user_id=$2) ORDER BY updated_at DESC LIMIT 1",
                        team_id, str(__import__('backend.memory.pg_repo', fromlist=['safe_uuid']).safe_uuid(team_id))
                    )
                    cfg = dict(r) if r else None
            if cfg and cfg.get("api_key"):
                has_llm = True
        except Exception:
            pass

    # Set pending_pipeline flag if human/chat memory and no LLM config
    if (req.source_type == "human" or req.memory_type == "chat") and not has_llm:
        if req.metadata is None:
            req.metadata = {}
        req.metadata["pending_pipeline"] = True


    # Estimate and record token usage for MCP/agent traffic
    if req.source_type in ("agent", "human", "chat"):
        try:
            from backend.services.cost_tracker import CostTracker
            estimated = CostTracker.estimate_tokens(req.content or "")
            async with pg_repo.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO user_token_usage (user_id, provider_name, model_name, total_tokens, prompt_tokens, created_at)
                       VALUES ($1, 'mcp_agent', 'memory-store', $2, $2, NOW())""",
                    team_id, estimated
                )
        except: pass

    # Persist metadata to PostgreSQL (primary source of truth)
    if pg_repo:
        await pg_repo.insert(
            id=memory_id,
            agent_id=final_agent_id,
            team_id=team_id,
            workspace_id=req.workspace_id,
            category=auto_category,
            subcategory=auto_subcategory,
            topic=auto_topic,
            memory_type=req.memory_type,
            title=req.title,
            content=req.content,
            summary=req.summary,
            embedding_model=req.embedding_model,
            importance=req.importance,
            confidence=req.confidence,
            source_type=req.source_type,
            source_uri=req.source_uri,
            tags=req.tags,
            metadata=req.metadata,
        )

    # Ingest into Qdrant (vector search)
    if ingestion:
        try:
            await ingestion.ingest(
                content=req.content,
                memory_id=memory_id,
                team_id=team_id,
                workspace_id=req.workspace_id,
                embedding_fn=registry.embed_single,
                title=req.title,
                category=auto_category,
                memory_type=req.memory_type,
                agent_id=final_agent_id
            )
        except Exception as e:
            logger.exception("Ingestion failed for memory %s (will retry later): %s", memory_id, e)

    # Create graph node and relations
    if graph_store:
        try:
            await graph_store.create_memory_node(
                memory_id=memory_id, title=req.title,
                category=req.category, memory_type=req.memory_type,
            )
            for rel in req.relations:
                await graph_store.create_relation(
                    source_id=memory_id, target_id=rel.target_id,
                    relation_type=rel.relation_type, weight=rel.weight,
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Graph store failed for {memory_id}: {e}"
            )
    if pg_repo: await pg_repo.audit(memory_id, final_agent_id, "store", {"title": req.title}, team_id=team_id)

    # Trigger L1-L3 memory extraction pipeline for raw user chats
    if (req.source_type == "human" or req.memory_type == "chat") and has_llm:
        try:
            from backend.pipeline.runner import enqueue as enqueue_pipeline
            import asyncio
            asyncio.create_task(
                enqueue_pipeline(
                    team_id=team_id,
                    session_id=final_agent_id or "default",
                    messages=[
                        {"role": "user", "content": req.content}
                    ]
                )
            )
        except Exception as e:
            logger.warning("[pipeline-trigger] %s", e)

    return MemoryResponse(
        id=memory_id, team_id=team_id, workspace_id=req.workspace_id,
        agent_id=final_agent_id,
        category=req.category, subcategory=req.subcategory,
        topic=req.topic, memory_type=req.memory_type,
        title=req.title or "Untitled", content=req.content, summary=req.summary,
        embedding_model=req.embedding_model,
        importance=req.importance, confidence=req.confidence,
        source_type=req.source_type, source_uri=req.source_uri,
        lifecycle_stage=req.lifecycle_stage,
        tags=req.tags, created_at=now, updated_at=now,
    )


@router.post("/memory/search", response_model=list[MemorySearchResult])
async def search_memory(
    req: MemorySearchRequest,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id),
):
    if not retrieval:
        raise HTTPException(status_code=503, detail="Retrieval engine not ready")

    if not req.query or not req.query.strip() or req.query.strip() == "*":
        # If query is empty or wildcard, return the most recent memories from Postgres
        if pg_repo:
            async with pg_repo.pool.acquire() as conn:
                if agent_id and agent_id not in ("default", "system"):
                    rows = await conn.fetch(
                        "SELECT * FROM memories WHERE team_id=$1 AND (agent_id IS NULL OR agent_id='' OR agent_id='default' OR agent_id=$2) ORDER BY created_at DESC LIMIT $3",
                        team_id, agent_id, req.top_k
                    )
                else:
                    rows = await conn.fetch("SELECT * FROM memories WHERE team_id=$1 ORDER BY created_at DESC LIMIT $2", team_id, req.top_k)
                
                out = []
                for r in rows:
                    m = dict(r)
                    m["id"] = str(m["id"])
                    m["category"] = m.get("category") or "general"
                    m["title"] = m.get("title") or "Untitled"
                    m["content"] = m.get("content") or ""
                    m["memory_type"] = m.get("memory_type") or "general"
                    m["importance"] = float(m.get("importance") if m.get("importance") is not None else 0.5)
                    m["confidence"] = float(m.get("confidence") if m.get("confidence") is not None else 0.5)
                    m["embedding_model"] = m.get("embedding_model") or "text-embedding-v3"
                    m["agent_id"] = m.get("agent_id") or ""
                    m["lifecycle_stage"] = m.get("lifecycle_stage") or "recent"
                    m["source_type"] = m.get("source_type") or "human"
                    m["tags"] = m.get("tags") or []
                    m["created_at"] = m["created_at"].isoformat() if m.get("created_at") else "2026-05-01T00:00:00Z"
                    m["updated_at"] = m["updated_at"].isoformat() if m.get("updated_at") else "2026-05-01T00:00:00Z"
                    out.append({
                        "id": str(r["id"]),
                        "score": 1.0,
                        "memory": m,
                        "chunk_text": r["content"] or ""
                    })
                return out
        return []

    # Phase 1: Team knowledge search
    results = await retrieval.search(
        query=req.query, embedding_fn=registry.embed_single,
        team_id=team_id, workspace_id=req.workspace_id,
        top_k=req.top_k, use_rerank=req.use_rerank,
        rerank_fn=registry.rerank if req.use_rerank and registry else None,
        use_graph=req.use_graph, min_confidence=req.min_confidence,
    ) or []

    # Phase 2: Personal memory search (if agent_id is set)
    if agent_id and agent_id != "default":
        personal = await retrieval.search(
            query=req.query, embedding_fn=registry.embed_single,
            team_id=team_id, workspace_id=agent_id,
            top_k=min(req.top_k, 5), use_rerank=req.use_rerank,
            rerank_fn=registry.rerank if req.use_rerank and registry else None,
            min_confidence=req.min_confidence,
        ) or []
        # Fuse: interleave personal memories with team results
        fused = []
        pi, ki = 0, 0
        while len(fused) < req.top_k and (pi < len(personal) or ki < len(results)):
            if pi < len(personal) and (ki >= len(results) or pi <= ki):
                personal[pi]["score"] *= 1.1  # slight boost for personal
                fused.append(personal[pi]); pi += 1
            else:
                fused.append(results[ki]); ki += 1
        results = fused
    
    # Enrich with PostgreSQL metadata if available
    memory_ids = [r["payload"].get("memory_id", r["id"]) for r in results]
    # Filter: remove other agents personal memories from team results
    if agent_id and agent_id != "default":
        results = [r for r in results if not r["payload"].get("agent_id") or r["payload"].get("agent_id") in ("", "default") or r["payload"].get("agent_id") == agent_id]
    # Fetch PG metadata (always)
    pg_rows: dict = {}
    if pg_repo and memory_ids:
        rows = await pg_repo.get_by_ids(memory_ids)
        pg_rows = {str(row["id"]): dict(row) for row in rows}

    out = []
    for r in results:
        mid = r["payload"].get("memory_id", r["id"])
        pg = pg_rows.get(str(mid), {})
        out.append(MemorySearchResult(
            memory=MemoryResponse(
                id=str(mid),
                team_id=team_id,
                workspace_id=req.workspace_id,
                category=pg.get("category") or r["payload"].get("category") or "general",
                title=pg.get("title") or r["payload"].get("title") or "Untitled",
                content=pg.get("content") or r["payload"].get("text") or "",
                memory_type=pg.get("memory_type") or r["payload"].get("memory_type") or "general",
                importance=float(pg.get("importance") if pg.get("importance") is not None else r["payload"].get("importance", 0.5)),
                confidence=float(pg.get("confidence") if pg.get("confidence") is not None else r["payload"].get("confidence", 0.5)),
                embedding_model=pg.get("embedding_model") or r["payload"].get("embedding_model") or "text-embedding-v3",
                agent_id=pg.get("agent_id") or r["payload"].get("agent_id") or "",
                lifecycle_stage=pg.get("lifecycle_stage") or "recent",
                source_type=pg.get("source_type") or "human",
                tags=pg.get("tags") or r["payload"].get("tags") or [],
                created_at=str(pg.get("created_at") or "2026-05-01T00:00:00Z"),
                updated_at=str(pg.get("updated_at") or "2026-05-01T00:00:00Z"),
            ),
            score=r["score"],
            chunk_text=r["payload"].get("text"),
            graph_context=r.get("graph_context", []),
        ))
    return out





@router.get("/memory/backup")
async def backup_memories(team_id: str = Depends(get_current_team)):
    """Export all memories for a team as JSON."""
    if not pg_repo:
        raise HTTPException(status_code=503)
    async with pg_repo.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM memories WHERE team_id = $1 ORDER BY created_at", team_id)
    import json
    from datetime import datetime
    data = [dict(r) for r in rows]
    for d in data:
        for k, v in d.items():
            if isinstance(v, datetime): d[k] = v.isoformat()
    return {"team_id": team_id, "count": len(data), "memories": data}

@router.post("/memory/restore")
async def restore_memories(data: dict, team_id: str = Depends(get_current_team)):
    """Import memories from a backup JSON."""
    if not pg_repo:
        raise HTTPException(status_code=503)
    memories = data.get("memories", [])
    count = 0
    for m in memories:
        if m.get("team_id") == team_id or data.get("force", False):
            m["team_id"] = team_id
            await pg_repo.insert(**m)
            count += 1
    return {"restored": count}


@router.get("/memory/gaps")
async def knowledge_gaps(team_id: str = Depends(get_current_team)):
    """Show knowledge gaps: topics needing more coverage."""
    if not pg_repo: raise HTTPException(503)
    engine = ReflectionEngine(pg_repo, graph_store, registry=registry, retrieval=retrieval)
    gaps = await engine._detect_gaps(team_id)
    return {"gaps": gaps, "note": "Topics with <2 sources or low confidence need review"}

@router.post("/memory/reflect")
async def run_reflection(
    team_id: str = Depends(get_current_team),
):
    """Run a full reflection cycle: auto-promote, decay freshness, detect duplicates."""
    if not pg_repo:
        raise HTTPException(status_code=503, detail="Database not ready")
    engine = ReflectionEngine(pg_repo, graph_store, registry=registry, retrieval=retrieval)
    report = await engine.reflect_all(team_id)
    return report



@router.post("/memory/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    category: str = Form("general"),
    team_id: str = Depends(get_current_team),
):
    """Upload an image, OCR it, and store the result."""
    from backend.memory.ocr import ocr_image
    if not pg_repo or not ingestion:
        raise HTTPException(status_code=503)

    suffix = Path(file.filename).suffix if file.filename else ".png"
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = ocr_image(tmp_path)
    except Exception:
        text = "(OCR failed)"
    finally:
        os.unlink(tmp_path)

    memory_id = str(uuid.uuid4())
    title = f"OCR: {file.filename or 'image'}"
    await pg_repo.insert(
        id=memory_id, team_id=team_id, workspace_id="default",
        category=category, title=title, content=text,
        embedding_model="text-embedding-v3",
        importance=0.7, confidence=0.8,
        source_type="image", source_uri=file.filename,
        tags=["ocr"], metadata={"type": "image"},
    )
    await ingestion.ingest(
        content=text, memory_id=memory_id, team_id=team_id,
        workspace_id="default", embedding_fn=registry.embed_single,
        title=title, category=category, memory_type="general",
    )
    return {"id": memory_id, "title": title, "ocr_text": text[:200] + "..." if len(text) > 200 else text}



@router.post("/memory/lifecycle")
async def transition_lifecycle(
    req: LifecycleTransitionRequest,
    team_id: str = Depends(get_current_team),
):
    """Manually promote or demote a memory between lifecycle stages."""
    if not pg_repo:
        raise HTTPException(status_code=503, detail="Database not ready")
    memory = await pg_repo.get(req.memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if memory["team_id"] != team_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target = LifecycleStage(req.target_stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {req.target_stage}")

    # Update freshness
    fresh = compute_freshness(memory)
    async with pg_repo.pool.acquire() as conn:
        await conn.execute(
            "UPDATE memories SET lifecycle_stage = $1, freshness = $2, updated_at = $3 WHERE id = $4",
            target.value, fresh, datetime.now(timezone.utc), req.memory_id,
        )

    return {"memory_id": req.memory_id, "stage": target.value, "freshness": round(fresh, 4)}



@router.get("/graph/visualization")
async def graph_visualization():
    """Return full Neo4j graph data for visualization."""
    if not graph_store:
        raise HTTPException(status_code=503, detail="Graph store not ready")
    try:
        data = await graph_store.get_full_graph()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/summary")
async def graph_summary():
    if not graph_store:
        raise HTTPException(status_code=503, detail="Graph store not ready")
    try:
        data = await graph_store.get_stats() if hasattr(graph_store, "get_stats") else {"nodes": 0, "edges": 0}
        return {"nodes": data.get("nodes", 0), "edges": data.get("edges", 0), "status": "ok"}
    except Exception as e:
        return {"nodes": 0, "edges": 0, "status": f"error: {e}"}

@router.post("/memory/graph", response_model=GraphResponse)
async def query_graph(
    req: GraphQueryRequest,
    team_id: str = Depends(get_current_team),
):
    if not graph_store:
        raise HTTPException(status_code=503, detail="Graph store not ready")
    try:
        data = await graph_store.get_relations(
            memory_id=req.memory_id or "",
            relation_types=req.relation_types or None,
            max_depth=req.max_depth,
            top_k=req.top_k,
        )
        from backend.models.schemas import GraphNode, GraphEdge
        return GraphResponse(
            nodes=[GraphNode(**n) for n in data["nodes"]],
            edges=[GraphEdge(**e) for e in data["edges"]],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/memory/longterm", response_model=list[MemorySearchResult])
async def get_longterm(
    req: LongTermMemoryRequest,
    team_id: str = Depends(get_current_team),
):
    if not retrieval:
        raise HTTPException(status_code=503, detail="Retrieval engine not ready")
    results = await retrieval.search(
        query="longterm core knowledge summary",
        embedding_fn=registry.embed_single,
        team_id=team_id,
        workspace_id=req.workspace_id,
        top_k=req.top_k,
        use_rerank=True,
        rerank_fn=registry.rerank,
        use_graph=True,
        min_confidence=req.min_importance,
    )
    return [
        MemorySearchResult(
            memory=MemoryResponse(
                id=r["payload"].get("memory_id", r["id"]),
                team_id=team_id,
                workspace_id=req.workspace_id,
                category=r["payload"].get("category", ""),
                title=r["payload"].get("title", ""),
                content=r["payload"].get("text", ""),
                memory_type=r["payload"].get("memory_type", "general"),
                importance=float(r["payload"].get("importance", 0.5)),
                confidence=float(r["payload"].get("confidence", 0.5)),
                source_type="human",
                tags=r["payload"].get("tags", []),
                created_at="2026-05-01T00:00:00Z",
                updated_at="2026-05-01T00:00:00Z",
            ),
            score=r["score"],
            chunk_text=r["payload"].get("text"),
            graph_context=r.get("graph_context", []),
        )
        for r in results
    ]



@router.get("/user/stats")
async def get_user_usage_stats(team_id: str = Depends(get_current_team)):
    """Retrieve user usage breakdown, monthly metrics and RAG savings."""
    from backend.api.db_helper import get_db_conn
    from backend.memory.pg_repo import safe_uuid
    import os
    
    total_tokens = 0
    saved_tokens = 0
    saved_usd = 0.0
    rag_hits = 0
    month_tokens = 0
    week_writes = 0
    usage_by_model = []
    
    pipeline_stats = {
        "l1_calls": 0,
        "l2_calls": 0,
        "l3_calls": 0,
        "l1_tokens": 0,
        "l2_tokens": 0,
        "l3_tokens": 0,
        "total_tokens": 0
    }
    
    use_sqlite = os.getenv("MEMORY_OS_USE_STANDALONE", "false").lower() == "true"
    user_id_query = team_id if use_sqlite else safe_uuid(team_id)
    
    conn = await get_db_conn()
    try:
        # 1. Clean up test data
        await conn.execute("DELETE FROM user_token_usage WHERE provider_name = $1", "test")
        
        # 2. Get totals from user_token_usage
        row = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(total_tokens), 0) as total,
                COALESCE(SUM(tokens_saved_estimate), 0) as saved,
                COALESCE(SUM(cost_usd), 0.0) as cost,
                COALESCE(SUM(memory_tokens_injected), 0) as injected
            FROM user_token_usage
            WHERE user_id = $1
        """, user_id_query)
        if row:
            total_tokens = int(row["total"] or 0)
            saved_tokens = int(row["saved"] or 0)
            # Save estimate: e.g. $2 per 1M tokens saved
            saved_usd = float(row["saved"] or 0) / 1000000.0 * 2.0
            rag_hits = int(row["injected"] or 0)
            
        # 3. Monthly tokens (last 30 days)
        if use_sqlite:
            m_tok = await conn.fetchrow("""
                SELECT COALESCE(SUM(total_tokens), 0) as total
                FROM user_token_usage
                WHERE user_id = $1 AND created_at >= datetime('now', '-30 days')
            """, user_id_query)
            month_tokens = int(m_tok["total"] or 0) if m_tok else 0
        else:
            m_tok = await conn.fetchrow("""
                SELECT COALESCE(SUM(total_tokens), 0) as total
                FROM user_token_usage
                WHERE user_id = $1 AND created_at >= now() - interval '30 days'
            """, user_id_query)
            month_tokens = int(m_tok["total"] or 0) if m_tok else 0

        # 4. Weekly writes
        if use_sqlite:
            w_wr = await conn.fetchrow("""
                SELECT COUNT(*) as cnt
                FROM memories
                WHERE team_id = $1 AND created_at >= datetime('now', '-7 days')
            """, team_id)
            week_writes = int(w_wr["cnt"] or 0) if w_wr else 0
        else:
            w_wr = await conn.fetchrow("""
                SELECT COUNT(*) as cnt
                FROM memories
                WHERE team_id = $1 AND created_at >= now() - interval '7 days'
            """, team_id)
            week_writes = int(w_wr["cnt"] or 0) if w_wr else 0

        # 5. Usage by model
        rows = await conn.fetch("""
            SELECT provider_name, model_name,
                   SUM(prompt_tokens) as prompt,
                   SUM(completion_tokens) as completion,
                   SUM(total_tokens) as total
            FROM user_token_usage
            WHERE user_id = $1
            GROUP BY provider_name, model_name
            ORDER BY total DESC
        """, user_id_query)
        for r in rows:
            usage_by_model.append({
                "provider_name": r["provider_name"],
                "model_name": r["model_name"] or "default",
                "prompt_tokens": int(r["prompt"] or 0),
                "completion_tokens": int(r["completion"] or 0),
                "total_tokens": int(r["total"] or 0)
            })

        # 6. Pipeline Usage breakdown
        p_row = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(l1_calls), 0) as l1_c,
                COALESCE(SUM(l2_calls), 0) as l2_c,
                COALESCE(SUM(l3_calls), 0) as l3_c,
                COALESCE(SUM(l1_tokens), 0) as l1_t,
                COALESCE(SUM(l2_tokens), 0) as l2_t,
                COALESCE(SUM(l3_tokens), 0) as l3_t,
                COALESCE(SUM(total_tokens), 0) as total_t
            FROM pipeline_usage
            WHERE team_id = $1
        """, team_id)
        if p_row:
            pipeline_stats = {
                "l1_calls": int(p_row["l1_c"] or 0),
                "l2_calls": int(p_row["l2_c"] or 0),
                "l3_calls": int(p_row["l3_c"] or 0),
                "l1_tokens": int(p_row["l1_t"] or 0),
                "l2_tokens": int(p_row["l2_t"] or 0),
                "l3_tokens": int(p_row["l3_t"] or 0),
                "total_tokens": int(p_row["total_t"] or 0)
            }
            
    except Exception as e:
        logger.error(f"Error fetching user stats breakdown: {e}")
    finally:
        await conn.close()
        
    return {
        "total_tokens": total_tokens,
        "month_tokens": month_tokens,
        "saved_tokens": saved_tokens,
        "saved_usd": saved_usd,
        "week_writes": week_writes,
        "rag_hits": rag_hits,
        "usage_by_model": usage_by_model,
        "pipeline_stats": pipeline_stats
    }


@router.get("/audit-logs")
async def get_user_audit_logs(
    limit: int = 50,
    ctx: dict = Depends(get_user_context)
):
    """Retrieve audit logs securely filtered by the current user's team or agent identity."""
    from backend.api.db_helper import get_db_conn
    import os
    conn = await get_db_conn()
    try:
        use_sqlite = os.getenv("MEMORY_OS_USE_STANDALONE", "false").lower() == "true"
        if use_sqlite:
            # Standalone SQLite queries agent_id matching the current user context
            rows = await conn.fetch(
                "SELECT * FROM audit_log WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2",
                ctx.get("username") or ctx["team_id"], limit
            )
            if not rows:
                rows = await conn.fetch(
                    "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT $1", limit
                )
        else:
            # PostgreSQL queries by team_id
            rows = await conn.fetch(
                "SELECT * FROM audit_log WHERE team_id = $1 ORDER BY created_at DESC LIMIT $2",
                ctx["team_id"], limit
            )
        logs = []
        for r in rows:
            d = dict(r)
            # Map resource_id to target_id for V6 UI compatibility
            d["target_id"] = str(d.get("resource_id") or "")
            # Ensure created_at is converted to ISO string
            if d.get("created_at"):
                d["created_at"] = d["created_at"].isoformat()
            logs.append(d)
        return {"logs": logs}
    except Exception as e:
        logger.warning("[audit] Failed to fetch user audit logs: %s", e)
        return {"logs": []}
    finally:
        await conn.close()


