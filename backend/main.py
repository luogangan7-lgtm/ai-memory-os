from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.proxy import router as proxy_router
from backend.api.admin import init_registry as init_admin, router as admin_router, public_router
from backend.api.routes import init_stores as init_biz, router as biz_router
from backend.graph.neo4j_store import GraphStore
from backend.manager.registry import ModelRegistry
from backend.memory.ingestion import IngestionPipeline
from backend.memory.pg_repo import MemoryRepo
from backend.memory.qdrant_store import QdrantStore
from backend.memory.retrieval import RetrievalPipeline
from backend.reflection.engine import ReflectionEngine
from backend.scheduler.reflection_scheduler import ReflectionScheduler
from backend.services.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Standalone mode detection and initialization
    if settings.use_standalone:
        from backend.memory.sqlite_repo import SQLiteMemoryRepo
        from backend.memory.lancedb_store import LanceDBStore
        print("🚀 Starting in STANDALONE mode (Embedded SQLite + LanceDB)")
        qs = LanceDBStore() # Replaces Qdrant
        pg = await SQLiteMemoryRepo.create() # Replaces PostgreSQL
    else:
        qs = QdrantStore(host=settings.qdrant_host, port=settings.qdrant_port)
        pg = await MemoryRepo.create(host=settings.pg_host, port=settings.pg_port, user=settings.pg_user, password=settings.pg_password, database=settings.pg_db)
    
    gs = GraphStore(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
    ip = IngestionPipeline(qs)
    rp = RetrievalPipeline(qs, gs)
    registry = ModelRegistry()
    
    # Ensure default admin account exists
    try:
        from backend.auth.accounts import register
        acc_file = Path.home() / ".codex" / "memory-os" / "accounts.json"
        if not acc_file.exists():
            register("default", "admin", "admin123", "admin")
    except: pass

    init_biz(qs, gs, ip, rp, pg, registry)
    init_admin(registry, pg)
    refl = ReflectionEngine(pg, gs, registry=registry)
    sched = ReflectionScheduler(refl, interval_minutes=30)
    await sched.start()
    app.state.scheduler = sched
    yield
    await sched.stop()
    if gs: gs.close()
    await pg.close()

app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("CORS_ORIGIN", "*")], allow_methods=["*"], allow_headers=["*"])

# Rate limiting middleware
from backend.services.rate_limit import rate_limit_middleware
from backend.services.admin_limit import AdminLocalhostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.add_middleware(AdminLocalhostMiddleware)

# API routes
from backend.api.mcp import router as mcp_router
from backend.api.user_providers import router as user_providers_router
app.include_router(biz_router)
app.include_router(proxy_router)
app.include_router(public_router)
app.include_router(user_providers_router, prefix="/api")
app.include_router(admin_router, prefix="/admin")
app.include_router(mcp_router)


# UI routes
UI_DIR = Path(__file__).parent / "ui"
APP_DIR = Path(__file__).parent / "app_ui"
WEBUI_DIST = Path(__file__).parent.parent / "webui-dist"

if UI_DIR.exists():
    app.mount("/manage", StaticFiles(directory=str(UI_DIR), html=True), name="manage_ui")

if APP_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(APP_DIR), html=True), name="app_ui")

# Mount React SPA at root (if exists)
if WEBUI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEBUI_DIST), html=True), name="spa")

# Metrics
from backend.services.metrics import metrics_response
@app.get("/metrics")
async def metrics():
    return metrics_response()
