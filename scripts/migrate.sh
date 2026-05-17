#!/bin/bash
# AI Memory OS — Data Migration Tool
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
EXPORT_DIR="${1:-$DIR/backup_$(date +%Y%m%d_%H%M%S)}"

echo "========================================"
echo " AI Memory OS — Migration Export"
echo "========================================"
mkdir -p "$EXPORT_DIR"

# 1. PostgreSQL dump
echo "[1/6] Exporting PostgreSQL..."
curl -s "http://localhost:8000/memory/backup" > "$EXPORT_DIR/pg_backup.json" 2>/dev/null || \
  docker exec ai-memory-os-postgres-1 pg_dump -U memoryos memory_os > "$EXPORT_DIR/pg_dump.sql"
echo "  PostgreSQL: done"

# 2. Qdrant snapshot
echo "[2/6] Creating Qdrant snapshot..."
curl -s -X POST "http://localhost:6335/collections/memory/snapshots" > "$EXPORT_DIR/qdrant_snapshot.json" 2>/dev/null
echo "  Qdrant: see Docker volume qdrant_data"

# 3. Neo4j dump
echo "[3/6] Exporting Neo4j..."
docker exec ai-memory-os-neo4j-1 neo4j-admin dump --database=neo4j --to=/data/neo4j.dump 2>/dev/null && \
  docker cp ai-memory-os-neo4j-1:/data/neo4j.dump "$EXPORT_DIR/" 2>/dev/null
echo "  Neo4j: done"

# 4. API keys + config
echo "[4/6] Copying configuration..."
[ -f "$DIR/config/providers.json" ] && cp "$DIR/config/providers.json" "$EXPORT_DIR/"
[ -f "$DIR/config/.env" ] && cp "$DIR/config/.env" "$EXPORT_DIR/"
[ -f "$DIR/settings.json" ] && cp "$DIR/settings.json" "$EXPORT_DIR/"
# API keys
KEYS_DIR="${HOME}/.codex/memory-os"
[ -f "$KEYS_DIR/api_keys.json" ] && cp "$KEYS_DIR/api_keys.json" "$EXPORT_DIR/"
echo "  Config: done"

# 5. Docker volumes (marker)
echo "[5/6] Volume info..."
docker volume ls | grep ai-memory-os > "$EXPORT_DIR/volumes.txt" 2>/dev/null
echo "  Volumes listed"

# 6. Summary
echo "[6/6] Creating restore guide..."
cat > "$EXPORT_DIR/RESTORE.md" << 'GUIDE'
# Restore Instructions

1. Copy this entire folder to the new server
2. Deploy Memory OS on the new server: `python deploy.py`
3. Stop services: `docker compose down`
4. Restore PG:
   docker cp pg_dump.sql ai-memory-os-postgres-1:/tmp/
   docker exec ai-memory-os-postgres-1 psql -U memoryos -d memory_os -f /tmp/pg_dump.sql
5. Restore Neo4j:
   docker cp neo4j.dump ai-memory-os-neo4j-1:/data/
   docker exec ai-memory-os-neo4j-1 neo4j-admin load --database=neo4j --from=/data/neo4j.dump --force
6. Restore config:
   cp providers.json config/
   cp api_keys.json ~/.codex/memory-os/
   cp settings.json ./
7. Start services: `docker compose up -d`
8. Start API: `python deploy.py --daemon`
GUIDE
echo "  Guide created"

echo ""
echo "========================================"
echo " Migration exported to:"
echo "   $EXPORT_DIR"
echo ""
echo " Copy this folder to new server and"
echo " follow RESTORE.md"
echo "========================================"
