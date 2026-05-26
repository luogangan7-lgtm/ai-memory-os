#!/bin/bash
# check_init.sh

PASS=0; FAIL=0

check() {
    if eval "$2" &>/dev/null; then
        echo "✅ $1"; ((PASS++))
    else
        echo "❌ $1 — $3"; ((FAIL++))
    fi
}

check ".env 文件存在"        "[ -f .env ]"              "cp .env.example .env 并填写"
check ".gitignore 包含 .env" "grep -q '^\.env' .gitignore" "echo '.env' >> .gitignore"
check "README.md 存在"       "[ -f README.md ]"         "创建 README.md"
check "docker-compose.yml"   "[ -f docker-compose.yml ]" "补充 docker-compose.yml"
check "migrations 目录"      "[ -d migrations ]"        "mkdir -p migrations"
check "tests 目录"           "[ -d tests ]"             "mkdir -p tests"
check "Git 已初始化"          "git rev-parse --git-dir"  "git init"
check "main 分支存在"         "git branch | grep -E 'q main|master'" "git checkout -b main"

echo ""
echo "初始化检查：✅ $PASS 通过 | ❌ $FAIL 失败"
[ $FAIL -gt 0 ] && exit 1 || echo "可以开始开发"
