# AI Memory OS V6.0 — 优化与提升指南
> **适用版本**: V6.0 Production | **目标读者**: Codex 开发  
> **文档用途**: 针对现有架构的完整优化方案，含可直接执行的代码片段

---

## 目录

1. [🔐 安全优化（高优先级）](#1-安全优化)
2. [🏗️ 架构可靠性](#2-架构可靠性)
3. [⚡ 性能优化](#3-性能优化)
4. [📊 可观测性](#4-可观测性)
5. [🗄️ 数据治理](#5-数据治理)
6. [🔧 工程规范](#6-工程规范)
7. [📋 优先级执行清单](#7-优先级执行清单)

---

## 1. 安全优化

### 1.1 🔴 JWT / API Key 迁移至 httpOnly Cookie

**问题**: `AuthContext.tsx` 将 `admin_token`、`mos_admin_token`、`mcp_api_key` 全部存入 `localStorage`，任何 XSS 注入脚本均可直接读取所有凭证。

**后端修改** — `backend/auth/accounts.py` 或登录路由：

```python
from fastapi import Response

@router.post("/auth/token")
async def login(response: Response, form_data: LoginForm):
    # ... 验证逻辑 ...
    access_token = create_jwt(team_id=user.team_id)
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,        # JS 无法读取
        secure=True,          # 仅 HTTPS
        samesite="strict",    # 防 CSRF
        max_age=60 * 60 * 24  # 24h
    )
    # 不在 JSON body 里返回 token，只返回必要的用户信息
    return {"team_id": user.team_id, "api_key": user.api_key}
```

**前端修改** — `webui/src/api/client.ts`：

```typescript
// 所有请求加 credentials: 'include'，浏览器自动携带 Cookie
const apiClient = async (path: string, options: RequestInit = {}) => {
  const res = await fetch(`/api${path}`, {
    ...options,
    credentials: "include",   // 关键：携带 httpOnly Cookie
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};
```

**前端修改** — `webui/src/contexts/AuthContext.tsx`：

```typescript
// 删除所有 localStorage 读写，仅保留必要的非敏感状态
const login = useCallback(async (id: string, password: string) => {
  const data = await apiLogin(id, password);
  // api_key 用于显示/复制，可短暂保留在内存 state，不写 localStorage
  setMcpKey(data.api_key || "");
  setIsAuthenticated(true);
}, []);

const logout = useCallback(() => {
  // 调用后端清除 Cookie
  fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  setMcpKey("");
  setIsAuthenticated(false);
}, []);
```

---

### 1.2 🔴 LLM API Key 加密落库

**问题**: `user_provider_configs` 表中的 `api_key` 字段明文存储，数据库泄露即全部 Key 泄露。

**新增** — `backend/utils/crypto.py`（如不存在则创建）：

```python
import os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 从环境变量读取 32 字节 Master Key（base64 编码）
_MASTER_KEY = base64.b64decode(os.environ["MEMORY_OS_MASTER_KEY"])

def encrypt_api_key(plaintext: str) -> str:
    """加密 API Key，返回 base64(nonce + ciphertext)"""
    aesgcm = AESGCM(_MASTER_KEY)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_api_key(encoded: str) -> str:
    """解密 API Key"""
    data = base64.b64decode(encoded)
    nonce, ct = data[:12], data[12:]
    aesgcm = AESGCM(_MASTER_KEY)
    return aesgcm.decrypt(nonce, ct, None).decode()
```

**修改** — `backend/api/user_providers.py`：

```python
from backend.utils.crypto import encrypt_api_key, decrypt_api_key

@router.post("")
async def save_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    encrypted_key = encrypt_api_key(data.get("api_key", ""))
    await pg_repo.save_user_provider_config(
        user_id=team_id,
        api_key=encrypted_key,   # 存密文
        ...
    )

@router.get("")
async def get_user_llm(team_id: str = Depends(get_current_team)):
    cfg = await pg_repo.get_user_provider_config(team_id)
    if cfg:
        cfg["api_key"] = decrypt_api_key(cfg["api_key"])  # 返回前解密
    return cfg
```

**生成 Master Key**:

```bash
# 生成随机 32 字节 key 并 base64 编码
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
# 写入环境变量或 .env 文件
export MEMORY_OS_MASTER_KEY="<上面生成的值>"
```

---

### 1.3 🟠 CSRF 防护（配套 Cookie 方案）

迁移到 Cookie 后需要 CSRF 防护。在 FastAPI 中间件层添加：

```python
# backend/auth/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware

class CSRFMiddleware(BaseHTTPMiddleware):
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    async def dispatch(self, request, call_next):
        if request.method not in self.SAFE_METHODS:
            origin = request.headers.get("origin", "")
            host = request.headers.get("host", "")
            if origin and not origin.endswith(host):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
        return await call_next(request)

# main.py
app.add_middleware(CSRFMiddleware)
```

---

## 2. 架构可靠性

### 2.1 🔴 asyncpg 连接池

**问题**: `get_db_conn()` 每次请求建立新连接，高并发下快速耗尽 PostgreSQL 默认 100 连接数上限。

**修改** — `backend/main.py`（lifespan）：

```python
import asyncpg
from contextlib import asynccontextmanager

_pg_pool: asyncpg.Pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pg_pool
    _pg_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        command_timeout=30,
        max_inactive_connection_lifetime=300,
    )
    # 启动时预热 _user_llm_configs（见 2.2）
    await warm_up_llm_configs(_pg_pool)
    yield
    await _pg_pool.close()

app = FastAPI(lifespan=lifespan)
```

**修改** — `backend/api/db_helper.py`：

```python
async def get_db_conn() -> DBConn:
    if settings.use_standalone:
        db = await aiosqlite.connect(STANDALONE_DB)
        db.row_factory = aiosqlite.Row
        return DBConn(db, True)
    # 从全局 Pool 获取连接，而非每次新建
    from backend.main import _pg_pool
    conn = await _pg_pool.acquire()
    return DBConn(conn, False, pool=_pg_pool)  # 记录所属 Pool 以便 release

class DBConn:
    def __init__(self, conn, standalone: bool, pool=None):
        self._conn = conn
        self._standalone = standalone
        self._pool = pool

    async def close(self):
        if self._standalone:
            await self._conn.close()
        elif self._pool:
            await self._pool.release(self._conn)
```

---

### 2.2 🟠 `_user_llm_configs` 启动预热

**问题**: 服务重启后内存字典为空，第一批请求会走 fallback LLM 而非用户配置。

**新增** — `backend/api/user_providers.py`：

```python
async def warm_up_llm_configs(pool: asyncpg.Pool):
    """服务启动时从 DB 全量加载用户 LLM 配置到内存"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, provider_name, api_key, model_name "
            "FROM user_provider_configs WHERE is_active = TRUE"
        )
    for row in rows:
        _user_llm_configs[row["user_id"]] = {
            "provider": row["provider_name"],
            "api_key": decrypt_api_key(row["api_key"]),
            "model": row["model_name"],
        }
    print(f"[warm-up] Loaded {len(rows)} user LLM configs into memory")
```

---

### 2.3 🟠 管线队列：死信机制 + 指数退避

**修改** — `backend/pipeline/runner.py`：

```python
MAX_RETRY = 3

async def process_queue_item(item: dict):
    try:
        await run_pipeline(item)
        await mark_finished(item["id"])
    except Exception as e:
        retry = item["retry_count"] + 1
        if retry >= MAX_RETRY:
            await mark_dead(item["id"], str(e))
            await alert_dead_letter(item)  # 发告警（日志/邮件/Slack）
        else:
            delay = min(30 * (2 ** retry), 1800)  # 指数退避，最长 30 分钟
            await reschedule(item["id"], retry, delay, str(e))

async def mark_dead(item_id: str, error: str):
    await db.execute(
        "UPDATE pipeline_queue SET status='dead', error_msg=$1, finished_at=NOW() WHERE id=$2",
        error, item_id
    )

async def reschedule(item_id: str, retry: int, delay_seconds: int, error: str):
    await db.execute(
        "UPDATE pipeline_queue SET retry_count=$1, status='pending', "
        "scheduled_at=NOW() + INTERVAL '$2 seconds', error_msg=$3 WHERE id=$4",
        retry, delay_seconds, error, item_id
    )
```

**新增管理端接口** — 查看死信并手动重试：

```python
@admin_router.get("/pipeline/dead")
async def list_dead_jobs():
    return await db.fetch("SELECT * FROM pipeline_queue WHERE status='dead' ORDER BY finished_at DESC LIMIT 100")

@admin_router.post("/pipeline/retry/{job_id}")
async def retry_dead_job(job_id: str):
    await db.execute(
        "UPDATE pipeline_queue SET status='pending', retry_count=0, scheduled_at=NOW() WHERE id=$1",
        job_id
    )
    return {"status": "requeued"}
```

---

### 2.4 🟡 `pipeline_conversations` 清理策略

**新增** — `backend/scheduler/cleanup_scheduler.py`：

```python
import asyncio
from datetime import datetime, timedelta

RETENTION_DAYS = 30  # 可配置为环境变量

async def cleanup_processed_conversations():
    """清理已处理且超过保留期的 L0 对话记录"""
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    result = await db.execute(
        "DELETE FROM pipeline_conversations "
        "WHERE processed_l1 = TRUE AND created_at < $1",
        cutoff
    )
    print(f"[cleanup] Deleted old L0 conversations before {cutoff.date()}")

# 在 lifespan 启动后台任务
async def start_cleanup_scheduler():
    while True:
        await asyncio.sleep(24 * 3600)  # 每天执行
        try:
            await cleanup_processed_conversations()
        except Exception as e:
            print(f"[cleanup] Error: {e}")
```

---

## 3. 性能优化

### 3.1 🟡 Redis 热缓存 — Persona & Memory List

**修改** — `backend/api/persona.py`：

```python
import json
import redis.asyncio as aioredis

redis_client: aioredis.Redis = None  # 在 lifespan 初始化

PERSONA_TTL = 300  # 5 分钟

@router.get("/default")
async def get_persona_default(current_team: str = Depends(get_current_team)):
    cache_key = f"persona:{current_team}"
    
    # 1. 尝试从 Redis 读取
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. Cache Miss：查 DB
    conn = await get_db_conn()
    row = await conn.fetchrow("SELECT * FROM user_persona WHERE team_id=$1", current_team)
    result = dict(row) if row else {}
    
    # 3. 写入缓存
    await redis_client.setex(cache_key, PERSONA_TTL, json.dumps(result, default=str))
    return result
```

**缓存失效** — 在 L3 画像更新时主动失效：

```python
# backend/pipeline/l3_persona.py
async def update_persona(team_id: str, ...):
    # ... 更新 DB ...
    await redis_client.delete(f"persona:{team_id}")  # 清除缓存
```

---

### 3.2 🟡 混合检索超时隔离

**问题**: Neo4j 图谱遍历慢时会阻塞整个检索响应。

**修改** — `backend/memory/retrieval.py`：

```python
import asyncio

async def hybrid_search(query: str, team_id: str, top_k: int = 5):
    # 三路并发，但 Graph 检索设置独立超时
    dense_task = asyncio.create_task(dense_vector_search(query, team_id, top_k=50))
    sparse_task = asyncio.create_task(bm25_search(query, team_id, top_k=30))
    graph_task  = asyncio.create_task(graph_search(query, team_id, depth=2))

    results = {"dense": [], "sparse": [], "graph": []}

    # Graph 单独处理，超时不影响其他路
    try:
        results["graph"] = await asyncio.wait_for(graph_task, timeout=2.0)
    except asyncio.TimeoutError:
        print(f"[retrieval] Graph search timeout for team {team_id}, skipping")
        graph_task.cancel()

    results["dense"]  = await dense_task
    results["sparse"] = await sparse_task

    # 合并 + Rerank
    candidates = merge_results(results)
    return await rerank(query, candidates, top_k=top_k)
```

---

### 3.3 🟢 动态调整粗排 Top-K

```python
# backend/memory/retrieval.py
async def get_rough_top_k(team_id: str) -> int:
    """根据语料库大小动态决定粗排数量"""
    count = await db.fetchval("SELECT COUNT(*) FROM memories WHERE team_id=$1", team_id)
    if count < 500:
        return 20
    elif count < 5000:
        return 50
    else:
        return min(count // 100, 200)
```

---

## 4. 可观测性

### 4.1 🟡 结构化日志 + Trace ID

**安装依赖**:
```bash
pip install structlog python-json-logger
```

**新增** — `backend/services/logging.py`（替换现有）：

```python
import structlog
import logging

def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )

logger = structlog.get_logger()
```

**中间件** — 注入 Trace ID：

```python
# backend/auth/middleware.py
import uuid
import structlog

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            team_id="",  # 认证后在各路由更新
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        return response
```

**使用示例**:

```python
# 在管线各层打印耗时
import time
from backend.services.logging import logger

async def run_l1_extraction(conv_id: str, team_id: str):
    t0 = time.perf_counter()
    try:
        result = await extract_facts(conv_id)
        logger.info("l1_extraction_done",
                    team_id=team_id,
                    conv_id=conv_id,
                    duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                    fact_count=len(result))
        return result
    except Exception as e:
        logger.error("l1_extraction_failed",
                     team_id=team_id,
                     conv_id=conv_id,
                     error=str(e))
        raise
```

---

### 4.2 🟢 Prometheus 指标暴露

**安装**:
```bash
pip install prometheus-fastapi-instrumentator
```

**修改** — `backend/main.py`：

```python
from prometheus_fastapi_instrumentator import Instrumentator

# 在 app 创建后
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**自定义业务指标**:

```python
from prometheus_client import Counter, Histogram, Gauge

pipeline_runs = Counter("memory_pipeline_runs_total", "Pipeline executions", ["layer", "team_id"])
search_latency = Histogram("memory_search_duration_seconds", "Search latency", ["type"])
queue_depth = Gauge("memory_pipeline_queue_depth", "Pending queue items")

# 在管线执行时
pipeline_runs.labels(layer="l1", team_id=team_id).inc()

# 在检索时
with search_latency.labels(type="hybrid").time():
    results = await hybrid_search(query, team_id)
```

**Nginx 配置** — 仅内网访问 `/metrics`：

```nginx
location /metrics {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    deny all;
    proxy_pass http://backend:8003;
}
```

---

## 5. 数据治理

### 5.1 🟠 `audit_log` / `audit_logs` 表合并

**确认现状**：

```sql
-- 查询两张表是否同时存在
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('audit_log', 'audit_logs') 
AND table_schema = 'public';
```

**迁移（如两张表都存在）**:

```sql
-- 将旧表数据合并入新表
INSERT INTO audit_logs SELECT * FROM audit_log
ON CONFLICT (id) DO NOTHING;

-- 重命名旧表为备份
ALTER TABLE audit_log RENAME TO audit_log_deprecated_backup;

-- 验证后删除
-- DROP TABLE audit_log_deprecated_backup;
```

---

### 5.2 🟡 `freshness` 字段衰减调度

**新增** — `backend/scheduler/freshness_decay.py`：

```python
import asyncio
import math

# 衰减参数：半衰期 30 天（未被访问的记忆每 30 天 freshness 减半）
HALF_LIFE_DAYS = 30
DECAY_FACTOR = math.exp(-math.log(2) / HALF_LIFE_DAYS)

async def run_freshness_decay():
    """每日对超过 7 天未访问的记忆执行 freshness 衰减"""
    result = await db.execute(
        """
        UPDATE memories
        SET freshness = GREATEST(freshness * $1, 0.01),
            updated_at = NOW()
        WHERE updated_at < NOW() - INTERVAL '7 days'
          AND freshness > 0.01
        """,
        DECAY_FACTOR
    )
    logger.info("freshness_decay_done", updated_rows=result)

async def start_freshness_scheduler():
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            await run_freshness_decay()
        except Exception as e:
            logger.error("freshness_decay_error", error=str(e))
```

---

### 5.3 🟢 Embedding 版本升级与重建流程

**管理端触发接口**:

```python
@admin_router.post("/embeddings/rebuild")
async def trigger_embedding_rebuild(
    target_version: int,
    team_id: str = None,  # None 表示全局重建
    batch_size: int = 50
):
    """将旧版本 embedding 的 memories 加入重建队列"""
    query = "SELECT id FROM memories WHERE embedding_version < $1"
    params = [target_version]
    if team_id:
        query += " AND team_id = $2"
        params.append(team_id)
    
    rows = await db.fetch(query, *params)
    job_ids = [row["id"] for row in rows]
    
    # 分批加入 pipeline_queue
    for i in range(0, len(job_ids), batch_size):
        batch = job_ids[i:i+batch_size]
        await db.execute(
            "INSERT INTO pipeline_queue (team_id, layer, input_ids, status) VALUES ($1, 'emb', $2, 'pending')",
            team_id or "global", batch
        )
    
    return {"queued_count": len(job_ids), "batch_count": math.ceil(len(job_ids) / batch_size)}
```

---

## 6. 工程规范

### 6.1 🟠 引入 Alembic 数据库迁移

**安装**:
```bash
pip install alembic
```

**初始化**:
```bash
cd backend
alembic init migrations
```

**修改** — `backend/migrations/env.py`：

```python
from backend.services.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url)
```

**工作流程**:

```bash
# 创建迁移文件
alembic revision --autogenerate -m "add_freshness_decay_index"

# 查看待执行迁移
alembic history

# 执行迁移
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

**建议的迁移文件命名**:
```
migrations/versions/
  001_init_v5_schema.py
  002_add_v6_tables.py          ← init_db_v6.sql 内容迁移至此
  003_add_embedding_version_idx.py
  004_add_freshness_decay_idx.py
```

---

### 6.2 🟡 `UserApp.tsx` 拆分与懒加载

**建议目录结构**:

```
webui/src/pages/user/
  UserApp.tsx          ← 主壳（仅路由和布局）
  LoginOverlay.tsx
  panels/
    MemoryPanel.tsx
    ConnectPanel.tsx
    MyLLMPanel.tsx
    PersonaPanel.tsx
    CanvasPanel.tsx
    AuditPanel.tsx
  components/
    LLMStatusBar.tsx
    Dashboard.tsx
```

**懒加载配置** — `webui/src/pages/user/UserApp.tsx`：

```tsx
import { lazy, Suspense } from "react";

const MemoryPanel  = lazy(() => import("./panels/MemoryPanel"));
const PersonaPanel = lazy(() => import("./panels/PersonaPanel"));
const CanvasPanel  = lazy(() => import("./panels/CanvasPanel"));

// 在渲染时
<Suspense fallback={<LoadingSpinner />}>
  {activePanel === "memory"  && <MemoryPanel />}
  {activePanel === "persona" && <PersonaPanel />}
  {activePanel === "canvas"  && <CanvasPanel />}
</Suspense>
```

---

### 6.3 🟠 生产环境进程管理（替代 run.py kill 逻辑）

**新增** — `deploy/memory-os.service`（systemd）：

```ini
[Unit]
Description=AI Memory OS Backend
After=network.target postgresql.service

[Service]
Type=simple
User=memoryos
WorkingDirectory=/opt/ai-memory-os
ExecStart=/opt/ai-memory-os/.venv/bin/python -m uvicorn backend.main:app \
    --host 0.0.0.0 --port 8003 \
    --workers 4 \
    --log-level info
Restart=always
RestartSec=5
Environment=PYTHONPATH=/opt/ai-memory-os

[Install]
WantedBy=multi-user.target
```

**使用**:
```bash
sudo cp deploy/memory-os.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable memory-os
sudo systemctl start memory-os
sudo journalctl -u memory-os -f
```

---

### 6.4 🟢 Nginx 完整生产配置

```nginx
upstream backend {
    server 127.0.0.1:8003;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # 管理端仅内网访问
    location /manage/ {
        allow 10.0.0.0/8;
        allow 192.168.0.0/16;
        deny all;
        proxy_pass http://backend;
    }

    # MCP SSE 长连接配置
    location /mcp {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;  # SSE 长连接
    }

    # 通用代理
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;
    }
}

# HTTP 强制跳转 HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

---

## 7. 优先级执行清单

### 🔴 立即执行（影响安全/稳定性）

- [ ] **1.1** 将前端 JWT/API Key 从 `localStorage` 迁移到 `httpOnly Cookie`
- [ ] **2.1** 将 `asyncpg.connect()` 改为 `create_pool()` 连接池
- [ ] **1.2** LLM API Key AES-256-GCM 加密落库

### 🟠 近期完成（1-2 周）

- [ ] **2.2** 服务启动时预热 `_user_llm_configs`
- [ ] **2.3** 管线队列：死信机制 + 指数退避重试
- [ ] **1.3** CSRF 中间件（配套 Cookie 方案）
- [ ] **5.1** 确认并合并 `audit_log` / `audit_logs` 重复表
- [ ] **6.1** 引入 Alembic，将现有 SQL 迁移历史纳入版本管理
- [ ] **6.3** 切换到 systemd 进程管理，移除 `run.py` 的 kill-port 逻辑

### 🟡 中期完成（1 个月内）

- [ ] **3.1** Redis 热缓存 persona 和 memory_list
- [ ] **3.2** 混合检索 Graph 路径独立超时隔离
- [ ] **2.4** `pipeline_conversations` 定时清理任务
- [ ] **4.1** 结构化日志 + Trace ID 中间件
- [ ] **5.2** `freshness` 字段每日衰减调度器
- [ ] **6.2** `UserApp.tsx` 拆分 + React lazy 懒加载

### 🟢 长期规划（按需推进）

- [ ] **4.2** Prometheus 指标 + Grafana 看板
- [ ] **3.3** 粗排 Top-K 动态调整
- [ ] **5.3** Embedding 版本升级重建管理端入口
- [ ] **6.4** Nginx 生产完整配置（SSE 长连接 / 内网管理端隔离）

---

## 附录：环境变量清单（新增）

| 变量名 | 用途 | 示例值 |
|---|---|---|
| `MEMORY_OS_MASTER_KEY` | API Key 加密 Master Key（base64，32字节） | `base64生成的值` |
| `MEMORY_OS_RETENTION_DAYS` | L0 对话保留天数 | `30` |
| `MEMORY_OS_FRESHNESS_HALFLIFE` | freshness 半衰期（天） | `30` |
| `MEMORY_OS_PG_POOL_MIN` | PostgreSQL 连接池最小连接数 | `5` |
| `MEMORY_OS_PG_POOL_MAX` | PostgreSQL 连接池最大连接数 | `20` |
| `MEMORY_OS_GRAPH_TIMEOUT` | Neo4j 检索超时（秒） | `2.0` |
| `MEMORY_OS_PERSONA_CACHE_TTL` | Persona Redis 缓存 TTL（秒） | `300` |

---

> **文档版本**: V1.0 | **基于系统版本**: AI Memory OS V6.0 | **生成日期**: 2026-05-18
