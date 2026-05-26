#!/bin/bash
# weekly_security_scan.sh

echo "=== 每周依赖安全扫描 $(date +%Y-%m-%d) ==="

# Create local temp dir
mkdir -p .tmp

# Python 依赖
echo "── Python 依赖 ─────────────────────"
if command -v pip-audit &>/dev/null; then
    pip-audit --requirement backend/requirements.txt \
        --format=json > .tmp/py_audit.json 2>/dev/null

    VULN_COUNT=$(python3 -c "
import json, os
if os.path.exists('.tmp/py_audit.json'):
    data = json.load(open('.tmp/py_audit.json'))
    vulns = [v for p in data for v in p.get('vulns', [])]
    print(len(vulns))
else:
    print(0)
" 2>/dev/null || echo 0)

    [ "$VULN_COUNT" -gt 0 ] \
        && echo "⚠️  发现 $VULN_COUNT 个漏洞，请升级" \
        || echo "✅ 无已知漏洞"
else
    echo "⚠️  未安装 pip-audit，跳过 Python 漏洞扫描"
fi

# NPM 依赖
echo "── NPM 依赖 ────────────────────────"
if [ -d "webui" ]; then
    (cd webui && npm audit --audit-level=high --json > ../.tmp/npm_audit.json 2>/dev/null)
    NPM_HIGH=$(python3 -c "
import json, os
if os.path.exists('.tmp/npm_audit.json'):
    data = json.load(open('.tmp/npm_audit.json'))
    print(data.get('metadata',{}).get('vulnerabilities',{}).get('high', 0))
else:
    print(0)
" 2>/dev/null || echo 0)

    [ "$NPM_HIGH" -gt 0 ] \
        && echo "⚠️  发现 $NPM_HIGH 个高危 NPM 漏洞" \
        || echo "✅ 无高危 NPM 漏洞"
else
    echo "⚠️  未找到 webui 目录，跳过 NPM 漏洞扫描"
fi

echo "=== 依赖扫描完成 ==="
