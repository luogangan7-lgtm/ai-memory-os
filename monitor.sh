#!/bin/bash
# monitor.sh — 每 5 分钟由 cron 执行

WEBHOOK_URL="${MONITOR_WEBHOOK_URL:-}"  # 钉钉/飞书/Slack URL

alert() {
    local msg="$1"
    echo "[$(date)] ALERT: $msg"
    if [ -n "$WEBHOOK_URL" ]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"🚨 AI Memory OS 告警：$msg\"}" \
            > /dev/null
    fi
}

# 1. 服务健康检查
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    http://localhost:8003/health 2>/dev/null)
[ "$STATUS" != "200" ] && alert "健康检查失败，HTTP 状态：$STATUS"

# 2. 磁盘使用率
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
[ "$DISK_USAGE" -gt 75 ] && alert "磁盘使用率 ${DISK_USAGE}%，请及时清理"

# 3. 内存使用率
if command -v free &>/dev/null; then
    MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3/$2*100}')
    [ "$MEM_USAGE" -gt 85 ] && alert "内存使用率 ${MEM_USAGE}%"
else
    # macOS fallback
    TOTAL_MEM=$(sysctl hw.memsize | awk '{print $2}')
    if [ -n "$TOTAL_MEM" ]; then
        echo "Total memory: $((TOTAL_MEM / 1024 / 1024)) MB"
    fi
fi

# 4. 错误日志扫描（最近 5 分钟）
if command -v docker &>/dev/null; then
    ERROR_COUNT=$(docker compose logs backend --since=5m 2>/dev/null \
        | grep -c "ERROR" || echo 0)
    [ "$ERROR_COUNT" -gt 10 ] && alert "最近5分钟出现 ${ERROR_COUNT} 个 ERROR 日志"
fi

echo "[$(date)] 监控检查完成"
