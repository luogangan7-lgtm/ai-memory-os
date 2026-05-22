import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
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

# Global PostgreSQL connection pool
_pg_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pg_pool
    # Initialize connection pool for Docker mode
    if not settings.use_standalone:
        import asyncpg as _apg
        db_url = f"postgresql://{settings.pg_user}:{settings.pg_password}@{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
        _pg_pool = await _apg.create_pool(
            db_url, min_size=5, max_size=20,
            command_timeout=30, max_inactive_connection_lifetime=300)
        print(f"[pool] PostgreSQL connection pool created (min=5, max=20)")
        from backend.api.user_providers import warm_up_llm_configs
        await warm_up_llm_configs()
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
    ip = IngestionPipeline(qs, pg_repo=pg)
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
    registry.qs = qs  # Attach QdrantStore for account deletion cleanup

    # V6.0 Pipeline init (L0→L3 memory processing)
    from backend.pipeline.runner import init as init_pipeline
    init_pipeline(pg)
    from backend.pipeline.runner import start_worker
    from backend.scheduler.cleanup_scheduler import start_cleanup_scheduler
    start_worker()
    asyncio.create_task(start_cleanup_scheduler())
    from backend.scheduler.freshness_decay import start_decay_scheduler
    asyncio.create_task(start_decay_scheduler())
    from backend.scheduler.plan_expiry import start_plan_expiry_scheduler
    asyncio.create_task(start_plan_expiry_scheduler())
    refl = ReflectionEngine(pg, gs, registry=registry, retrieval=rp)
    sched = ReflectionScheduler(refl, interval_minutes=30)
    await sched.start()
    app.state.scheduler = sched
    yield
    await sched.stop()
    if _pg_pool:
        await _pg_pool.close()
        print("[pool] PostgreSQL connection pool closed")
    if gs: await gs.close()
    await pg.close()

app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
# Hardened CORS: Allow localhost, LAN IPs, and current host
import os as _os
_local_origins = [
    "http://localhost:8003", "http://localhost:5173",
    "http://127.0.0.1:8003", "http://127.0.0.1:5173",
    "http://192.168.50.167:8003", "http://192.168.50.167:5173",
]
ALLOWED_ORIGINS = _os.environ.get("ALLOWED_ORIGINS", "").split(",") if _os.environ.get("ALLOWED_ORIGINS") else _local_origins
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

# Rate limiting middleware
from backend.services.rate_limit import rate_limit_middleware
from backend.services.admin_limit import AdminLocalhostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.add_middleware(AdminLocalhostMiddleware)
from backend.auth.middleware import TraceMiddleware
app.add_middleware(TraceMiddleware)
# CSRF protection for state-changing requests
from starlette.middleware.base import BaseHTTPMiddleware
class CSRFMiddleware(BaseHTTPMiddleware):
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    async def dispatch(self, request, call_next):
        if request.method not in self.SAFE_METHODS:
            origin = request.headers.get("origin", "")
            if origin:
                from urllib.parse import urlparse
                host = request.headers.get("host", "")
                parsed = urlparse(origin)
                if parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1") and parsed.hostname != host.split(":")[0]:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
        return await call_next(request)
app.add_middleware(CSRFMiddleware)

# API routes
from backend.api.mcp import router as mcp_router
from backend.api.user_providers import router as user_providers_router
app.include_router(biz_router)
app.include_router(proxy_router)
app.include_router(public_router)
app.include_router(user_providers_router, prefix="/api")
app.include_router(admin_router, prefix="/admin")
app.include_router(mcp_router)
from backend.api.persona import router as persona_router
from backend.api.canvas import router as canvas_router
from backend.api.payment import router as payment_router
app.include_router(persona_router)
app.include_router(canvas_router)
app.include_router(payment_router)

# Favicon fix
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(Path(__file__).parent / "ui" / "assets" / "favicon.ico") if (Path(__file__).parent / "ui" / "assets" / "favicon.ico").exists() else None


# Liveness probe — must be declared before the SPA catch-all routes below, otherwise the
# fallback at "/{full_path:path}" returns index.html and external monitors see HTTP 200
# with HTML body, faking liveness.
@app.get("/health", include_in_schema=False)
@app.get("/api/health", include_in_schema=False)
async def health():
    """Real health check testing all core services."""
    from backend.api.admin import _pg_repo, _qdrant_store, _graph_store, _minio_store
    svc = {"postgres": False, "qdrant": False, "neo4j": False, "redis": True, "minio": False}
    if _pg_repo and _pg_repo.pool:
        try:
            async with _pg_repo.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            svc["postgres"] = True
        except: pass
    if _qdrant_store and _qdrant_store.client:
        try:
            _qdrant_store.client.get_collections()
            svc["qdrant"] = True
        except: pass
    if _graph_store and _graph_store.driver:
        try:
            await _graph_store.driver.verify_connectivity()
            svc["neo4j"] = True
        except: pass
    if _minio_store:
        try:
            if hasattr(_minio_store, 'client'):
                _minio_store.client.list_buckets()
            svc["minio"] = True
        except: pass
    all_ok = all(svc.values())
    return {"status": "ok" if all_ok else "degraded", "services": svc}


# Root → user app. The product is multi-tenant; the public-facing entry is the
# Memory Workspace (which itself shows a marketing landing + signin/signup when
# the visitor is unauthenticated). The admin Command Deck stays reachable at
# /manage/ as an explicit URL, not from the public root.
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/app/", status_code=302)


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
