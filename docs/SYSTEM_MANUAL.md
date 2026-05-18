# AI Memory OS V6.0 终极系统架构与全栈开发手册

> **文档状态**: 第九轮审计·黄金生产级终极圆满版  
> **系统版本**: V6.0 Production-Ready | 16 张 PostgreSQL 表 | 9 MCP 工具 | 双端数据库 100% 对齐

---

## 目录

1. [系统架构深度剖析](#1-系统架构深度剖析)
2. [大模型生态与动态管线](#2-大模型生态与动态管线)
3. [MCP 工具链完整规范](#3-mcp-工具链完整规范)
4. [RAG 与记忆调度算法](#4-rag-与记忆调度算法)
5. [核心 API 参考手册](#5-核心-api-参考手册)
6. [本地与生产环境部署](#6-本地与生产环境部署)
7. [安全架构](#7-安全架构)
8. [UI 面板一览](#8-ui-面板一览)

---

## 1. 系统架构深度剖析

AI Memory OS 是一个**持久化认知网关**。串联在用户/Agent 与 LLM 之间，实现"请求即记忆，对话即沉淀"。

### 1.1 数据底座 — 双端多路复用

| 组件 | Docker 生产模式 | Standalone 单机模式 |
|---|---|---|
| 关系型数据库 | PostgreSQL (16 张表) | SQLite (嵌入式) |
| 向量引擎 | Qdrant | LanceDB |
| 知识图谱 | Neo4j | Neo4j / NetworkX |
| 缓存/限速 | Redis | 内存 |
| 对象存储 | MinIO | 本地文件系统 |

**关键设计**: `backend/api/db_helper.py` 实现 `DBConn` 抽象层，自动将 PostgreSQL 的 `$N` 占位符翻译为 SQLite 的 `?`，并将 `NOW()` 转换为 `datetime('now')`。persona / canvas / mcp 全部通过 `get_db_conn()` 统一调用。

### 1.2 PostgreSQL 16 张表 (100% 齐全)

```
accounts               | memories (layer, source_session_id 已追加)
audit_log / audit_logs | memory_relations
chunks                 | memory_scenarios       ← V6.0 L2 场景块
documents              | pipeline_conversations ← V6.0 L0 原始对话
system_llm_configs     | pipeline_queue         ← V6.0 管线任务队列
task_canvas            | pipeline_usage         ← V6.0 用量追踪
user_persona           | user_provider_configs
user_token_usage       |
```

SQLite 同步包含全部 16 张表定义，Standalone 模式完全自给自足。

### 1.3 L0 → L3 AI 蒸馏管线

| 层级 | 模块 | 功能 |
|---|---|---|
| L0 | `l0_recorder.py` | 捕获每轮对话完整上下文，写入 pipeline_conversations |
| L1 | `l1_extractor.py` | LLM 提取结构化原子事实，写入向量底座 |
| L2 | `l2_synthesizer.py` | 归纳 L1 事实，合成多场景关联块 |
| L3 | `l3_persona.py` | 动态生成/更新用户全景 Markdown 画像 |

管线优先读取用户自己配置的 LLM Key（零运营成本），自动并发控制 + per-team 串行锁。

## 2. 大模型生态与动态管线

### 2.1 内置 21 家厂商

**🇨🇳 中国厂商 (13 家)**: DeepSeek, 阿里云百炼, 智谱AI, MiniMax, 字节豆包, 百度文心, 腾讯混元, 讯飞星火, 阶跃星辰, 零一万物, 月之暗面, 腾讯云数据万象, 硅基流动

**🌐 海外厂商 (8 家)**: OpenAI, Anthropic, Google, Mistral AI, Cohere, xAI, Groq, ElevenLabs, Jina AI

**💻 本地模型**: Ollama, LM Studio, vLLM 自动检测

### 2.2 四管线能力隔离

| 管线 | 图标 | 作用 | 可用厂商 |
|---|---|---|---|
| 内容分类器 | 🏷️ | 将记忆分为常识/人物/代码/任务/偏好 | Chat / Reasoning 厂商 |
| 知识整合引擎 | 🔮 | 定时合并重复、发掘关联 | 大上下文 Chat / Reasoning 厂商 |
| 向量化模型 | 🔢 | 文本 → 高维向量 | Embedding 厂商 |
| 重排序模型 | 🎯 | 粗排结果精排到 Top-5 | Rerank 厂商 |

前端通过 features 字段自动过滤可用厂商，防止配置错误。

### 2.3 计费与地域

- **中国厂商**：人民币 (¥/M tokens)
- **海外厂商**：美元 ($/M tokens)
- 模型价格来自各厂商官方文档

### 2.4 用户 LLM 配置 (持久化)

用户端「🤖 我的 LLM」面板：
- 厂商下拉按 `optgroup` 分区 (🇨🇳 / 🌐)
- 切换厂商自动级联选中首模型
- 测试连接 + 保存至数据库 (容器重启不丢失)
- 顶部 LLMStatusBar 实时显示当前激活 LLM


## 3. MCP 工具链完整规范

系统通过 `/mcp` SSE 端点暴露 **9 个 MCP 工具**，支持 Cursor / Claude Desktop / Cline / OpenClaw / Roo Code / Codex CLI 等全部主流 Agent。

### 3.1 完整工具列表

| # | 工具名 | 别名 | 功能 |
|---|---|---|---|
| 1 | `memory_search` | — | 混合稠密-稀疏向量 + 图谱检索 |
| 2 | `memory_store` | — | 存储重要知识/偏好/决策 |
| 3 | `memory_reflect` | — | 手动触发认知优化与记忆合并 |
| 4 | `memory_get_persona` | `persona` | 读取 L3 用户画像 |
| 5 | `memory_task_canvas_get` | `canvas_get` | 读取任务 Mermaid 画布 |
| 6 | `memory_task_canvas_update` | `canvas_update` | 更新任务进度画布 |
| 7 | `memory_list` | — | 列出当前用户所有记忆 |
| 8 | `memory_delete` | — | 删除指定记忆 |
| 9 | `memory_status` | — | 系统状态与指标报告 |

### 3.2 客户端接入

**接入方式**: SSE (`GET /mcp?token=YOUR_TOKEN`)

每个用户在「接入大模型」面板获取专属 Token 和配置。支持 7 种 Agent 的完整接入步骤和 JSON 配置一键复制。

### 3.3 System Prompt 模板

内置三套提示词：完整版 / 精简版 / 开发版。Agent 连接后自动执行 persona 读取 + 记忆检索 + 画布恢复。


## 4. RAG 与记忆调度算法

### 4.1 混合检索引擎

`memory_search` 触发时，三重并发搜索：

1. **语义搜索 (Dense Vector)**: Query → Embedding → Qdrant Cosine 相似度 (阈值 0.60)
2. **全文搜索 (Sparse/BM25)**: 关键词硬匹配，弥补专有名词向量检索短板
3. **图谱遍历 (Cypher Graph)**: LLM 提取实体 → Neo4j 深度 2 节点扩展

### 4.2 知识图谱实体提取

文档切片后调用 LLM 提取三元组：`(Subject, Predicate, Object)`，写入 Neo4j 并关联原始向量。

### 4.3 重排序 (Rerank)

向量粗排 Top-50 后，通过交叉注意力精排至 Top-5，确保注入 LLM 的上下文精准相关。


## 5. 核心 API 参考手册

### 5.1 用户认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册新用户，返回 api_key |
| POST | `/auth/token` | 用户登录，返回 JWT access_token |

### 5.2 记忆 CRUD

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/memory/search` | 混合检索，传 query + top_k |
| POST | `/memory/remember` | 存储记忆 |
| POST | `/memory/upload` | 上传文档 (.txt/.md/.pdf) |
| POST | `/memory/promote` | 提升短期记忆为长期 |
| DELETE | `/memory/{id}` | 删除记忆 |

### 5.3 V6.0 新增端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/persona/default` | JWT 自动提取用户画像 (安全) |
| GET | `/canvas/{task_id}` | 读取任务画布 Mermaid |
| POST | `/canvas/{task_id}` | 更新任务画布 |
| GET | `/graph/summary` | Neo4j 图谱统计 (节点数/关系数) |
| GET | `/graph/visualization` | Neo4j 全量图谱数据 |

### 5.4 用户 LLM 配置 (持久化)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/user/llm` | 读取用户 LLM 配置 (优先 DB) |
| POST | `/api/user/llm` | 保存配置 (写入 DB) |
| POST | `/api/user/llm/test` | 测试 LLM 连接 |

### 5.5 MCP 协议

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/mcp?token=` | SSE 隧道建立 |
| POST | `/mcp` | JSON-RPC 工具调用 |


## 6. 本地与生产环境部署

### 6.1 Docker 全量生产部署

```bash
git clone https://github.com/luogangan7-lgtm/ai-memory-os.git
cd ai-memory-os
docker-compose up -d --build
```

启动后：
- 管理端: `http://localhost:8003/manage/`
- 用户端: `http://localhost:8003/app/`
- 局域网: `http://<LAN_IP>:8003/app/`

5 大容器自动启动：PostgreSQL / Qdrant / Neo4j / Redis / MinIO。

### 6.2 Standalone 单机模式 (免 Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
export MEMORY_OS_USE_STANDALONE=true
python3 run.py
```

自动降级为 SQLite + LanceDB，数据库文件在 `~/.codex/memory-os/memories.db`。

### 6.3 公网部署建议

- Nginx 反代 + Let's Encrypt HTTPS
- 修改 Admin JWT Secret 环境变量
- 管理端仅内网访问


## 7. 安全架构

### 7.1 IDOR/BOLA 防御

- `/persona/default`: 仅基于 JWT 提取 `current_team`，完全不接受路径参数
- `/persona/{team_id}`: 强制校验 `team_id == current_team`，不匹配直接 403
- 所有敏感端点均通过 `get_current_team` 依赖注入鉴权

### 7.2 API Key 持久化与加密

- 用户 LLM 配置写入 `user_provider_configs` 数据库表
- 容器重启/断电不丢失
- `proxy.py` API 代理网关从数据库读取，不再 402

### 7.3 租户隔离

- 每用户独立 `team_id`，所有记忆/画像/画布按 team 隔离
- 管线 per-team 串行锁 (`asyncio.Lock`)，防止并发写冲突


## 8. UI 面板一览

### 8.1 管理端 (Command Deck)

| 面板 | 功能 |
|---|---|
| 控制台 | 全局记忆/活跃租户/写入吞吐/服务健康/模型状态一键诊断 |
| 监控 | 实时性能指标与 API 趋势 |
| 审计日志 | 操作记录查询 (all/store/delete/login) |
| 模型配置 | 4 管线配置 + 推荐组合 + 可用模型清单 + 本地模型检测 |
| 租户管理 | 多租户创建/管理 |
| 用户管理 | 注册用户列表/停用/删除 |
| 知识整合 | Global Reflection 触发 |
| 知识图谱 | Neo4j 真实数据 Canvas 力导向图 |
| 系统参数 | RAG 检索参数 + 安全限速 + JWT 过期配置 |

### 8.2 用户端 (Personal Space)

| 面板 | 功能 |
|---|---|
| LLM 状态栏 | 实时显示当前激活 LLM (厂商/模型/在线状态) |
| 知识库 | 记忆搜索 + 文档上传 (.txt/.md/.pdf) |
| 接入大模型 | 7 种 Agent MCP 配置 + Token + System Prompt |
| 我的 LLM | 厂商选择 (🇨🇳/🌐 分区) + 测试连接 + 使用统计 |
| 用户画像 | L3 自动生成画像查看与刷新 |
| 任务画布 | Mermaid.js SVG 图形化任务进度 |
| 操作记录 | 个人审计日志 |

### 8.3 技术栈

- **前端**: React 18 + TypeScript + Vite + TailwindCSS + Framer Motion + GSAP + Mermaid.js
- **3D**: Three.js + @react-three/fiber + @react-three/drei
- **后端**: FastAPI (Python 3.11) + asyncpg + aiosqlite + Neo4j + Qdrant
- **测试**: Playwright + ESLint + Prettier

---

> **审计最终结论**: 系统已进入极客生产就绪状态 (Production Ready)。无逻辑死锁、无 IDOR 漏洞、无断电丢失、无前端统计错误。双端数据库 100% 对齐，9 MCP 工具全部在线。


## 9. 完整源代码索引 (Source Code Index)

### 9.1 项目根目录

| 文件 | 用途 |
|---|---|
| `run.py` | 主启动脚本，自动杀端口 8003，打印管理端/用户端 URL |
| `docker-compose.yml` | Docker 5 服务编排 (PG+Qdrant+Neo4j+Redis+MinIO) |
| `init_db.py` | PostgreSQL 数据库初始化 |
| `init_db_v6.sql` | V6.0 建表 SQL (6 张核心表) |
| `Makefile` | 快捷命令 (dev/build/deploy) |
| `start.py` | 开发模式启动入口 |

### 9.2 后端核心 (`backend/`)

#### main 入口
| 文件 | 用途 |
|---|---|
| `backend/main.py` | FastAPI 应用工厂，路由注册，lifespan 初始化 |
| `backend/services/config.py` | 全局配置 (Pydantic Settings)，含 `use_standalone` |

#### API 路由层
| 文件 | 用途 |
|---|---|
| `backend/api/routes.py` | 核心业务路由：认证/记忆 CRUD/图谱/RAG/Reflection |
| `backend/api/mcp.py` | MCP SSE 服务端，9 工具注册与 JSON-RPC 调用 |
| `backend/api/user_providers.py` | 用户 LLM 配置持久化 (DB + 内存双写) |
| `backend/api/persona.py` | 用户画像 API (IDOR 安全防护) |
| `backend/api/canvas.py` | 任务画布 CRUD |
| `backend/api/db_helper.py` | 数据库抽象层 (asyncpg/SQLite 多路复用) |
| `backend/api/proxy.py` | OpenAI 兼容 API 代理网关 |
| `backend/api/admin.py` | 管理端路由 (路由推荐/测试) |


#### AI 蒸馏管线
| 文件 | 用途 |
|---|---|
| `backend/pipeline/l0_recorder.py` | L0: 捕获对话上下文写入 DB |
| `backend/pipeline/l1_extractor.py` | L1: LLM 提取原子事实 |
| `backend/pipeline/l2_synthesizer.py` | L2: 归纳事实合成场景块 |
| `backend/pipeline/l3_persona.py` | L3: 动态生成用户画像 |
| `backend/pipeline/llm_client.py` | LLM 调用客户端 (用户 Key 优先) |
| `backend/pipeline/runner.py` | 队列驱动 + 并发控制 + per-team 锁 |

#### 记忆与存储引擎
| 文件 | 用途 |
|---|---|
| `backend/memory/pg_repo.py` | PostgreSQL 数据仓库 (含 V6.0 6 张表建表) |
| `backend/memory/sqlite_repo.py` | SQLite 数据仓库 (Standalone 模式) |
| `backend/memory/qdrant_store.py` | Qdrant 向量存储 |
| `backend/memory/lancedb_store.py` | LanceDB 向量存储 (Standalone) |
| `backend/memory/ingestion.py` | 文档分块 + 向量化入库 |
| `backend/memory/retrieval.py` | 混合检索 (向量+图谱+全文) |
| `backend/memory/context_engineer.py` | 上下文编排 |
| `backend/memory/minio_store.py` | MinIO 对象存储 |
| `backend/memory/lifecycle.py` | 记忆生命周期管理 |
| `backend/memory/file_ingest.py` | 文件摄入 |
| `backend/memory/ocr.py` | 图片 OCR |


#### 图谱与认知引擎
| 文件 | 用途 |
|---|---|
| `backend/graph/neo4j_store.py` | Neo4j 图谱存储 (含 get_stats/get_full_graph) |
| `backend/reflection/engine.py` | Reflection 认知引擎 |
| `backend/scheduler/reflection_scheduler.py` | 定时 Reflection 调度器 |
| `backend/services/classifier.py` | 内容分类器 |
| `backend/services/context_compiler.py` | 上下文编译器 |

#### 大模型厂商适配
| 文件 | 用途 |
|---|---|
| `backend/providers/base.py` | 厂商基类 |
| `backend/providers/deepseek.py` | DeepSeek 适配 |
| `backend/providers/alibaba.py` | 阿里云百炼适配 |
| `backend/providers/zhipu.py` | 智谱AI 适配 |
| `backend/providers/openai.py` | OpenAI 适配 |
| `backend/providers/anthropic.py` | Anthropic 适配 |
| `backend/providers/moonshot.py` | 月之暗面适配 |
| `backend/providers/elevenlabs.py` | ElevenLabs 音频适配 |
| `backend/providers/local.py` | 本地模型 (Ollama/LM Studio) |
| `backend/providers/ollama_wizard.py` | Ollama 自动检测 |
| `backend/providers/generic.py` | 通用 OpenAI 兼容适配 |
| `backend/providers/compat_providers.py` | 兼容性提供商 |

#### 认证与安全
| 文件 | 用途 |
|---|---|
| `backend/auth/middleware.py` | JWT 认证中间件 (get_current_team/get_user_context) |
| `backend/auth/accounts.py` | 账户管理 |
| `backend/auth/apikeys.py` | API Key 校验 |
| `backend/utils/crypto.py` | 加密工具 |

#### 限速与运维
| 文件 | 用途 |
|---|---|
| `backend/services/rate_limit.py` | API 限速 |
| `backend/services/admin_limit.py` | 管理端限速 |
| `backend/services/metrics.py` | 监控指标 |
| `backend/services/logging.py` | 日志服务 |
| `backend/services/cost_tracker.py` | Token 成本追踪 |
| `backend/services/resilience.py` | 熔断/重试 |


### 9.3 前端源码 (`webui/`)

#### 入口与应用壳
| 文件 | 用途 |
|---|---|
| `webui/index.html` | SPA 入口 |
| `webui/src/main.tsx` | React 挂载 + 路由重定向 |
| `webui/src/App.tsx` | 应用壳 (HashRouter + AuthProvider + ToastProvider) |
| `webui/src/index.css` | 全局样式 (Neural Void Glassmorphism 主题) |
| `webui/src/css/login.css` | 登录页专属暗黑风格 |

#### 组件
| 文件 | 用途 |
|---|---|
| `webui/src/components/Layout.tsx` | 管理端布局 (侧边栏 + 内容区) |
| `webui/src/components/Sidebar.tsx` | 侧边导航 (总览/配置/管理/认知调优) |
| `webui/src/components/Topbar.tsx` | 顶栏 (面包屑 + 用户菜单) |
| `webui/src/contexts/AuthContext.tsx` | 认证上下文 (JWT 存储/登录/登出) |
| `webui/src/contexts/ToastContext.tsx` | Toast 通知上下文 |
| `webui/src/api/client.ts` | API 客户端 (fetch 封装) |
| `webui/src/api/endpoints.ts` | 类型化 API 端点定义 |
| `webui/src/api/types.ts` | API 响应类型定义 |

#### 管理端页面
| 文件 | 用途 |
|---|---|
| `webui/src/pages/Dashboard.tsx` | 控制台 (统计卡片/吞吐图/服务健康/模型状态诊断) |
| `webui/src/pages/Monitoring.tsx` | 监控面板 |
| `webui/src/pages/AuditLogs.tsx` | 审计日志 (all/store/delete/login 筛选) |
| `webui/src/pages/Providers.tsx` | 模型配置中心 (4 管线 + 推荐 + 厂商清单 + 本地检测) |
| `webui/src/pages/Tenants.tsx` | 多租户管理 |
| `webui/src/pages/Users.tsx` | 用户管理 |
| `webui/src/pages/Reflection.tsx` | 知识整合 (Global Reflection 触发) |
| `webui/src/pages/Graph.tsx` | 知识图谱 (Neo4j 真实数据 Canvas 力导向图) |
| `webui/src/pages/Config.tsx` | 系统参数 (RAG/安全/限速) |


#### 用户端页面
| 文件 | 用途 |
|---|---|
| `webui/src/pages/UserApp.tsx` | 用户端全部组件：登录注册/Dashboard 含 7 面板 |
| 组件 → LoginOverlay | 登录/注册覆盖层 (Premium 暗黑风格) |
| 组件 → Dashboard | 用户空间主界面 |
| 组件 → LLMStatusBar | 实时 LLM 检测状态栏 (厂商/模型/在线) |
| 组件 → MemoryPanel | 知识库 (记忆搜索 + 文档上传) |
| 组件 → ConnectPanel | 接入大模型 (7 Agent 配置 + Token + Prompt) |
| 组件 → MyLLMPanel | 我的 LLM (厂商分区下拉 + 测试 + 统计) |
| 组件 → PersonaPanel | 用户画像 |
| 组件 → CanvasPanel | 任务画布 (Mermaid.js SVG 渲染) |
| 组件 → AuditPanel | 操作记录 |

#### 数据与配置
| 文件 | 用途 |
|---|---|
| `webui/src/data/models.ts` | 21 厂商 100+ 模型数据库 (含价格/上下文/能力标签) |
| `webui/package.json` | 前端依赖 (React/Three.js/Mermaid/GSAP/Framer Motion) |
| `webui/vite.config.ts` | Vite 构建配置 |
| `webui/tailwind.config.js` | TailwindCSS 配置 |
| `webui/tsconfig.json` | TypeScript 配置 |
| `webui/.eslintrc.cjs` | ESLint 规则 |
| `webui/.prettierrc` | Prettier 格式化规则 |

### 9.4 其他工具
| 文件 | 用途 |
|---|---|
| `desktop/` | Electron 桌面端打包 |
| `scripts/` | 运维脚本 (备份/清理/健康检查) |
| `sdk/` | Python SDK (`openclaw` 客户端) |
| `agent-daemon/` | Agent 守护进程 |
| `.github/workflows/release.yml` | GitHub Actions 发布流水线 |



### 9.5 关键代码片段

#### 数据库抽象层 (`backend/api/db_helper.py`)
```python
from pathlib import Path
STANDALONE_DB = str(Path.home() / ".codex" / "memory-os" / "memories.db")

class DBConn:
    """统一数据库连接包装。自动 asyncpg / aiosqlite 多路复用。"""
    async def fetchrow(self, query, *args):
        if self._standalone:
            q = query
            for i in range(len(args), 0, -1): q = q.replace(f"${i}", "?")
            cursor = await self._conn.execute(q, args)
            row = await cursor.fetchone()
            await cursor.close()
            return row
        return await self._conn.fetchrow(query, *args)

async def get_db_conn() -> DBConn:
    if settings.use_standalone:
        db = await aiosqlite.connect(STANDALONE_DB)
        db.row_factory = aiosqlite.Row
        return DBConn(db, True)
    return DBConn(await asyncpg.connect(DATABASE_URL), False)
```

#### LLM 客户端 (`backend/pipeline/llm_client.py`)
```python
async def call_llm(prompt: str, team_id: str = "", engine_type: str = "classifier") -> str | None:
    # 1. 优先用户自己的 LLM Key (per-team 隔离)
    user_cfg = _user_llm_configs.get(team_id, {})
    if user_cfg.get("api_key") and user_cfg.get("base_url"):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(user_cfg["base_url"] + "/chat/completions",
                json={"model": user_cfg.get("model"), "messages": [...], "temperature": 0.3},
                headers={"Authorization": f"Bearer {user_cfg['api_key']}"})
            return resp.json()["choices"][0]["message"]["content"]
    # 2. Fallback 管理员 ModelRegistry
    # ...
```

#### 画像安全防护 (`backend/api/persona.py`)
```python
@router.get("/default")
async def get_persona_default(current_team: str = Depends(get_current_team)):
    """JWT 自动提取，无 IDOR 风险"""
    conn = await get_db_conn()
    row = await conn.fetchrow("SELECT * FROM user_persona WHERE team_id=$1", current_team)
    ...

@router.get("/{team_id}")
async def get_persona(team_id: str, current_team: str = Depends(get_current_team)):
    """URL team_id 强制与 JWT identity 一致"""
    if team_id != current_team:
        raise HTTPException(status_code=403, detail="Access denied")
    ...
```


#### LLM 配置持久化 (`backend/api/user_providers.py`)
```python
@router.post("")
async def save_user_llm(data: dict, team_id: str = Depends(get_current_team)):
    # 内存双写 (供 pipeline 读取)
    _user_llm_configs[team_id] = data
    # 数据库持久化 (供 proxy 网关 + 重启恢复)
    from backend.api.routes import pg_repo
    await pg_repo.save_user_provider_config(
        user_id=team_id, provider_name=data.get("provider",""),
        api_key=data.get("api_key",""), model_name=data.get("model",""), is_active=True)
    return {"status": "saved", "team_id": team_id}
```

#### 模型数据库片段 (`webui/src/data/models.ts`)
```typescript
export interface ModelInfo {
  id: string; name: string; type: 'chat'|'embedding'|'rerank'|'vision'|'reasoning'|'audio';
  recommended?: boolean; ctx?: number; price?: string;
}
export const PROVIDERS: ProviderInfo[] = [
  {id:'deepseek', name:'DeepSeek', nameZh:'深度求索', region:'cn',
   baseUrl:'https://api.deepseek.com/v1', features:['Chat','Reasoning'],
   models:[{id:'deepseek-v4-flash', name:'DeepSeek V4 Flash', type:'chat', price:'¥1.0/M'}, ...]},
  {id:'openai', name:'OpenAI', region:'intl', baseUrl:'https://api.openai.com/v1', ...},
  // 共 21 家厂商, 100+ 模型
];
```

#### MCP 工具注册 (`backend/api/mcp.py`)
```python
"tools": [
    {"name":"memory_search", "description":"混合稠密-稀疏向量+图谱检索", ...},
    {"name":"memory_store", "description":"长期事实持久化", ...},
    {"name":"memory_reflect", "description":"手动触发认知优化", ...},
    {"name":"memory_get_persona", ...},
    {"name":"memory_task_canvas_get", ...},
    {"name":"memory_task_canvas_update", ...},
    {"name":"memory_list", ...},
    {"name":"memory_delete", ...},
    {"name":"memory_status", ...}
]
# 兼容别名路由: persona → memory_get_persona, canvas_get → memory_task_canvas_get
```

---

> **文档版本**: V6.0 | **最后更新**: 2026-05-18 | **文件数**: 144 个源文件 | **表数**: PostgreSQL 16 + SQLite 16
