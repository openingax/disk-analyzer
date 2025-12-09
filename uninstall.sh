#!/bin/bash
#
# macOS 磁盘空间分析工具 - 卸载脚本
#

set -e

echo "正在卸载 disk-analyzer..."

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 删除虚拟环境
if [ -d "$SCRIPT_DIR/.venv" ]; then
    rm -rf "$SCRIPT_DIR/.venv"
    echo "  ✓ 已删除虚拟环境"
fi

# 从 shell 配置中移除
for RC_FILE in "$HOME/.zshrc" "$HOME/.bashrc"; do
    if [ -f "$RC_FILE" ]; then
        # 使用 sed 删除相关行
        sed -i '' '/# macOS 磁盘空间分析工具/d' "$RC_FILE" 2>/dev/null || true
        sed -i '' '/disk-analyzer()/,/^}/d' "$RC_FILE" 2>/dev/null || true
        echo "  ✓ 已从 $RC_FILE 移除命令"
    fi
done

echo ""
echo "✅ 卸载完成！请运行 source ~/.zshrc 使更改生效"
