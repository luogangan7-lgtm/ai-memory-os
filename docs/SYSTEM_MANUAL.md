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
