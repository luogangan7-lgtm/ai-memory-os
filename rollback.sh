#!/bin/bash
# rollback.sh — 提前写好，出问题直接运行

PREV_VERSION="${1:-}"  # 传入旧版本号，如 v6.0

if [ -z "$PREV_VERSION" ]; then
    echo "用法：bash rollback.sh v6.0"
    exit 1
fi

echo "[$(date)] 开始回滚到 $PREV_VERSION"

# 1. 回滚代码
git checkout "$PREV_VERSION"
docker compose build backend

# 2. 重启服务
docker compose up -d backend
sleep 15

# 3. 验证
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    http://localhost:8003/health)

if [ "$STATUS" = "200" ]; then
    echo "✅ 回滚成功，版本：$PREV_VERSION"
else
    echo "❌ 回滚后服务仍异常，HTTP：$STATUS"
    echo "请检查日志：docker compose logs backend --tail=100"
fi
