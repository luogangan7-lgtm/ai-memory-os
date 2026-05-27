# Cortex — Long-term Memory OS for AI Agents

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Version: V7.1](https://img.shields.io/badge/Version-V7.1-00f0d4.svg?style=flat-square)](#)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-violet.svg)](#)
[![Node: 18+](https://img.shields.io/badge/Node-18%2B-emerald.svg)](#)
[![MCP: 18 Tools](https://img.shields.io/badge/MCP-18%20Tools-amber.svg)](#)
[![Providers: 14+](https://img.shields.io/badge/LLM%20Providers-14%2B-ff6b6b.svg)](#)
[![Docker](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ed.svg)](#)

**Give your AI agents permanent long-term memory. Build a unified knowledge brain for your team.**

[中文说明](README_CN.md) | [Features](#-core-pillars) | [Architecture](#-architecture) | [Quick Start](#-quick-start) | [MCP Integration](#-mcp-integration)

</div>

---

<div align="center">

![Cortex V7.1 Dashboard](docs/images/cortex_v71_dashboard.png)

</div>

---

## 🚀 What's New in V7.1

| Feature | Description |
|---------|-------------|
| **K2 Three-Phase Knowledge Pipeline** | Real-time topic classification → auto-split oversized topics → semantic merging |
| **LLM Quality Gate** | User's own LLM evaluates content quality (0–1 score) before internalization |
| **Reasoning Strip (`<think>`)** | Central cleaner for MiniMax-M2.7 / DeepSeek-R1 / Qwen reasoning prefix pollution |
| **429 Exponential Backoff** | Auto-retry on rate limit: 1s → 2s → 4s (max 3 attempts), production-grade stability |
| **L4 Skill Evolution** | Merge similar skills via `/api/skills/evolve`; PRM feedback loop updates effectiveness |
| **Code Graph REST View** | `/api/code-entities` replaces MCP text search — Files / Entities / Languages tri-view |
| **Chinese Document Chunking Fix** | CJK-aware character counting (was word-count, caused 1-chunk bug for Chinese docs) |
| **Provider API Key Fallback** | Engine config missing key → auto-fallback to stored provider key |
| **Inline Health Monitor** | `index.html` script → page title shows `✅ ALL OK` / `⚠️ N DOWN` / `❌ API DOWN` |

---

## 🌟 Core Pillars

### 1. 🔌 MCP Memory Gateway (18 Tools)
Full compatibility with Anthropic's MCP spec. One-click integration for **Cursor, Claude Desktop, Cline, Roo Code, Codex CLI, Continue**.

| Category | Tools |
|----------|-------|
| Memory CRUD | `memory_search`, `memory_store`, `memory_list`, `memory_delete`, `memory_reflect`, `memory_get_persona`, `memory_task_canvas_get`, `memory_task_canvas_update`, `memory_status` |
| Code Graph | `code_index`, `code_search`, `code_relations`, `code_impact`, `code_memory_link` |
| Skills & Feedback | `memory_feedback`, `memory_skill_list` |
| Documents & Public | `doc_search`, `public_browse` |

### 2. 🧠 5-Layer Cognitive Pipeline (L0 → L4)
```
L0 Record  → Raw memory storage + vector embedding
L1 Extract → Facts / decisions / preferences via LLM
L2 Synth   → Aggregate similar facts into scenes
L3 Persona → Generate user persona + knowledge graph
L4 Skills  → Crystallize recurring patterns into reusable skills
K2 Topics  → Classify, split, and merge public knowledge pool
```

### 3. 🤖 14+ LLM Providers (Multi-vendor)
Zhipu · MiniMax · DeepSeek · Alibaba Bailian · OpenAI · Anthropic · Moonshot · Doubao · Baidu · Hunyuan · Spark · StepFun · Yi · SiliconFlow + Generic OpenAI-compatible

All providers share unified response cleaning — reasoning tags (`<think>`) auto-stripped.

### 4. 📄 Two-Tier Document Processing
- **T1 (System cost)**: Extract text → semantic chunking → vector embedding → immediate search
- **T2 (User LLM)**: Deep summary + entity extraction + knowledge graph linking

### 5. 💎 Neural Void UI
Dark glassmorphism with neon cyan/purple accents, dynamic particle background, 8-tab user workspace.

---

## 🏗️ Architecture

<div align="center">

![Cortex V7.1 Architecture](docs/images/cortex_v71_architecture.png)

</div>

```
Access Layer:  /app (User WebUI)  |  /manage (Admin Console)  |  /mcp (SSE Gateway)
                                      │
                              FastAPI Gateway
                    (routes.py + admin.py + mcp.py)
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
    PostgreSQL               Qdrant Vector DB               Neo4j Graph
  (memories, users,         (semantic search,           (10 relation types,
    skills, feedback)        document chunks)           knowledge topology)
          
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
        Redis                       MinIO                  14+ LLM Providers
    (rate limit, cache)         (document files)          (with <think> strip)
```

---

## 📦 Quick Start

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone
git clone https://github.com/luogangan7-lgtm/ai-memory-os.git
cd ai-memory-os

# 2. Configure (IMPORTANT: change passwords before production!)
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, NEO4J_PASSWORD, MINIO_ROOT_PASSWORD

# 3. Start all services
docker compose up -d

# 4. Verify
curl http://localhost:8003/admin/health

# Access:
# User workspace:   http://localhost:8003/app
# Admin console:    http://localhost:8003/manage  (default: admin / admin)
```

### Option B: Standalone (No Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
USE_STANDALONE=true python3 run.py
```

### Frontend Build (if modifying UI)

```bash
cd webui && npm install && npm run build
```

---

## 🔌 MCP Integration

### SSE Connection
```
GET https://your-domain.com/mcp?token=mos_your_token_here
```

### Cursor / Cline / Codex
```json
{
  "mcpServers": {
    "cortex-memory": {
      "command": "npx",
      "args": ["-y", "ai-memory-os-mcp", "--token=mos_your_token", "--server=https://your-domain.com"]
    }
  }
}
```

### System Prompt Template
After connecting, add this to your agent's system prompt:
```
You have access to a persistent memory system via MCP tools.
Use memory_search to recall past context, memory_store to save important decisions,
and memory_reflect to optimize your knowledge periodically.
```

---

## 🗄️ Database Schema

| Table | Purpose |
|-------|---------|
| `memories` | All L0–L4 memories with layer, topic, lifecycle metadata |
| `memory_skills` | L4 crystallized skills with effectiveness + source_agents |
| `skill_feedback` | PRM outcome records (success/failure/partial) |
| `code_entities` | Code graph: functions/classes/imports across 27 languages |
| `user_provider_configs` | Encrypted user LLM keys (AES-256-GCM) |
| `task_canvas` | Mermaid diagram state per user |

---

## 🛡️ Security

- **Tenant isolation**: `team_id` scopes every query — no cross-user data leakage
- **Encrypted key storage**: User LLM API keys encrypted with AES-256-GCM at rest (`MEMORY_OS_MASTER_KEY`)
- **JWT auth**: 24h access tokens, signed with `MEMORY_OS_JWT_SECRET`
- **PII filter**: Blocks internalization of API keys, emails, phone numbers, ID cards
- **Rate limiting**: Redis-backed per-user rate limits → 429 on abuse
- **No hardcoded secrets**: All credentials via environment variables

### ⚠️ Production Security Checklist

```bash
# Required before going live:
MEMORY_OS_MASTER_KEY=<base64 32-byte random>   # Encrypts provider keys at rest
MEMORY_OS_JWT_SECRET=<64-char random hex>       # Signs user sessions
POSTGRES_PASSWORD=<strong password>             # NOT the default "memoryos"
NEO4J_PASSWORD=<strong password>               # NOT the default "password"
```

---

## 📋 API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register with email verification |
| POST | `/auth/token` | Login → JWT + API key |
| POST | `/memory/remember` | Store memory (auto-classify) |
| POST | `/memory/search` | Semantic search (+ `since`/`until` time travel) |
| POST | `/memory/upload` | Upload document (T1+T2 processing) |
| POST | `/memory/reflect` | Trigger reflection engine |
| GET | `/api/code-entities` | Code entity browser |
| GET | `/api/skills` | L4 skill library |
| POST | `/api/skills/evolve` | Trigger skill evolution |
| GET | `/graph/visualization` | Knowledge graph data |
| GET | `/admin/health` | Service health check |

Full API: see [AI_Memory_OS_Cortex_完整系统文档.md](docs/) or `/docs` (Swagger UI when running).

---

## 🖥️ GCP Production Deployment

```bash
# Server: GCP Compute Engine, Ubuntu 22.04, 2 vCPU / 4 GB RAM
ssh user@YOUR_SERVER_IP
git clone https://github.com/luogangan7-lgtm/ai-memory-os.git /opt/ai-memory-os
cd /opt/ai-memory-os
cp .env.example .env && nano .env   # Set strong passwords
docker compose up -d
# Point Cloudflare DNS A record → server IP
```

Domains: [luolimo.pics](https://luolimo.pics) · [cortexmemory.cloud](https://cortexmemory.cloud)

---

## 📄 License

[MIT License](LICENSE) — Open source, free to use and deploy.

---

<div align="center">

**Cortex V7.1** | Python 3.11 + FastAPI + React + Qdrant + Neo4j + PostgreSQL

*Built for developers who want their AI agents to actually remember things.*

</div>
