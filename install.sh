#!/bin/bash
#
# macOS 磁盘空间分析工具 - 安装脚本
# 使用方法: ./install.sh
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║     macOS 磁盘空间分析工具 - 安装程序          ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
MAIN_PY="$SCRIPT_DIR/main.py"

# 检查 Python3
echo -e "${YELLOW}[1/4] 检查 Python 环境...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "  ✓ 已找到 $PYTHON_VERSION"
else
    echo -e "${RED}  ✗ 未找到 Python3，请先安装 Python 3.8+${NC}"
    echo "    推荐使用 Homebrew: brew install python3"
    exit 1
fi

# 检查 Python 版本
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}  ✗ Python 版本过低，需要 3.8+${NC}"
    exit 1
fi

# 创建虚拟环境
echo -e "${YELLOW}[2/4] 创建虚拟环境...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo "  ✓ 虚拟环境已存在"
else
    python3 -m venv "$VENV_DIR"
    echo "  ✓ 虚拟环境创建成功"
fi

# 安装依赖
echo -e "${YELLOW}[3/4] 安装依赖...${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q
echo "  ✓ 依赖安装完成"

# 添加到 shell
echo -e "${YELLOW}[4/4] 配置 shell 命令...${NC}"

# 生成 shell 函数
SHELL_FUNC="
# macOS 磁盘空间分析工具 (disk-analyzer)
disk-analyzer() {
    \"$VENV_DIR/bin/python3\" \"$MAIN_PY\" \"\$@\"
}"

# 检测 shell 类型
SHELL_RC=""
if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    # 检查是否已添加
    if grep -q "disk-analyzer()" "$SHELL_RC" 2>/dev/null; then
        echo "  ✓ 命令已存在于 $SHELL_RC"
    else
        echo "$SHELL_FUNC" >> "$SHELL_RC"
        echo "  ✓ 已添加 disk-analyzer 命令到 $SHELL_RC"
    fi
else
    echo -e "${YELLOW}  ⚠ 无法检测 shell 类型，请手动添加以下内容到你的 shell 配置文件:${NC}"
    echo "$SHELL_FUNC"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ 安装完成!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "使用方法:"
echo "  1. 重新加载 shell 配置: source $SHELL_RC"
echo "  2. 运行分析工具: disk-analyzer ~"
echo ""
echo "更多选项请运行: disk-analyzer --help"
