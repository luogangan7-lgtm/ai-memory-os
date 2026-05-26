#!/bin/bash
# security_check.sh

echo "=== 安全审查清单 ==="

# 1. 检查敏感信息硬编码
echo "▶ 扫描硬编码密钥..."
if grep -r "sk-\|password\s*=\s*['\"][^'\"]\|secret\s*=\s*['\"][^'\"]" \
    backend/ --include="*.py" | grep -v "test\|#\|env\|os.get"; then
    echo "❌ 发现可能的硬编码密钥，请检查"
else
    echo "✅ 无硬编码密钥"
fi

# 2. 依赖安全扫描
echo "▶ 扫描 Python 依赖漏洞..."
# Try pip-audit or check if it exists, otherwise skip/warn
if command -v pip-audit &>/dev/null; then
    pip-audit --requirement backend/requirements.txt 2>/dev/null \
        && echo "✅ Python 依赖无已知漏洞" \
        || echo "⚠️  发现已知漏洞，查看详情并评估是否需要升级"
else
    echo "⚠️  未安装 pip-audit，跳过 Python 依赖漏洞扫描 (可运行 pip install pip-audit 安装)"
fi

echo "▶ 扫描 NPM 依赖漏洞..."
if [ -d "webui" ]; then
    (cd webui && npm audit --audit-level=high 2>/dev/null \
        && echo "✅ NPM 依赖无高危漏洞" \
        || echo "⚠️  发现高危漏洞")
else
    echo "⚠️  未发现 webui 目录，跳过 NPM 漏洞扫描"
fi

# 3. SQL 注入检查（确保使用参数化查询）
echo "▶ 检查 SQL 拼接..."
# Filter out benign comment lines or print statement logs
if grep -r "f\"SELECT\|f'SELECT\|\.format.*SELECT\|%.*SELECT" \
    backend/ --include="*.py" | grep -v "test"; then
    echo "❌ 发现可能的 SQL 拼接，必须改为参数化查询"
else
    echo "✅ 未发现 SQL 拼接"
fi

echo ""
echo "=== 安全审查完成 ==="
