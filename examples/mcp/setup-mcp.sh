#!/bin/bash
# MCP 配置快速设置脚本
# 用法: ./setup-mcp.sh [agent_name]

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

AGENT_NAME="${1:-agent}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.deepagents/$AGENT_NAME"

echo -e "${GREEN}=== DataAgent MCP 配置脚本 ===${NC}"
echo ""
echo -e "Agent: ${BLUE}$AGENT_NAME${NC}"
echo -e "目标目录: ${BLUE}$TARGET_DIR${NC}"
echo ""

# 创建目录
mkdir -p "$TARGET_DIR"

# 检查是否已存在配置
if [ -f "$TARGET_DIR/mcp.json" ]; then
    echo -e "${YELLOW}警告: $TARGET_DIR/mcp.json 已存在${NC}"
    read -p "是否覆盖? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
fi

# 选择配置模板
echo "请选择配置模板:"
echo "  1) 最小配置 (仅文件系统)"
echo "  2) 标准配置 (文件系统 + AWS 文档)"
echo "  3) 高级配置 (多个服务器)"
echo ""
read -p "选择 [1-3]: " choice

case $choice in
    1)
        cp "$SCRIPT_DIR/mcp-minimal.json" "$TARGET_DIR/mcp.json"
        echo -e "${GREEN}✓ 已复制最小配置${NC}"
        ;;
    2)
        cp "$SCRIPT_DIR/mcp.json" "$TARGET_DIR/mcp.json"
        echo -e "${GREEN}✓ 已复制标准配置${NC}"
        ;;
    3)
        cp "$SCRIPT_DIR/mcp-advanced.json" "$TARGET_DIR/mcp.json"
        echo -e "${GREEN}✓ 已复制高级配置${NC}"
        ;;
    *)
        echo "无效选择，使用标准配置"
        cp "$SCRIPT_DIR/mcp.json" "$TARGET_DIR/mcp.json"
        ;;
esac

echo ""
echo -e "${GREEN}配置完成！${NC}"
echo ""
echo "配置文件位置: $TARGET_DIR/mcp.json"
echo ""
echo "下一步:"
echo "  1. 编辑配置文件，修改路径和 token"
echo "  2. 启动 DataAgent CLI: dataagent --agent $AGENT_NAME"
echo "  3. 使用 /mcp 命令查看服务器状态"
echo ""
echo -e "${YELLOW}注意: 请确保已安装 npx (Node.js) 或 uvx (Python)${NC}"
