# AI Memory OS - API Routes
# Blueprint Section 8

from __future__ import annotations

import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import UploadFile, File, Form

from fastapi import APIRouter, Depends, HTTPException

from datetime import datetime, timezone
from fastapi import UploadFile, File, Form

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


@router.get("/")
async def root():
    return {"status": "ok", "version": settings.version}


@router.post("/auth/token")
async def login(team_id: str = "default"):
    token = create_access_token(team_id)
    return {"access_token": token, "team_id": team_id}




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
        await ingestion.ingest(
            content=req.content, memory_id=memory_id,
            team_id=team_id, workspace_id=req.workspace_id or agent_id,
            embedding_fn=registry.embed_single, category=auto_cat, 
            source_type=req.source_type or "agent",
        )

    return {"id": memory_id, "status": "stored"}

@router.get("/memory/recent")
async def list_recent_memories(
    team_id: str = Depends(get_current_team),
    limit: int = 20,
    filter: str = "all"
):
    """List recent memories with optional filtering."""
    if not pg_repo: raise HTTPException(503)
    rows = await pg_repo.list_recent(team_id, limit, filter)
    return rows


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
    
    # 2. Check Permissions: Team ID must match, and (Agent ID must match OR role is admin)
    if memory["team_id"] != ctx["team_id"]:
        raise HTTPException(403, "Access denied")
        
    if memory["agent_id"] != ctx["agent_id"] and ctx["role"] != "admin":
        raise HTTPException(403, "Only the owner or admin can delete this knowledge")
        
    # 3. Perform deletion
    ok = await pg_repo.delete(memory_id, ctx["team_id"])
    if qdrant_store and ok:
        await qdrant_store.delete(memory_id)
    return {"deleted": ok}


@router.get("/stats")
async def get_user_stats(team_id: str = Depends(get_current_team)):
    """Get stats for the current team's dashboard."""
    if not pg_repo: raise HTTPException(503)
    total = await pg_repo.count_by_team(team_id)
    agent_total = await pg_repo.count_by_team(team_id, source_type="agent")
    tokens_saved = total * 500 # Rough estimate
    return {
        "total": total,
        "agent": agent_total,
        "tokens_saved": tokens_saved
    }

@router.post("/memory/store", response_model=MemoryResponse)
async def store_memory(
    req: MemoryStoreRequest,
    team_id: str = Depends(get_current_team),
    agent_id: str = Depends(get_agent_id),
):
    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

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
        await ingestion.ingest(
            content=req.content,
            memory_id=memory_id,
            team_id=team_id,
            workspace_id=req.workspace_id,
            embedding_fn=registry.embed_single,
            title=req.title,
            category=req.category,
            memory_type=req.memory_type,
            agent_id=req.agent_id,
            )

    # Create graph node and relations
    if graph_store:
        try:
            graph_store.create_memory_node(
                memory_id=memory_id, title=req.title,
                category=req.category, memory_type=req.memory_type,
            )
            for rel in req.relations:
                graph_store.create_relation(
                    source_id=memory_id, target_id=rel.target_id,
                    relation_type=rel.relation_type, weight=rel.weight,
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Graph store failed for {memory_id}: {e}"
            )
    if pg_repo: await pg_repo.audit(memory_id, final_agent_id, "store", {"title": req.title})
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

    if not req.query:
        # If query is empty, just return the most recent memories from Postgres
        if pg_repo:
            async with pg_repo.pool.acquire() as conn:
                if agent_id and agent_id != "default":
                    rows = await conn.fetch("SELECT * FROM memories WHERE team_id=$1 AND (agent_id='' OR agent_id=$2) ORDER BY created_at DESC LIMIT $3", team_id, agent_id, req.top_k)
                else:
                    rows = await conn.fetch("SELECT * FROM memories WHERE team_id=$1 ORDER BY created_at DESC LIMIT $2", team_id, req.top_k)
                
                return [
                    {"id": r["id"], "score": 1.0, "memory": dict(r), "text": r["content"]}
                    for r in rows
                ]
        return []

    # Phase 1: Team knowledge search
    results = await retrieval.search(
        query=req.query, embedding_fn=registry.embed_single,
        team_id=team_id, workspace_id=req.workspace_id,
        top_k=req.top_k, use_rerank=req.use_rerank,
        rerank_fn=registry.rerank if req.use_rerank and registry else None,
        use_graph=req.use_graph, min_confidence=req.min_confidence,
    )

    # Phase 2: Personal memory search (if agent_id is set)
    if agent_id and agent_id != "default":
        personal = await retrieval.search(
            query=req.query, embedding_fn=registry.embed_single,
            team_id=team_id, workspace_id=agent_id,
            top_k=min(req.top_k, 5), use_rerank=req.use_rerank,
            rerank_fn=registry.rerank if req.use_rerank and registry else None,
            min_confidence=req.min_confidence,
        )
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
        results = [r for r in results if not r["payload"].get("agent_id") or r["payload"].get("agent_id") == agent_id]
    # Fetch PG metadata (always)
    pg_rows: dict = {}
    if pg_repo and memory_ids:
        rows = await pg_repo.get_by_ids(memory_ids)
        pg_rows = {row["id"]: dict(row) for row in rows}

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
                content=pg.get("content", r["payload"].get("text", "")),
                memory_type=pg.get("memory_type", r["payload"].get("memory_type", "general")),
                importance=float(pg.get("importance", r["payload"].get("importance", 0.5))),
                confidence=float(pg.get("confidence", r["payload"].get("confidence", 0.5))),
                embedding_model=pg.get("embedding_model", "text-embedding-v3"),
                agent_id=pg.get("agent_id", r["payload"].get("agent_id", "")),
                lifecycle_stage=pg.get("lifecycle_stage", "recent"),
                source_type=pg.get("source_type", "human"),
                tags=pg.get("tags", r["payload"].get("tags", [])),
                created_at=str(pg.get("created_at", "2026-05-01T00:00:00Z")),
                updated_at=str(pg.get("updated_at", "2026-05-01T00:00:00Z")),
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
    engine = ReflectionEngine(pg_repo, graph_store)
    gaps = await engine._detect_gaps(team_id)
    return {"gaps": gaps, "note": "Topics with <2 sources or low confidence need review"}

