#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "========================================"
echo " AI Memory OS - Production Deploy"
echo "========================================"

# 1. System check
echo "[1/7] Checking system..."
command -v docker >/dev/null || { echo "Install Docker first"; exit 1; }
echo "  Docker: OK"

# 2. Prompt for config
echo "[2/7] Configuration..."
read -p "  Domain (e.g. memory.example.com): " DOMAIN
read -sp "  PostgreSQL password: " PG_PW && echo
read -sp "  Grafana admin password: " GF_PW && echo
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)

cat > "$DIR/config/.env" << EOF
POSTGRES_PASSWORD=$PG_PW
NEO4J_PASSWORD=$PG_PW
MINIO_ROOT_PASSWORD=$PG_PW
JWT_SECRET=$JWT_SECRET
GRAFANA_PASSWORD=$GF_PW
MEMORY_OS_BM25=1
MEMORY_OS_CORS_ORIGINS=https://$DOMAIN
EOF
echo "  Config saved"

# 3. Start all services
echo "[3/7] Starting services (Docker + API)..."
cd "$DIR"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
echo "  Services started"

# 4. Wait for healthy
echo "[4/7] Waiting for services to be healthy..."
for i in $(seq 1 30); do
  curl -s http://localhost:8000/ > /dev/null 2>&1 && break
  sleep 2
done
echo "  API is ready"

# 5. HTTPS
echo "[5/7] Setting up HTTPS..."
if command -v certbot >/dev/null 2>&1; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || echo "  Certbot failed, run manually"
else
  echo "  Install certbot: sudo apt install certbot python3-certbot-nginx"
fi

# 6. Systemd + cron
echo "[6/7] Installing system service..."
sudo cp "$DIR/config/memory-os.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable memory-os
sudo systemctl start memory-os
(crontab -l 2>/dev/null; echo "0 3 * * * $DIR/config/backup-cron") | crontab -
echo "  Service + backup cron installed"

# 7. Done
echo "[7/7] Complete!"
echo "  Admin UI:  https://$DOMAIN/admin/ui/"
echo "  Grafana:   https://$DOMAIN:3000/"
echo "  Metrics:   https://$DOMAIN/metrics"
echo "  API:       https://$DOMAIN"

# Auto-detect IP
SERVER_IP=$(python3 -c "
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.connect(('8.8.8.8',80))
print(s.getsockname()[0])
s.close()
" 2>/dev/null || echo "localhost")

echo ""
echo "========================================"
echo "  Remote team access:"
echo "  http://$SERVER_IP:8000/app/"
echo "  https://$DOMAIN/app/ (after DNS)"
echo ""
echo "  Share this URL with your team!"
echo "========================================"
