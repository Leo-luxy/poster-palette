#!/bin/sh
# 装本地钩子：拦住不小心提交 data/ 的情况。
# 用法：sh scripts/install_hooks.sh
set -e
root=$(git rev-parse --show-toplevel)
cd "$root"
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
echo "✓ 已启用 .githooks"
echo "  以后提交里带 data/ 会被拦下来；A 补数据时用 ALLOW_DATA=1 git commit ..."
