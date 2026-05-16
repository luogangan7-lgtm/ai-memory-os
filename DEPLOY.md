# AI Memory OS — Nginx 反代 + HTTPS 部署指南

## 1. 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt install nginx certbot python3-certbot-nginx -y

# CentOS/RHEL
sudo yum install nginx certbot python3-certbot-nginx -y
```

## 2. Nginx 配置文件

创建 `/etc/nginx/sites-available/memory-os`：

```nginx
server {
    listen 80;
    server_name memory.your-domain.com;   # 替换为你的域名

    # 上传文件大小限制
    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket 支持（用于 MCP SSE）
    location /mcp {
        proxy_pass http://127.0.0.1:8003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400s;
    }
}
```

启用站点：
```bash
sudo ln -s /etc/nginx/sites-available/memory-os /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 3. HTTPS (Let's Encrypt 免费证书)

```bash
sudo certbot --nginx -d memory.your-domain.com
```

证书会自动续期。验证自动续期：
```bash
sudo certbot renew --dry-run
```

## 4. 防火墙开放端口

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 5. 启动 Memory OS

```bash
cd /path/to/ai-memory-os
docker-compose up -d
```

## 6. 验证

浏览器打开 `https://memory.your-domain.com/manage/` 和 `https://memory.your-domain.com/app/`
