#!/bin/bash
# DataAgent 开发模式快速启动脚本
# 用法: ./scripts/dev.sh [command] [options]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/source/dataagent-core:$PROJECT_ROOT/source/dataagent-cli:$PROJECT_ROOT/source/dataagent-server:$PROJECT_ROOT/source/dataagent-harbor:$PYTHONPATH"

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  DataAgent Development Tools${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

show_help() {
    print_header
    echo ""
    echo -e "${YELLOW}Usage:${NC} ./scripts/dev.sh <command> [options]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  cli [args]        Run DataAgent CLI"
    echo "  server [args]     Run DataAgent Server (with hot-reload)"
    echo "  demo              Run Streamlit Demo (with hot-reload)"
    echo "  dev [port]        Run Server + Demo together (recommended for development)"
    echo "  test [module]     Run tests (core|server|harbor|all)"
    echo "  install           Install all packages in dev mode"
    echo "  help              Show this help"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  ./scripts/dev.sh cli                    # Start CLI"
    echo "  ./scripts/dev.sh cli --agent mybot      # Start CLI with agent"
    echo "  ./scripts/dev.sh cli --auto-approve     # Start CLI with auto-approve"
    echo "  ./scripts/dev.sh cli help               # Show CLI help"
    echo "  ./scripts/dev.sh server                 # Start server on port 8000"
    echo "  ./scripts/dev.sh server --port 9000     # Start server on port 9000"
    echo "  ./scripts/dev.sh demo                   # Start demo only"
    echo "  ./scripts/dev.sh dev                    # Start server + demo (port 8000)"
    echo "  ./scripts/dev.sh dev 9000               # Start server + demo (port 9000)"
    echo "  ./scripts/dev.sh test core              # Run core tests"
    echo "  ./scripts/dev.sh test server            # Run server tests"
    echo "  ./scripts/dev.sh test                   # Run all tests"
    echo ""
}

run_cli() {
    echo -e "${GREEN}Starting DataAgent CLI...${NC}"
    python3 -m dataagent_cli.main "$@"
}

run_server() {
    local port=8000
    local args=()
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                port="$2"
                shift 2
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    
    echo -e "${GREEN}Starting DataAgent Server on port $port...${NC}"
    echo -e "${YELLOW}Hot-reload enabled - changes will auto-reload${NC}"
    echo ""
    uvicorn dataagent_server.main:app --reload --host 0.0.0.0 --port "$port" "${args[@]}"
}

run_demo() {
    echo -e "${GREEN}Starting Streamlit Demo...${NC}"
    echo -e "${YELLOW}Hot-reload enabled - changes will auto-reload${NC}"
    echo ""
    streamlit run source/dataagent-server-demo/dataagent_server_demo/app.py --server.runOnSave true
}

run_dev() {
    # 同时启动 Server 和 Demo
    echo -e "${GREEN}Starting Server + Demo development environment...${NC}"
    echo ""
    
    # 检查端口是否被占用
    local server_port="${1:-8000}"
    
    # 启动 Server（后台）
    echo -e "${YELLOW}Starting Server on port $server_port (background)...${NC}"
    uvicorn dataagent_server.main:app --reload --host 0.0.0.0 --port "$server_port" &
    SERVER_PID=$!
    
    # 等待 Server 启动
    sleep 2
    
    # 检查 Server 是否启动成功
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${RED}Server failed to start${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Server started (PID: $SERVER_PID)${NC}"
    echo ""
    
    # 启动 Demo（前台）
    echo -e "${YELLOW}Starting Demo...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop both Server and Demo${NC}"
    echo ""
    
    # 捕获退出信号，清理后台进程
    trap "echo ''; echo -e '${YELLOW}Stopping...${NC}'; kill $SERVER_PID 2>/dev/null; exit 0" INT TERM
    
    streamlit run source/dataagent-server-demo/dataagent_server_demo/app.py --server.runOnSave true
    
    # Demo 退出后，停止 Server
    kill $SERVER_PID 2>/dev/null
}

run_tests() {
    local module="${1:-all}"
    
    case $module in
        core)
            echo -e "${GREEN}Running Core tests...${NC}"
            pytest source/dataagent-core/tests -v
            ;;
        server)
            echo -e "${GREEN}Running Server tests...${NC}"
            pytest source/dataagent-server/tests -v
            ;;
        harbor)
            echo -e "${GREEN}Running Harbor tests...${NC}"
            pytest source/dataagent-harbor/tests -v
            ;;
        all|"")
            echo -e "${GREEN}Running all tests...${NC}"
            pytest source/dataagent-core/tests source/dataagent-server/tests -v
            ;;
        *)
            echo -e "${GREEN}Running tests: $module${NC}"
            pytest "$module" -v
            ;;
    esac
}

install_dev() {
    echo -e "${GREEN}Installing packages in development mode...${NC}"
    pip install -e source/dataagent-core
    pip install -e source/dataagent-cli
    pip install -e source/dataagent-server
    pip install -e source/dataagent-harbor
    echo -e "${GREEN}✓ Installation complete${NC}"
}

# 主命令处理
case "${1:-help}" in
    cli)
        shift
        run_cli "$@"
        ;;
    server)
        shift
        run_server "$@"
        ;;
    demo)
        run_demo
        ;;
    dev)
        shift
        run_dev "$@"
        ;;
    test)
        shift
        run_tests "$@"
        ;;
    install)
        install_dev
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
