#!/bin/bash
# DW_STORE 项目规则配置脚本
# 用法: 在 dw_store 项目根目录运行此脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DataAgent Rules 配置脚本 ===${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "README.md" ]; then
    echo -e "${YELLOW}警告: 当前目录没有 README.md，请确认是否在项目根目录${NC}"
fi

# 创建规则目录
RULES_DIR=".dataagent/rules"
echo "创建规则目录: $RULES_DIR"
mkdir -p "$RULES_DIR"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 复制项目规则
echo "复制项目规则..."
if [ -d "$SCRIPT_DIR/project-rules" ]; then
    cp "$SCRIPT_DIR/project-rules/"*.md "$RULES_DIR/"
    echo -e "${GREEN}✓ 已复制项目规则${NC}"
else
    echo -e "${YELLOW}未找到项目规则模板，请手动创建${NC}"
fi

# 显示已安装的规则
echo ""
echo "已安装的规则:"
for file in "$RULES_DIR"/*.md; do
    if [ -f "$file" ]; then
        name=$(basename "$file" .md)
        echo "  - $name"
    fi
done

echo ""
echo -e "${GREEN}配置完成！${NC}"
echo ""
echo "使用方法:"
echo "  1. 启动 DataAgent CLI: dataagent"
echo "  2. 查看规则: /rules list"
echo "  3. 规则会自动应用到对话中"
echo ""
echo "规则文件位置: $(pwd)/$RULES_DIR/"
