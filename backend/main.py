import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
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

    # V6.0 Pipeline init (L0→L3 memory processing)
    from backend.pipeline.runner import init as init_pipeline
    init_pipeline(pg)
    from backend.pipeline.runner import start_worker
    from backend.scheduler.cleanup_scheduler import start_cleanup_scheduler
    start_worker()
    asyncio.create_task(start_cleanup_scheduler())
    from backend.scheduler.freshness_decay import start_decay_scheduler
    asyncio.create_task(start_decay_scheduler())
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
# Hardened CORS: Allow localhost and the current local IP
ALLOWED_ORIGINS = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])

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
app.include_router(persona_router)
app.include_router(canvas_router)

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
    return {"status": "ok", "service": settings.app_name, "version": settings.version}


# Root portal — split traffic between /manage (admin Command Deck) and /app (user
# Workspace). Self-contained HTML so it loads without the SPA bundle, and so first-time
# operators landing on the bare domain don't accidentally enter the admin view.
PORTAL_HTML = """<!doctype html>
<html lang="zh-CN" data-theme="system">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Memory OS</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #FAFAFA;
      --bg-elev: #FFFFFF;
      --fg: #0A0A0A;
      --fg-muted: #6B6B6B;
      --border: #E5E5E5;
      --border-strong: #D4D4D4;
      --accent: #6E56CF;
      --accent-glow: rgba(110, 86, 207, 0.18);
      --radius-sm: 6px;
      --radius-md: 8px;
      --radius-lg: 12px;
      --ease: cubic-bezier(0.16, 1, 0.3, 1);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #0A0A0A;
        --bg-elev: #111111;
        --fg: #E5E5E5;
        --fg-muted: #888888;
        --border: #1F1F1F;
        --border-strong: #2A2A2A;
        --accent: #8E78E5;
        --accent-glow: rgba(142, 120, 229, 0.22);
      }
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg);
      color: var(--fg);
      font-feature-settings: 'cv11', 'ss01';
      -webkit-font-smoothing: antialiased;
      letter-spacing: -0.01em;
      perspective: 1200px;
    }
    .page {
      min-height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 24px;
      gap: 48px;
    }
    .brand { text-align: center; }
    .brand .logo {
      display: inline-flex; align-items: center; gap: 10px;
      font-family: 'Geist Mono', ui-monospace, monospace;
      font-size: 13px; letter-spacing: 0.06em;
      color: var(--fg-muted); text-transform: uppercase;
    }
    .brand .logo::before {
      content: ''; width: 8px; height: 8px; border-radius: 999px;
      background: var(--accent); box-shadow: 0 0 12px var(--accent-glow);
    }
    .brand h1 {
      margin-top: 14px; font-size: 32px; font-weight: 600;
      letter-spacing: -0.02em;
    }
    .brand p {
      margin-top: 8px; font-size: 14px; color: var(--fg-muted);
    }
    .cards {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 360px));
      gap: 20px; width: 100%; max-width: 760px;
    }
    .card {
      position: relative;
      display: block; text-decoration: none; color: inherit;
      background: var(--bg-elev);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 28px;
      transition: transform 0.35s var(--ease), border-color 0.2s, box-shadow 0.3s;
      transform-style: preserve-3d;
      will-change: transform;
    }
    .card:hover {
      transform: translateY(-4px) rotateX(2deg) rotateY(-2deg);
      border-color: var(--border-strong);
      box-shadow: 0 14px 32px -16px var(--accent-glow), 0 0 0 1px var(--accent-glow);
    }
    .card::after {
      content: ''; position: absolute; inset: 0;
      border-radius: var(--radius-lg);
      background: linear-gradient(135deg, var(--accent-glow), transparent 50%);
      opacity: 0; transition: opacity 0.3s var(--ease); pointer-events: none;
    }
    .card:hover::after { opacity: 1; }
    .card .icon {
      width: 44px; height: 44px;
      display: inline-flex; align-items: center; justify-content: center;
      border-radius: var(--radius-md);
      background: var(--accent-glow);
      color: var(--accent);
      margin-bottom: 18px;
    }
    .card h2 {
      font-size: 18px; font-weight: 600; margin-bottom: 6px;
      letter-spacing: -0.015em;
    }
    .card p {
      font-size: 13.5px; line-height: 1.55; color: var(--fg-muted);
      margin-bottom: 18px;
    }
    .card .cta {
      display: inline-flex; align-items: center; gap: 4px;
      font-family: 'Geist Mono', monospace;
      font-size: 12px; letter-spacing: 0.04em;
      color: var(--accent); text-transform: uppercase;
    }
    .card .cta::after { content: '→'; transition: transform 0.2s var(--ease); }
    .card:hover .cta::after { transform: translateX(3px); }
    .meta {
      font-family: 'Geist Mono', monospace;
      font-size: 11px; color: var(--fg-muted); letter-spacing: 0.04em;
      text-align: center; opacity: 0.7;
    }
    .meta a { color: var(--fg-muted); text-decoration: none; border-bottom: 1px dotted var(--border-strong); }
    @media (max-width: 640px) {
      .cards { grid-template-columns: 1fr; }
      .brand h1 { font-size: 26px; }
    }
  </style>
</head>
<body>
  <main class="page">
    <header class="brand">
      <div class="logo">AI Memory OS · v6</div>
      <h1>Where do you want to go?</h1>
      <p>同一服务,两套界面。按你的角色选择入口。</p>
    </header>

    <section class="cards">
      <a class="card" href="/manage/" data-card="admin">
        <div class="icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1.5"/>
            <rect x="14" y="3" width="7" height="7" rx="1.5"/>
            <rect x="3" y="14" width="7" height="7" rx="1.5"/>
            <rect x="14" y="14" width="7" height="7" rx="1.5"/>
          </svg>
        </div>
        <h2>Command Deck</h2>
        <p>管理后台。租户、用户、提供商、反射引擎、监控、知识图谱、审计日志。</p>
        <span class="cta">Enter admin</span>
      </a>

      <a class="card" href="/app/" data-card="user">
        <div class="icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a3 3 0 0 1 3 3v6a3 3 0 1 1-6 0V5a3 3 0 0 1 3-3z"/>
            <path d="M5 11a7 7 0 0 0 14 0"/>
            <path d="M12 18v3"/>
            <path d="M8 21h8"/>
          </svg>
        </div>
        <h2>Memory Workspace</h2>
        <p>个人空间。你的长期记忆、对话历史、人物画像、MCP 接入。</p>
        <span class="cta">Enter workspace</span>
      </a>
    </section>

    <footer class="meta">
      backend healthy · <a href="/health" target="_blank">/health</a> · <a href="https://github.com/luogangan7-lgtm/ai-memory-os" target="_blank">source</a>
    </footer>
  </main>
  <script>
    // 3D tilt: subtle perspective parallax based on cursor
    document.querySelectorAll('.card').forEach(card => {
      card.addEventListener('pointermove', (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = `translateY(-4px) rotateX(${y * -6}deg) rotateY(${x * 6}deg)`;
      });
      card.addEventListener('pointerleave', () => {
        card.style.transform = '';
      });
    });
  </script>
</body>
</html>
"""


@app.get("/", include_in_schema=False)
async def portal():
    return HTMLResponse(PORTAL_HTML)


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
