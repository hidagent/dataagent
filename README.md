# DataAgent

DataAgent 是基于 DeepAgent 构建的数据智能助手平台，支持终端交互和 Web 服务两种使用方式，为数据开发工程师、业务人员和数据管理人员提供智能化的数据处理能力。

## 功能特性

- **多端支持**: CLI 终端交互和 Web API 服务
- **流式输出**: 实时流式响应，支持 WebSocket 和 SSE
- **人机交互 (HITL)**: 敏感操作需用户审批，支持自动审批模式
- **会话管理**: 支持多会话、会话持久化（内存/MySQL）
- **MCP 集成**: 支持 Model Context Protocol 扩展工具
- **中间件系统**: 长期记忆、技能系统、Shell 执行
- **高并发**: 支持 100+ 用户同时问答
- **测试框架**: 内置压测和评估工具

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              DataAgent                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐         ┌─────────────────────────────────────┐  │
│   │  DataAgentCli   │         │         DataAgentServer             │  │
│   │   (终端交互)     │         │          (FastAPI)                  │  │
│   └────────┬────────┘         └─────────────────┬───────────────────┘  │
│            │                                    │                       │
│            │                                    │                       │
│            ▼                                    ▼                       │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                       DataAgentCore                              │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │  │
│   │  │ AgentFactory │  │AgentExecutor │  │    Events    │          │  │
│   │  └──────────────┘  └──────────────┘  └──────────────┘          │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │  │
│   │  │  Middleware  │  │    Tools     │  │     HITL     │          │  │
│   │  └──────────────┘  └──────────────┘  └──────────────┘          │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    External Dependencies                         │  │
│   │  deepagents | LangChain | LangGraph | Sandbox Providers         │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
dataagent/
├── source/
│   ├── dataagent-core/      # 核心库：Agent 创建、执行、事件系统
│   ├── dataagent-cli/       # CLI 客户端：终端交互界面
│   ├── dataagent-server/    # Web 服务：REST API + WebSocket
│   └── dataagent-harbor/    # 测试框架：压测和评估工具
├── libs/                    # 依赖库（deepagents 等）
└── docs/                    # 设计文档
```

## 快速开始

### 环境要求

- Python >= 3.11
- uv (推荐) 或 pip

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd dataagent

# 安装核心库
cd source/dataagent-core
pip install -e .

# 安装 CLI（可选）
cd ../dataagent-cli
pip install -e .

# 安装 Server（可选）
cd ../dataagent-server
pip install -e .
```

### 配置环境变量

```bash
# LLM API Keys（至少配置一个）
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."

# 可选：Web 搜索
export TAVILY_API_KEY="tvly-..."
```

### 使用 CLI

```bash
# 启动交互式会话
dataagent

# 使用指定 Agent
dataagent --agent mybot

# 自动审批模式
dataagent --auto-approve
```

### 启动 Server

```bash
# 启动服务
dataagent-server

# 或使用 uvicorn
uvicorn dataagent_server.main:app --host 0.0.0.0 --port 8000
```

## 组件说明

### DataAgentCore

核心业务逻辑层，提供：

| 模块 | 说明 |
|------|------|
| `engine/` | Agent 工厂和执行器 |
| `events/` | 事件系统 (TextEvent, ToolCallEvent 等) |
| `middleware/` | 中间件 (Memory, Skills, Shell) |
| `tools/` | 工具系统 (HTTP, Web Search, File Tracker) |
| `hitl/` | HITL 协议定义 |
| `session/` | 会话管理和存储 |
| `mcp/` | MCP 集成 |

### DataAgentServer

Web 服务层，提供：

| 端点 | 说明 |
|------|------|
| `GET /api/v1/health` | 健康检查 |
| `POST /api/v1/chat` | 发送消息（同步） |
| `POST /api/v1/chat/{session_id}/cancel` | 取消问答 |
| `GET /api/v1/sessions` | 列出会话 |
| `GET /api/v1/sessions/{session_id}/messages` | 获取历史消息 |
| `/ws/chat/{session_id}` | WebSocket 实时聊天 |

### DataAgentCli

终端客户端，支持：

- 交互式聊天
- 文件操作预览（Diff）
- Shell 命令执行
- HITL 审批交互
- 斜杠命令 (`/help`, `/reset` 等)

### DataAgentHarbor

测试评估框架，支持：

- 批量压测
- 并发测试
- 结果统计
- LangSmith 追踪

## 配置参考

### Server 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DATAAGENT_HOST` | 监听地址 | `0.0.0.0` |
| `DATAAGENT_PORT` | 监听端口 | `8000` |
| `DATAAGENT_API_KEYS` | API Key 列表（逗号分隔） | - |
| `DATAAGENT_SESSION_TIMEOUT` | 会话超时秒数 | `3600` |
| `DATAAGENT_AUTH_DISABLED` | 禁用认证 | `false` |
| `DATAAGENT_MAX_CONNECTIONS` | 最大并发连接数 | `200` |

### 会话存储配置

```bash
# 内存存储（默认）
DATAAGENT_SESSION_STORE=memory

# MySQL 存储
DATAAGENT_SESSION_STORE=mysql
DATAAGENT_MYSQL_HOST=localhost
DATAAGENT_MYSQL_PORT=3306
DATAAGENT_MYSQL_USER=dataagent
DATAAGENT_MYSQL_PASSWORD=your_password
DATAAGENT_MYSQL_DATABASE=dataagent
```

## 事件类型

Agent 执行过程通过事件流与 UI 层通信：

| 事件 | 说明 |
|------|------|
| `TextEvent` | 文本输出 |
| `ToolCallEvent` | 工具调用 |
| `ToolResultEvent` | 工具结果 |
| `HITLRequestEvent` | HITL 审批请求 |
| `TodoUpdateEvent` | 任务列表更新 |
| `FileOperationEvent` | 文件操作 |
| `ErrorEvent` | 错误信息 |
| `DoneEvent` | 执行完成 |

## 开发

```bash
# 运行测试
cd source/dataagent-core
pytest

# 运行测试并生成覆盖率报告
pytest --cov=dataagent_core --cov-report=html
```

## 文档

- [架构设计](docs/architecture.md)
- [详细设计文档](docs/dataagent-design/)
- [API 参考](docs/api-reference.md)
- [开发指南](docs/developer-guide.md)

## License

MIT
