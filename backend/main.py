import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.proxy import router as proxy_router
from backend.api.admin import init_registry as init_admin, router as admin_router, public_router
from backend.api.routes import init_stores as init_biz, router as biz_router
from backend.auth.accounts import init_accounts, register as register_user
from backend.graph.neo4j_store import GraphStore
from backend.manager.registry import ModelRegistry
from backend.memory.ingestion import IngestionPipeline
from backend.memory.pg_repo import MemoryRepo
from backend.memory.qdrant_store import QdrantStore
from backend.memory.retrieval import RetrievalPipeline
from backend.memory.minio_store import MinIOStore
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
    await gs.setup_indexes()
    ms = MinIOStore()
    ip = IngestionPipeline(qs)
    rp = RetrievalPipeline(qs, gs)
    registry = ModelRegistry()
    
    # Initialize accounts with DB
    from backend.auth.apikeys import init_keys
    init_accounts(pg)
    init_keys(pg)

    # Ensure default admin account exists (now async)
    try:
        admin_exists = await pg.get_account("admin")
        if not admin_exists:
            await register_user("default", "admin", "admin", "admin")
            print("👤 Default admin account created.")
    except Exception as e:
        print(f"⚠️ Error creating default admin: {e}")

    init_biz(qs, gs, ip, rp, pg, registry)
    init_admin(registry, pg, qs, gs, ms)
    refl = ReflectionEngine(pg, gs, registry=registry)
    sched = ReflectionScheduler(refl, interval_minutes=30)
    await sched.start()
    app.state.scheduler = sched
    yield
    await sched.stop()
    if gs: await gs.close()
    await pg.close()

app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
# Hardened CORS: Allow localhost and the current local IP
ALLOWED_ORIGINS = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])

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

# Favicon fix
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(Path(__file__).parent / "ui" / "assets" / "favicon.ico") if (Path(__file__).parent / "ui" / "assets" / "favicon.ico").exists() else None


# UI routes
UI_DIR = Path(__file__).parent.parent / "webui-dist"
APP_DIR = Path(__file__).parent.parent / "webui-dist"
WEBUI_DIST = Path(__file__).parent.parent / "webui-dist"

@app.get("/manage/{full_path:path}")
async def serve_manage_ui(full_path: str):
    # This handles SPA routing for the Command Deck
    if full_path == "" or full_path.endswith("/"):
        response = FileResponse(UI_DIR / "index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    
    file_path = UI_DIR / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    
    # Fallback to index.html for SPA routes (e.g. /manage/login, /manage/tenants)
    response = FileResponse(UI_DIR / "index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

if APP_DIR.exists():
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_app_ui(full_path: str):
        if full_path == "" or full_path.endswith("/"):
            response = FileResponse(APP_DIR / "index.html")
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
            
        file_path = APP_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
            
        response = FileResponse(APP_DIR / "index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

# Metrics
from backend.services.metrics import metrics_response
@app.get("/metrics")
async def metrics():
    return metrics_response()

# Mount React SPA at root (if exists)
if WEBUI_DIST.exists():
    # app.mount("/", StaticFiles(directory=str(WEBUI_DIST), html=True), name="spa")
    # Custom mount to prevent index.html caching
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_root(full_path: str):
        if full_path == "" or full_path.endswith("/"):
            response = FileResponse(WEBUI_DIST / "index.html")
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
            
        file_path = WEBUI_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
            
        response = FileResponse(WEBUI_DIST / "index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
