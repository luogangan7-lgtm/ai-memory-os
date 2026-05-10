# AI Memory OS Desktop App

## Build
npm install
npm start          # dev mode
npm run build:mac  # macOS .dmg
npm run build:win  # Windows .exe
npm run build:linux  # Linux .AppImage

## What it does
- Auto-checks Docker
- Starts all services (Qdrant, PG, Neo4j, MinIO, Redis)
- Launches API server
- Opens admin panel as desktop window
- System tray for quick access

## Requirements
- Docker Desktop (docker.com)
- Python 3.10+ (python.org)
- Node.js 18+ (nodejs.org)
