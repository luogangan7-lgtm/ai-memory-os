# Changelog

## V6.0 (2026-05-16)

### 🚀 Major Features
- **MCP Bridge**: 5 tools for agent memory integration (search/store/list/delete/status)
- **Neural Void WebUI**: React + TypeScript + Vite, 26 files, 1475 lines
- **Model Database**: 21 providers, 100+ models with official API IDs and pricing
- **7 Agent Configs**: Cursor, Claude, OpenClaw, Cline, Continue, Roo, Codex

### 🎨 UI
- Deep Space design system with 3D R3F particle background
- Model configuration center with auto-recommendations
- Knowledge graph visualization
- Chinese localization for all UI text
- Responsive design (Desktop/Tablet/Mobile)

### 🔧 Backend
- Standalone mode: SQLite + LanceDB (no Docker required)
- Full Docker support: PostgreSQL + Qdrant + Neo4j + Redis + MinIO
- MCP SSE server at /mcp
- Memory API: search, store, recent, delete, stats
- CORS support for LAN/Internet access

### ✅ Quality
- TypeScript: zero errors
- ESLint: zero warnings  
- E2E: 12/12 passing
- Vite Build: 2.6s

### 📦 Installation
```bash
git clone https://github.com/luogangan7-lgtm/ai-memory-os.git
cd ai-memory-os && python3 run.py
```