@router.post("/memory/reflect")
async def run_reflection(
    team_id: str = Depends(get_current_team),
):
    """Run a full reflection cycle: auto-promote, decay freshness, detect duplicates."""
    if not pg_repo:
        raise HTTPException(status_code=503, detail="Database not ready")
    engine = ReflectionEngine(pg_repo, graph_store)
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

@router.post("/memory/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("general"),
    source_type: str = Form("agent"),
    importance: float = Form(0.5),
    team_id: str = Depends(get_current_team),
):

    """Upload a PDF/Markdown/Text file and ingest its content."""
    if not ingestion or not pg_repo:
        raise HTTPException(status_code=503, detail="Not ready")

    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    import urllib.parse
    title = urllib.parse.unquote(file.filename) if file.filename else "Uploaded file"

    # Read file content
    file_bytes = await file.read()

    # Save to MinIO
    object_name = f"{team_id}/{memory_id}{Path(file.filename).suffix if file.filename else '.txt'}"
    try:
        minio = MinIOStore()
        minio.upload(object_name, file_bytes, file.content_type or "application/octet-stream")
        source_uri = f"minio://{object_name}"
    except Exception:
        source_uri = file.filename

    # Extract text (write to temp for PDF parsing)
    import tempfile
    suffix = Path(file.filename).suffix if file.filename else ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        text = extract_text(tmp_path)
    except Exception:
        text = "(extraction failed)"
    finally:
        os.unlink(tmp_path)

    title = urllib.parse.unquote(file.filename) if file.filename else "Uploaded file"

    # Auto-classify based on extracted text
    from backend.services.classifier import classify_memory
    clf = await classify_memory(text, title, registry)

    # Store metadata
    await pg_repo.insert(
        id=memory_id, team_id=team_id, workspace_id="default",
        category=clf["category"], subcategory=clf["subcategory"], topic=clf["topic"],
        title=title, content=text,
        embedding_model="text-embedding-v3",
        importance=importance, confidence=0.9,
        source_type=source_type, source_uri=source_uri or file.filename,
        tags=[], metadata={"filename": file.filename, "size": len(text)},
    )

    # Ingest into Qdrant
    await ingestion.ingest(
        content=text, memory_id=memory_id,
        team_id=team_id, workspace_id="default",
        embedding_fn=registry.embed_single,
        title=title, category=clf["category"], source_type=source_type,
    )

    return {"id": memory_id, "title": title, "category": clf["category"], "chars": len(text)}


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

@router.post("/memory/graph", response_model=GraphResponse)
async def query_graph(
    req: GraphQueryRequest,
    team_id: str = Depends(get_current_team),
):
    if not graph_store:
        raise HTTPException(status_code=503, detail="Graph store not ready")
    try:
        data = graph_store.get_relations(
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
