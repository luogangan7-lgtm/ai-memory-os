# AI Memory OS — Production Deployment SOP

End-to-end guide for first-time deployment on a Linux server using **Docker Compose mode** (recommended). Standalone-mode artifacts under `config/memory-os.service` are legacy and are not covered here.

> Target audience: a single operator deploying the V6 stack to one box. If you need HA, autoscaling, or k8s — adapt the principles, the steps below assume one host.

---

## 0. Prerequisites

### Server sizing (minimum)

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB SSD | 50 GB+ SSD (memories grow) |
| OS | Ubuntu 22.04 / Debian 12 / any with Docker | same |

The 6-container stack (backend + postgres + qdrant + neo4j + minio + redis) idles at ~2 GB RAM. Neo4j alone will happily eat 1–2 GB under load.

### Software

```bash
# Docker + Docker Compose v2
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # log out and back in

# Nginx + Certbot (for HTTPS reverse proxy)
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx

# Verify
docker --version
docker compose version
```

### Network

| Port | Direction | Purpose |
|---|---|---|
| 22 | inbound | SSH (consider key-only) |
| 80 | inbound | HTTP — used only for HTTPS redirect + Let's Encrypt challenge |
| 443 | inbound | HTTPS reverse proxy |
| 8003 | **NOT exposed publicly** | Backend listens on `127.0.0.1:8003` only |
| 5432 / 6333 / 6379 / 7474 / 7687 / 9000 / 9001 | bound to `127.0.0.1` | Internal datastores, never public |

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 1. Get the code

```bash
sudo mkdir -p /opt/memory-os && sudo chown "$USER" /opt/memory-os
cd /opt/memory-os
git clone https://github.com/luogangan7-lgtm/ai-memory-os.git .
```

---

## 2. First-time deploy (one command)

```bash
./scripts/deploy-prod.sh
```

The script will:

1. Verify docker + docker compose v2 are installed.
2. Prompt for `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `MINIO_ROOT_PASSWORD`, `GRAFANA_PASSWORD`, public domain.
3. Auto-generate `MEMORY_OS_MASTER_KEY` (AES-256-GCM key, base64) and `MEMORY_OS_JWT_SECRET` (hex64).
4. Write `.env` with `chmod 600`.
5. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
6. Wait for `/health` to return 200.

After it finishes:

- The backend is up on `127.0.0.1:8003` (not publicly accessible yet).
- Default admin account is `admin / admin` — **change immediately** at `/manage/`.

To re-run later (upgrade), just `git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`. The script also exits early if `.env` already exists.

---

## 3. Nginx reverse proxy + HTTPS

The repo ships `config/nginx.conf` as a template with two domains (`admin.` and `app.`). For a single-domain setup, use this minimum config:

```nginx
# /etc/nginx/sites-available/memory-os
server {
    listen 80;
    server_name memory.example.com;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name memory.example.com;

    ssl_certificate     /etc/letsencrypt/live/memory.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/memory.example.com/privkey.pem;

    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /mcp {
        proxy_pass http://127.0.0.1:8003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }

    # Prometheus metrics — never expose to the public
    location /metrics {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8003/metrics;
    }
}
```

Enable + obtain certificate:

```bash
sudo ln -s /etc/nginx/sites-available/memory-os /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d memory.example.com
sudo certbot renew --dry-run    # confirm autorenewal works
```

---

## 4. Post-deploy checklist

| # | Action |
|---|---|
| 1 | Open `https://memory.example.com/manage/` and change the `admin` password |
| 2 | Add at least one LLM provider (DeepSeek / Qwen / OpenAI) under Admin → Providers |
| 3 | Confirm `/health` returns `{"status":"ok"}` over HTTPS |
| 4 | Confirm `/metrics` returns 403 from outside (only `127.0.0.1` should reach it) |
| 5 | Check the backend log for the **absence** of the two security warnings: `MEMORY_OS_JWT_SECRET ... default` and `MEMORY_OS_MASTER_KEY is not set`. If they appear, the env file isn't being read. |
| 6 | Issue a user-scope MCP token under Settings → MCP and verify a Cursor/Claude Desktop connection |

---

## 5. Operations

### Logs

```bash
docker compose logs -f backend         # follow backend
docker compose logs --tail=200 backend
```

### Backups

The schema and memories live in two volumes that you must back up:

| Volume | Critical | What's in it |
|---|---|---|
| `pg_data` | yes | Memories, accounts, billing, canvases |
| `qdrant_data` | yes | Vector embeddings (regenerable but expensive) |
| `neo4j_data` | yes | Knowledge graph edges |
| `minio_data` | yes | Uploaded files (originals) |

```bash
# Daily pg dump (add to crontab)
docker exec ai-memory-os-postgres-1 pg_dump -U memoryos memory_os | gzip > /backup/pg-$(date +%F).sql.gz

# Volume snapshot (offline copy, run when stack is down)
docker compose stop
sudo tar czf /backup/volumes-$(date +%F).tgz /var/lib/docker/volumes/ai-memory-os_*
docker compose start
```

### Upgrades

```bash
cd /opt/memory-os
git fetch origin master && git log HEAD..origin/master --oneline   # review what changed
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs --tail=80 backend     # sanity check
```

### Rollback

```bash
git log --oneline -10
git reset --hard <previous-good-sha>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The data volumes are unaffected. Only the code reverts.

---

## 6. Security baseline (do this before going live)

- `.env` permissions: `chmod 600 .env`, owner = the user that runs `docker compose`.
- Override **every** datastore password — the compose template defaults are public knowledge.
- `MEMORY_OS_MASTER_KEY` must be set, otherwise provider API keys are stored in plaintext (you'll see a startup `WARNING`).
- `MEMORY_OS_JWT_SECRET` must be set, otherwise sessions can be forged trivially.
- Bind internal services to loopback — already done in `docker-compose.yml` (`127.0.0.1:5432:5432` etc).
- Restrict `/metrics` to localhost in nginx.
- Keep `ALLOW_REMOTE_ADMIN=true` only behind a trusted reverse proxy + IP allowlist if you can.
- Rotate the admin password from `admin / admin` on day one.

---

## 7. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/health` returns 200 with HTML body | Old image still running — `docker compose up -d --build` again |
| Backend crash-loops with `connection refused` for postgres | `.env` POSTGRES_PASSWORD changed but pg_data volume still encrypted with the old password. Reset: `docker compose down && docker volume rm ai-memory-os_pg_data && deploy-prod.sh` (DATA LOSS) |
| Mermaid diagrams blank in UI | webui-dist asset hash mismatch — `git pull && docker compose up -d --build` |
| MCP tools return "Canvas unavailable" | task_canvas schema drift — confirm with `docker exec ai-memory-os-postgres-1 psql -U memoryos -d memory_os -c "\d task_canvas"`; expect JSONB columns |
| Provider API key disappears after restart | `MEMORY_OS_MASTER_KEY` was set to a different value than what encrypted the row originally; reset via UI |
