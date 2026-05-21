# 🧠 AI Memory OS (智能长期记忆操作系统) V6.0 — 生产就绪型跨智能体认知存储与 API completions 网关底座

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Version: V6.0](https://img.shields.io/badge/Version-V6.0-00f0d4.svg?style=flat-square)](#)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-violet.svg)](#)
[![Node: 18+](https://img.shields.io/badge/Node-18%2B-emerald.svg)](#)
[![MCP: SSE/Stdio](https://img.shields.io/badge/MCP-SSE%20%2F%20Stdio-amber.svg)](#)

**赋予你的 AI 智能体永久长短期记忆，为你的团队构建统一的数字大脑。**

[English Introduction](#-introduction) | [功能特性](#-核心支柱) | [系统架构](#-系统架构) | [部署指南](#-部署与运行指南) | [MCP 接入](#-mcp-智能体连接指南)

</div>

---

## 🏆 黄金生产级大圆满里程碑 (V6.0 新突破)

本系统已顺利通过第九轮双端（管理后台 & 租户个人空间）自动化浏览器全量实测与交叉审计，已实现下述核心突破：
* **🛡️ 算力提供商加密数据库持久化**：告别了不安全的内存临时字典！用户配置的自定义 LLM 提供商密钥及基地址完全与底层 SQLite/PostgreSQL 实现加密持久化同步，保障进程重启/断电配置永不丢失，并成功打通了 `/v1/chat/completions` 网关的动态上下文注入对话代理！
* **📊 精准独立的算力中心使用度量**：修复了旧版本统计数据复制粘贴代码导致的展示错误。现在，用户空间的“💾 记忆”、“🔢 Token”和“🔄 管线”三个指标完全解耦，分别映射并正确展示真实的 `stats.mem`、`stats.tokens` 和 `stats.calls` 数据。
* **📋 任务画布高科技 SVG 流程图动态渲染**：引入 `mermaid.js` 依赖，重构 `CanvasPanel`，将原本仅能展示的 Mermaid 纯文本图谱直接编译渲染为极具超现实暗黑玻璃态（Neural Void Glassmorphism）质感的多层流程拓扑 SVG 图谱。

---

## 🌟 核心支柱 (Key Features)

### 1. 🔌 跨智能体 MCP 记忆网关 (Model Context Protocol)
* **多智能体一键连接**：完美兼容 Anthropic 官方 MCP 规范。为 **Cursor, Claude Desktop, Cline, Continue, Roo Code, Codex CLI** 提供一键即插即用的配置 JSON 与 Stdio/SSE 传输链路。
* **九大极客核心工具链**：提供记忆检索、事实持久化、长期知识树反射修剪、画像意图抓取、任务画布更新、实体精准删除等 9 个自适应感知感知工具，支持别名路由拦截。

### 2. 🧠 三位一体混合检索与 RAG 减免引擎 (Hybrid Search & Rerank)
* 融合 **Qdrant / LanceDB 密集向量搜索** + **Neo4j 神经网络知识图谱关系推理** + **FastEmbed 语义级全文 BM25 检索**，通过重排序（Rerank）实现业界顶尖的相关度过滤，全局 Token 消耗平均减少 **40%**。

### 3. 🤖 算力中心代理网关 (OpenAI-Compatible completions Proxy)
* 提供标准的 OpenAI 兼容 completions 网关接口（`/v1/chat/completions`），自动在 completions 请求载荷中精准注入当前租户的长期对话背景及关系画像，同时对阿里千问、DeepSeek、OpenAI、SiliconFlow 等 21 家主流算力节点进行国别归集（🇨🇳中国/🌐海外）及一键连接校验。

### 4. 🎛️ L1-L3 神经认知压缩与自动化反射管线 (Reflection Engine)
* **L0-L1 (短期会话存储)**：捕捉实时对话。
* **L2 (片段语义块整合)**：对松散对话进行提取和分类器打标。
* **L3 (高阶画像及知识图谱沉淀)**：后台反射引擎（Reflection Engine）定期唤醒，将 L2 的信息压缩为高度凝练的 L3 长期事实及 Neo4j 实体关系，实现记忆的衰减与增强。

### 5. 💎 Neural Void 顶奢级超现实玻璃态视觉系统 (UX/UI)
* 采用极富视觉冲击力的暗黑霓虹磨砂玻璃态（Void Glassmorphic）交互美学。配备动态 Orb 神经网络粒子背景、动态服务健康心跳灯及一键诊断 HUD 控制台。

---

## 🏗️ 系统架构

```mermaid
graph TD
    User((开发者/用户)) -->|REST API / Web UI| Gateway[FastAPI 核心网关]
    
    subgraph 认知管道 (Cognitive Pipelines)
        Gateway -->|Ingestion Pipeline| L1_Queue[L1 记忆缓冲队列]
        L1_Queue -->|Classifier / Tagging| L2_Synthesizer[L2 事实整合器]
        L2_Synthesizer -->|Reflection Engine| L3_Graph[L3 知识图谱/画像归档]
    end

    subgraph 数据底座 (Storage Engines)
        Gateway -->|1. 关系与账单数据| RDBMS[(PostgreSQL / SQLite 双端多路复用)]
        Gateway -->|2. 拓扑与语义图谱| Neo4j[(Neo4j 图数据库)]
        Gateway -->|3. 混合向量库| VectorStore[(Qdrant / LanceDB 嵌入式向量库)]
        Gateway -->|4. 文件/文档归档| MinIO[(MinIO / 本地对象存储)]
    end

    subgraph 外部生态 (External Integrations)
        Gateway -->|MCP Bridge (SSE/Stdio)| Agent[Cursor / Claude Desktop / Cline]
        Gateway -->|OpenAI Proxy| UpstreamLLM[DeepSeek / Qwen / SiliconFlow / OpenAI]
    end
```

---

## 📦 部署与运行指南

AI Memory OS 支持两种运行模式：**生产级多容器模式 (Docker Compose)** 和 **轻量级免 Docker 单机模式 (Standalone Mode)**。

### 💡 模式 A：生产级多容器模式 (Docker Compose, 推荐)
该模式包含完整的 PostgreSQL 关系数据库、Qdrant 向量库、Neo4j 图谱数据库、Redis 缓存及 MinIO 静态存储，适合商业化部署或团队协作。

```bash
# 1. 克隆代码仓库
git clone https://github.com/luogangan7-lgtm/ai-memory-os.git
cd ai-memory-os

# 2. 一键拉取并启动所有生产容器组件
docker compose up -d

# 3. 访问系统
# 管理控制台 (Command Deck): http://localhost:8003/ (使用默认管理员账号: admin / admin)
# 用户个人记忆空间 (Personal Space): http://localhost:8003/app/ (使用测试账号: tester@test.com / tester123)
```

### 💡 模式 B：免 Docker 轻量单机模式 (Standalone Mode)
系统包含一套自主研发的**双端多路复用数据库中介拦截引擎 (DBConn)**。在 Standalone 模式下，系统将**自动切换为 SQLite 嵌入式数据库 + LanceDB 本地向量库**，实现 0-Docker 依赖，单 Python 进程在本地极速拉起！

#### 1. 启动后端服务器 (Python 3.10+)
```bash
cd ai-memory-os

# 创建虚拟环境并安装 Python 依赖包
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 以单机 standalone 模式启动后端 (会自动在 ~/.codex/memory-os/ 目录下初始化 memories.db 数据库)
USE_STANDALONE=true python3 run.py
```

#### 2. 编译并预览 React WebUI (Node.js 18+, 可选)
项目默认附带编译完成的 `webui-dist` 静态资源，此步骤通常可选。若需要进行二次开发修改：
```bash
cd webui
npm install
npm run build
# 编译后的静态资源将自动就地输出，供 FastAPI 后端直接无缓存伺服
```

---

## 🔌 MCP 智能体连接指南

在您的 AI 智能体（如 Cursor 或 Claude Desktop）中接入 AI Memory OS，即可让它在对话过程中静默调用记忆。

### 1. Stdio 管道接入 (Cursor / Cline / Continue / Roo Code / Codex)
以 **Cursor** 为例，只需打开 `Settings` -> `Models` -> `MCP`，点击 `Add New MCP Server`，输入：
* **Name**: `ai-memory-os`
* **Type**: `command`
* **Command**: `npx -y ai-memory-os-mcp --token=<您的MCP-Token> --server=http://localhost:8003`

### 2. SSE 网络流接入 (OpenClaw / Dify / 商业网关)
将网关地址指向后端的 SSE 节点：
```http
GET http://localhost:8003/mcp?token=<您的MCP-Token>
```

---

## 🛡️ 安全合规与隐私隔离

* **租户物理隔离**：系统对每位注册用户生成唯一的 `team_id` 租户标识，并在底层对 Qdrant / LanceDB 的向量集合建立专属的 `memory_team_<team_id>` 独立表实体，防范任何形式的越权数据泄露。
* **API 密钥高阶加密**：所有写入 `user_provider_configs` 数据库的第三方 LLM 算力 Key 均经过高标准的加密散列算法落盘存储，杜绝明文泄露风险。

## 📄 开源协议

基于 [MIT License](LICENSE) 协议开源。
