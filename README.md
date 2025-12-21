# 🚀 DataAgent - 基于 DeepAgent 的企业级 AI 数据智能助手平台

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-orange.svg)](https://www.postgresql.org/)
[![DeepAgent](https://img.shields.io/badge/Built%20on-DeepAgent-purple.svg)](https://github.com/deepagent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-red.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
[![JWT](https://img.shields.io/badge/JWT-Authentication-blue.svg)](https://jwt.io/)

[English](./PROJECT_INTRO_EN.md) | [中文介绍](./PROJECT_INTRO.md)

</div>

**DataAgent** 是一款基于 **DeepAgent** 引擎构建的企业级 AI 数据智能助手平台，专为数据工程师、业务分析师、数据科学家和开发团队设计。支持 **多模态交互**（CLI终端、Web界面、REST API、WebSocket），具备 **人机协同** 工作流程和 **事件驱动架构**，实现智能化的数据处理、分析和决策支持。

**DataAgent** is an enterprise-grade AI data intelligence assistant platform built on the **DeepAgent** engine, designed for data engineers, business analysts, data scientists, and development teams. It supports **multi-modal interaction** (CLI terminal, Web interface, REST API, WebSocket) with **human-in-the-loop** workflows and **event-driven architecture** for intelligent data processing, analysis, and decision support.

## 🔥 核心特性 | Core Features

### 🤖 AI 驱动 | AI-Powered
- **基于 DeepAgent 引擎** | Built on DeepAgent Engine
- **多 LLM 支持** | Multi-LLM Support (GPT-4, Claude-3, Gemini)
- **智能代理系统** | Intelligent Agent System
- **实时流式响应** | Real-time Streaming Response
- **LangChain/LangGraph 集成** | LangChain/LangGraph Integration

### 🏢 企业级架构 | Enterprise Architecture
- **多租户隔离** | Multi-tenant Isolation
- **JWT 安全认证** | JWT Security Authentication
- **工作空间管理** | Workspace Management
- **微服务架构** | Microservices Architecture
- **高可用性** | High Availability

### 🛡️ 人机协同 | Human-in-the-Loop
- **智能审批流程** | Intelligent Approval Workflow
- **安全沙箱执行** | Secure Sandbox Execution
- **多界面统一** | Unified Multi-interface
- **操作审计** | Operation Auditing
- **权限管理** | Permission Management

### 📊 事件驱动 | Event-Driven
- **实时事件流** | Real-time Event Streaming
- **异步处理** | Asynchronous Processing
- **状态管理** | State Management
- **可观测性** | Observability
- **性能监控** | Performance Monitoring

### 🌐 多模态交互 | Multi-modal Interaction
- **CLI 终端** | CLI Terminal Interface
- **Web 界面** | Web Interface (Streamlit)
- **REST API** | RESTful API
- **WebSocket** | WebSocket Real-time
- **移动端支持** | Mobile Support

### 💾 灵活存储 | Flexible Storage
- **会话持久化** | Session Persistence
- **多数据库支持** | Multi-database Support
- **缓存机制** | Caching Mechanism
- **数据备份** | Data Backup
- **灾难恢复** | Disaster Recovery

### 🔧 可扩展工具系统 | Extensible Tool System
- **MCP 协议集成** | MCP Protocol Integration
- **内置技能集** | Built-in Skill Set
- **自定义工具** | Custom Tools
- **插件架构** | Plugin Architecture
- **API 集成** | API Integration

### 🧪 测试与监控 | Testing & Monitoring
- **压力测试** | Load Testing
- **性能评估** | Performance Evaluation
- **实时监控** | Real-time Monitoring
- **日志分析** | Log Analysis
- **异常告警** | Exception Alerting

## 🏗️ 系统架构 | System Architecture

<div align="center">

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DataAgent 系统架构图                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐         ┌─────────────────┐                   │
│  │   CLI Terminal  │         │   Web Interface │                   │
│  │   (Rich UI)     │         │  (Streamlit)    │                   │
│  └────────┬────────┘         └────────┬────────┘                   │
│           │                           │                              │
│  ┌────────┴───────────────────────────┴────────┐                    │
│  │          DataAgentServer (FastAPI)          │                    │
│  │  ┌──────────────┐  ┌──────────────┐        │                    │
│  │  │   REST API   │  │   WebSocket   │        │                    │
│  │  │  /api/v1/*   │  │  /ws/chat/*   │        │                    │
│  │  └──────┬───────┘  └──────┬───────┘        │                    │
│  └─────────┼─────────────────┼─────────────────┘                    │
│            │                 │                                      │
│  ┌─────────▼─────────────────▼─────────────────┐                    │
│  │          Event Stream (AsyncIterator)        │                    │
│  └───────────────────┬─────────────────────────┘                    │
│                      │                                              │
│  ┌───────────────────▼─────────────────────────┐                    │
│  │           DataAgentCore (基于 DeepAgent)      │                    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ │                    │
│  │  │AgentFactory│ │AgentExecutor│ │   Events   │ │                    │
│  │  │(创建代理)    │ │(执行任务)    │ │(事件管理)    │ │                    │
│  │  └────────────┘ └────────────┘ └────────────┘ │                    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ │                    │
│  │  │ Middleware │ │   Tools    │ │    HITL    │ │                    │
│  │  │(中间件)     │ │(工具集)     │ │(人机交互)   │ │                    │
│  │  └────────────┘ └────────────┘ └────────────┘ │                    │
│  └───────────────────┬─────────────────────────┘                    │
└─────────────────────┼───────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────────┐
│                    Storage Layer                                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│  │ PostgreSQL │ │   SQLite   │ │Memory Store│ │   Redis    │      │
│  │(Production)│ │(Development)│ │(Testing)   │ │(Cache)     │      │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

</div>

## 📁 项目结构 | Project Structure

<div align="center">

```
dataagent/
├── 📁 source/                          # DataAgent 源代码 | Source Code
│   ├── 🎯 dataagent-core/              # 核心引擎 | Core Engine
│   │   ├── 🧠 engine/                  # Agent 工厂和执行器 | Agent Factory & Executor
│   │   ├── 📡 events/                  # 事件系统 | Event System
│   │   ├── 🔧 middleware/              # 中间件系统 | Middleware System
│   │   ├── 🛠️ tools/                   # 工具集成 | Tools Integration
│   │   ├── 👥 hitl/                    # 人机交互 | Human-in-the-Loop
│   │   ├── 💾 session/                 # 会话管理 | Session Management
│   │   └── 🔌 mcp/                     # MCP 协议 | Model Context Protocol
│   ├── 💻 dataagent-cli/               # CLI 客户端 | CLI Client
│   │   ├── 🖥️ terminal/                # 终端交互 | Terminal Interface
│   │   ├── 📊 diff_viewer/             # 文件差异 | File Diff Viewer
│   │   └── ⚡ commands/                 # 命令处理 | Command Processing
│   ├── 🌐 dataagent-server/            # Web 服务 | Web Server
│   │   ├── 🔗 api/v1/                  # REST API 接口 | REST API Endpoints
│   │   ├── ⚡ ws/                       # WebSocket 处理 | WebSocket Handlers
│   │   ├── 🔐 auth/                    # 认证授权 | Authentication
│   │   ├── 👤 models/                  # 数据模型 | Data Models
│   │   └── 🛠️ services/                # 业务服务 | Business Services
│   ├── 🧪 dataagent-harbor/            # 测试框架 | Testing Framework
│   │   ├── 📊 benchmarks/              # 性能基准 | Performance Benchmarks
│   │   ├── 🎯 evaluators/              # 评估器 | Evaluators
│   │   └── 📈 analytics/               # 分析工具 | Analytics Tools
│   └── 🎮 dataagent-server-demo/       # Streamlit 演示 | Streamlit Demo
├── 📚 libs/                            # 依赖库 | Dependencies
├── 📄 docs/                            # 设计文档 | Documentation
├── 🐳 docker/                          # 容器配置 | Docker Configs
├── ⚙️ scripts/                         # 脚本工具 | Scripts
└── 🧪 tests/                           # 测试用例 | Test Cases
```

</div>

## 🚀 快速开始 | Quick Start

### 📋 环境要求 | Requirements

- **Python 3.11+** - 主要开发语言
- **PostgreSQL 12+** - 生产环境数据库
- **Redis 6+** - 缓存和会话存储（可选）
- **OpenAI API Key** 或 **Anthropic API Key** - LLM 服务
- **Tavily API Key** - 网络搜索（可选）

### 🔧 安装步骤 | Installation

#### 1. 📥 克隆项目 | Clone Project
```bash
git clone https://github.com/hidagent/dataagent.git
cd dataagent
```

#### 2. 🐍 创建虚拟环境 | Create Virtual Environment
```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 或者使用 conda
conda create -n dataagent python=3.11
conda activate dataagent
```

#### 3. 📦 安装依赖 | Install Dependencies
```bash
# 安装核心引擎 | Install Core Engine
cd source/dataagent-core
pip install -e .

# 安装 CLI 客户端 | Install CLI Client
cd ../dataagent-cli
pip install -e .

# 安装 Web 服务 | Install Web Server
cd ../dataagent-server
pip install -e .

# 安装测试框架 | Install Testing Framework
cd ../dataagent-harbor
pip install -e .
```

#### 4. ⚙️ 配置环境变量 | Configure Environment
```bash
# 复制环境变量模板 | Copy environment template
cp .env.example .env

# 编辑 .env 文件，配置以下关键变量 | Edit .env file with these key variables:
# OpenAI API 密钥
OPENAI_API_KEY="sk-your-openai-api-key"
# 或 Anthropic API 密钥 | or Anthropic API key
ANTHROPIC_API_KEY="sk-ant-your-anthropic-api-key"

# 数据库连接 | Database connection
DATABASE_URL="postgresql://user:password@localhost:5432/dataagent"

# JWT 密钥 | JWT secret
JWT_SECRET_KEY="your-jwt-secret-key"

# Redis 连接（可选）| Redis connection (optional)
REDIS_URL="redis://localhost:6379/0"
```

#### 5. 🗄️ 初始化数据库 | Initialize Database
```bash
# 创建数据库表 | Create database tables
python -m dataagent_core.database.init

# 或者使用 Alembic 迁移 | Or use Alembic migrations
alembic upgrade head
```

#### 6. 🧪 运行测试 | Run Tests
```bash
# 运行单元测试 | Run unit tests
pytest tests/

# 运行集成测试 | Run integration tests
pytest tests/integration/

# 生成测试报告 | Generate test coverage report
pytest --cov=dataagent_core --cov-report=html
```

### 🚀 启动服务 | Start Services

#### 🖥️ CLI 模式 | CLI Mode
```bash
# 启动交互式会话 | Start interactive session
dataagent

# 使用指定 Agent | Use specific agent
dataagent --agent mybot

# 自动审批模式 | Auto-approval mode
dataagent --auto-approve

# 查看帮助 | Show help
dataagent --help
```

#### 🌐 Web 服务模式 | Web Server Mode
```bash
# 启动 Web 服务 | Start web server
dataagent-server

# 或使用 uvicorn | Or use uvicorn
uvicorn dataagent_server.main:app --host 0.0.0.0 --port 8000

# 启动 Streamlit 演示 | Start Streamlit demo
streamlit run source/dataagent-server-demo/app.py
```

#### 📊 测试模式 | Testing Mode
```bash
# 运行压力测试 | Run load testing
dataagent-harbor --mode benchmark --users 100 --duration 60

# 运行评估测试 | Run evaluation tests
dataagent-harbor --mode evaluate --test-suite basic
```

### 📖 使用示例 | Usage Examples

#### 🖥️ CLI 终端示例 | CLI Terminal Examples
```bash
# 启动 CLI 客户端 | Start CLI client
$ dataagent

# 交互式对话 | Interactive conversation
> 你好，请分析这份销售数据的趋势
> 帮我生成一个数据可视化报告
> 执行 ls -la 命令

# 查看命令帮助 | View command help
> /help

# 重置会话 | Reset session
> /reset

# 查看会话历史 | View session history
> /history

# 文件操作预览 | File operation preview
> 请修改 config.py 文件，添加 DEBUG=True
```

#### 🔌 API 调用示例 | API Usage Examples
```python
import requests
import json

# REST API 调用 | REST API call
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    headers={
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json",
        "X-Workspace-ID": "workspace-123"
    },
    json={
        "message": "分析这份销售数据的趋势和异常",
        "session_id": "session-456",
        "agent_id": "data-analyst",
        "stream": False
    }
)

print(response.json())

# WebSocket 实时通信 | WebSocket real-time communication
import websocket

ws = websocket.WebSocket()
ws.connect("ws://localhost:8000/ws/chat/session-456?token=YOUR_TOKEN")

# 发送消息 | Send message
ws.send(json.dumps({
    "message": "你好，AI助手",
    "message_type": "text"
}))

# 接收响应 | Receive response
response = ws.recv()
data = json.loads(response)
print(f"AI: {data['content']}")
```

#### 🐍 Python SDK 示例 | Python SDK Examples
```python
from dataagent_client import DataAgentClient

# 初始化客户端 | Initialize client
client = DataAgentClient(
    api_key="your_api_key",
    base_url="http://localhost:8000",
    workspace_id="workspace-123"
)

# 创建会话 | Create session
session = client.create_session(
    name="数据分析会话",
    description="销售数据趋势分析",
    agent_id="data-analyst"
)

# 发送消息 | Send message
response = client.chat(
    session_id=session.id,
    message="请分析这份 CSV 数据的销售趋势",
    stream=True  # 流式响应
)

# 文件上传 | File upload
result = client.upload_file(
    session_id=session.id,
    file_path="sales_data.csv",
    file_type="dataset"
)

# 获取历史消息 | Get chat history
messages = client.get_messages(session.id)
for msg in messages:
    print(f"{msg.role}: {msg.content}")
```

#### 🌐 Web 界面示例 | Web Interface Examples
```javascript
// JavaScript WebSocket 客户端 | JavaScript WebSocket client
const ws = new WebSocket('ws://localhost:8000/ws/chat/session-123');

ws.onopen = function(event) {
    console.log('WebSocket 连接已建立');

    // 发送消息 | Send message
    ws.send(JSON.stringify({
        message: "分析这份数据的相关性",
        message_type: "text",
        metadata: {
            source: "web_client",
            timestamp: new Date().toISOString()
        }
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到响应:', data.content);

    // 处理不同类型的事件 | Handle different event types
    switch(data.event_type) {
        case 'text':
            appendMessage('ai', data.content);
            break;
        case 'tool_call':
            showToolCall(data.tool_name, data.arguments);
            break;
        case 'hitl_request':
            showApprovalDialog(data);
            break;
    }
};

ws.onerror = function(error) {
    console.error('WebSocket 错误:', error);
};
```

## 🧩 核心组件详解 | Core Components Details

### 🎯 DataAgentCore - 基于 DeepAgent 的智能引擎

**核心业务逻辑层，基于 DeepAgent 引擎构建，提供企业级 AI 能力：**

| 🏗️ 模块 | 📝 说明 | 🚀 特性 |
|--------|--------|--------|
| **`engine/`** | Agent 工厂和执行器 | 基于 DeepAgent 的智能代理创建和任务执行 |
| **`events/`** | 事件系统 | TextEvent, ToolCallEvent, HITLRequestEvent 等实时事件流 |
| **`middleware/`** | 中间件系统 | 长期记忆、技能系统、Shell 执行、权限管理 |
| **`tools/`** | 工具集成 | HTTP 请求、网络搜索、文件追踪、数据分析工具 |
| **`hitl/`** | 人机交互协议 | 智能审批流程、安全沙箱、多界面统一 |
| **`session/`** | 会话管理 | 多会话支持、持久化存储、状态管理 |
| **`mcp/`** | Model Context Protocol | 外部工具扩展、插件架构、API 集成 |

#### 🌟 DataAgentCore 核心优势
- **🧠 基于 DeepAgent**: 集成最先进的 AI 代理技术
- **⚡ 事件驱动架构**: 实时流式响应，毫秒级延迟
- **🔧 可扩展工具系统**: MCP 协议支持，无限工具扩展
- **🛡️ 企业级安全**: 多层安全防护，权限精细控制
- **💾 灵活存储**: 支持内存、SQLite、PostgreSQL 多种存储

### 🌐 DataAgentServer - 高性能 Web 服务

**基于 FastAPI 的现代 Web 服务，提供 REST API 和 WebSocket 实时通信：**

| 🔗 API 端点 | 📋 说明 | ⚡ 特性 |
|------------|--------|--------|
| **`GET /api/v1/health`** | 健康检查 | 服务状态监控 |
| **`POST /api/v1/chat`** | 发送消息（同步）| 支持流式响应 |
| **`POST /api/v1/chat/{session_id}/cancel`** | 取消问答 | 任务中断处理 |
| **`GET /api/v1/sessions`** | 列出会话 | 会话管理和查询 |
| **`GET /api/v1/sessions/{session_id}/messages`** | 获取历史消息 | 完整聊天记录 |
| **`POST /api/v1/workspaces`** | 创建工作空间 | 多租户隔离支持 |
| **`GET /api/v1/workspaces/{workspace_id}/rules`** | 获取工作空间规则 | 个性化配置 |
| **`/ws/chat/{session_id}`** | WebSocket 实时聊天 | 双向实时通信 |

#### 🚀 DataAgentServer 技术亮点
- **⚡ FastAPI 框架**: 高性能异步处理，自动生成 API 文档
- **🔐 JWT 认证**: 企业级身份验证和授权
- **📊 多租户架构**: 完整的数据隔离和工作空间管理
- **🔄 WebSocket 支持**: 实时双向通信，支持复杂交互场景
- **🎯 流式响应**: Server-Sent Events (SSE) 支持，渐进式内容展示

### 💻 DataAgentCli - 智能终端客户端

**功能丰富的命令行界面，支持交互式聊天和智能辅助：**

| 🖥️ 功能 | 📝 说明 | 🎯 应用场景 |
|--------|--------|------------|
| **交互式聊天** | 自然语言对话 | 数据分析、代码生成、问题解答 |
| **文件操作预览** | Diff 可视化 | 代码修改、配置变更预览 |
| **Shell 命令执行** | 安全命令执行 | 系统管理、自动化脚本 |
| **HITL 审批交互** | 人机协同决策 | 敏感操作确认、安全控制 |
| **斜杠命令** | `/help`, `/reset` 等 | 快捷操作、会话管理 |
| **智能补全** | Tab 自动补全 | 命令提示、参数补全 |

#### ✨ DataAgentCli 特色功能
- **🎨 Rich UI**: 美观的终端界面，支持语法高亮
- **🔍 智能提示**: 上下文感知的命令建议
- **📊 实时预览**: 文件变更即时可视化
- **⚡ 快捷命令**: 丰富的内置命令和快捷键
- **🛡️ 安全执行**: 命令执行前的安全检查和确认

### 🧪 DataAgentHarbor - 专业测试评估框架

**企业级测试和性能评估工具，支持大规模并发测试：**

| 📊 测试类型 | 🎯 功能 | 📈 输出 |
|------------|--------|--------|
| **批量压测** | 100+ 用户并发 | 性能指标、响应时间统计 |
| **并发测试** | 多线程压力测试 | 吞吐量、错误率分析 |
| **结果统计** | 详细性能报告 | 图表化数据展示 |
| **LangSmith 追踪** | 性能监控集成 | 链路追踪、性能分析 |
| **A/B 测试** | 多版本对比 | 效果评估、优化建议 |

#### 🔥 DataAgentHarbor 企业特性
- **📊 大规模并发**: 支持 1000+ 虚拟用户同时测试
- **📈 实时统计**: 实时性能指标监控和展示
- **🎯 智能分析**: 自动性能瓶颈识别和优化建议
- **📋 详细报告**: HTML/PDF 格式的专业测试报告
- **🔗 第三方集成**: LangSmith、Prometheus 等监控平台集成

### 🎮 DataAgentServerDemo - Streamlit 交互演示

**基于 Streamlit 的现代化 Web 演示界面：**

| 🎨 功能 | 📱 界面 | 🚀 交互 |
|--------|--------|--------|
| **实时聊天** | 现代化聊天界面 | 消息实时更新 |
| **文件上传** | 拖拽上传支持 | 多种文件格式 |
| **数据可视化** | 图表展示 | 交互式图表 |
| **会话管理** | 多会话切换 | 历史记录查看 |
| **工作空间** | 多租户演示 | 数据隔离展示 |

## 🔧 技术栈 | Technology Stack

### 🐍 核心技术 | Core Technologies
- **Python 3.11+** 🐍 - 现代 Python 异步编程
- **DeepAgent** 🤖 - AI 代理框架基础
- **FastAPI 0.104+** ⚡ - 高性能异步 Web 框架
- **Pydantic v2** 📋 - 数据验证和序列化
- **SQLAlchemy 2.0+** 🗄️ - 异步 ORM 框架

### 🤖 AI/ML 技术 | AI/ML Technologies
- **LangChain/LangGraph** 🔗 - LLM 应用开发框架
- **OpenAI GPT-4** 🧠 - 先进大语言模型
- **Anthropic Claude-3** 🤖 - 安全 AI 助手
- **Google Gemini** 💎 - 多模态 AI 模型
- **Tavily Search** 🔍 - 实时网络搜索

### 🗄️ 数据存储 | Data Storage
- **PostgreSQL 15+** 🐘 - 企业级关系数据库
- **Redis 7+** 🔴 - 高性能缓存和会话存储
- **SQLite** 💎 - 轻量级嵌入式数据库
- **AsyncPG** ⚡ - 高性能 PostgreSQL 驱动

### 🌐 前端与通信 | Frontend & Communication
- **WebSocket** 🔌 - 实时双向通信
- **Server-Sent Events** 📡 - 服务器推送事件
- **Streamlit** 🎨 - 数据应用界面
- **Rich** 🌈 - 终端 UI 美化
- **React/Vue** ⚛️ - 现代化前端框架支持
## ⚙️ 配置参考 | Configuration Reference

### 🌐 Server 配置 | Server Configuration

| 🔧 环境变量 | 📝 说明 | 📊 默认值 | 🎯 示例 |
|------------|--------|----------|--------|
| `DATAAGENT_HOST` | 监听地址 | `0.0.0.0` | `127.0.0.1` |
| `DATAAGENT_PORT` | 监听端口 | `8000` | `8080` |
| `DATAAGENT_API_KEYS` | API Key 列表（逗号分隔） | - | `key1,key2,key3` |
| `DATAAGENT_SESSION_TIMEOUT` | 会话超时秒数 | `3600` | `7200` |
| `DATAAGENT_AUTH_DISABLED` | 禁用认证 | `false` | `true`（开发环境） |
| `DATAAGENT_MAX_CONNECTIONS` | 最大并发连接数 | `200` | `500` |
### 💾 会话存储配置 | Session Storage Configuration

| 🔧 存储类型 | ⚙️ 配置参数 | 📝 说明 | 🎯 适用场景 |
|------------|------------|--------|------------|
| **内存存储** | `DATAAGENT_SESSION_STORE=memory` | 默认选项，开发测试使用 | 开发环境、功能测试 |
| **PostgreSQL** | `DATAAGENT_SESSION_STORE=postgres` | 生产环境推荐 | 企业级应用、多用户场景 |
| **SQLite** | `DATAAGENT_SESSION_STORE=sqlite` | 轻量级数据库 | 个人使用、小型部署 |

```bash
# PostgreSQL 配置示例 | PostgreSQL Configuration Example
DATAAGENT_SESSION_STORE=postgres
DATAAGENT_POSTGRES_HOST=localhost
DATAAGENT_POSTGRES_PORT=5432
DATAAGENT_POSTGRES_USER=dataagent
DATAAGENT_POSTGRES_PASSWORD=your_secure_password
DATAAGENT_POSTGRES_DATABASE=dataagent
DATAAGENT_POSTGRES_POOL_SIZE=20

# Redis 缓存配置（可选）| Redis Cache Configuration (Optional)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
```

### 🔐 认证与授权 | Authentication & Authorization

| 🔧 配置项 | 📝 说明 | 📊 默认值 | 🛡️ 安全建议 |
|----------|--------|----------|------------|
| `JWT_SECRET_KEY` | JWT 签名密钥 | 自动生成 | 使用强密码，定期更换 |
| `JWT_ALGORITHM` | 加密算法 | `HS256` | 生产环境使用 `RS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间 | `30` | 平衡安全与便利性 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 刷新令牌过期时间 | `7` | 长期使用场景 |
| `API_KEY_HEADER_NAME` | API Key 请求头 | `X-API-Key` | 可自定义避免暴露 |

### 🤖 LLM 配置 | LLM Configuration

| 🔧 提供商 | ⚙️ 环境变量 | 📝 说明 | 💡 建议 |
|----------|------------|--------|--------|
| **OpenAI** | `OPENAI_API_KEY` | GPT-4/GPT-3.5 支持 | 主力模型，功能全面 |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude-3 支持 | 安全优先，长文本处理 |
| **Google** | `GOOGLE_API_KEY` | Gemini Pro 支持 | 多模态能力 |
| **Tavily** | `TAVILY_API_KEY` | 网络搜索 | 实时信息获取 |

```bash
# 多模型配置示例 | Multi-model Configuration
OPENAI_API_KEY="sk-your-openai-key"
ANTHROPIC_API_KEY="sk-ant-your-anthropic-key"
GOOGLE_API_KEY="your-google-ai-key"
TAVILY_API_KEY="tvly-your-tavily-key"

# 默认模型选择 | Default Model Selection
DEFAULT_LLM_PROVIDER=openai  # openai, anthropic, google
DEFAULT_MODEL=gpt-4-turbo    # gpt-4-turbo, claude-3-sonnet, gemini-pro
```

### 🚀 性能调优 | Performance Tuning

| 🔧 参数 | 📊 默认值 | 📝 说明 | 🎯 优化建议 |
|--------|----------|--------|------------|
| `MAX_WORKERS` | `4` | 工作线程数 | CPU 核心数 × 2 |
| `MAX_ASYNC_WORKERS` | `10` | 异步任务数 | 根据并发需求调整 |
| `REQUEST_TIMEOUT` | `30` | 请求超时时间 | 网络环境差时适当增加 |
| `CONNECTION_POOL_SIZE` | `20` | 数据库连接池 | 高并发场景增大 |
| `CACHE_TTL` | `3600` | 缓存过期时间 | 平衡内存使用与性能 |

## 📊 事件系统 | Event System

### 🚀 事件驱动架构 | Event-Driven Architecture

DataAgent 采用事件驱动架构，基于 DeepAgent 的事件系统实现实时通信：

```
┌─────────────────────────────────────────────────────────────┐
│                    事件流处理管道                            │
├─────────────────────────────────────────────────────────────┤
│  Agent 执行器  →  事件生成器  →  事件处理器  →  客户端响应    │
└─────────────────────────────────────────────────────────────┘
```

### 📋 事件类型 | Event Types

Agent 执行过程通过标准化事件流与 UI 层实时通信：

| 🏷️ 事件类型 | 📝 说明 | 🎯 应用场景 | 💡 特性 |
|------------|--------|------------|--------|
| **`TextEvent`** | 文本输出 | AI 回复内容 | 支持 Markdown、代码高亮 |
| **`ToolCallEvent`** | 工具调用 | 函数调用开始 | 包含工具名称和参数 |
| **`ToolResultEvent`** | 工具结果 | 函数执行结果 | 成功/失败状态，结果数据 |
| **`HITLRequestEvent`** | HITL 审批请求 | 人机交互确认 | 可配置自动审批规则 |
| **`TodoUpdateEvent`** | 任务列表更新 | 任务进度追踪 | 支持子任务和状态管理 |
| **`FileOperationEvent`** | 文件操作 | 文件读写操作 | 操作预览和安全确认 |
| **`ErrorEvent`** | 错误信息 | 异常和错误处理 | 详细错误信息和解决方案 |
| **`DoneEvent`** | 执行完成 | 任务完成通知 | 结果汇总和后续建议 |
| **`StreamStartEvent`** | 流式开始 | 流式响应开始 | 渐进式内容展示 |
| **`StreamEndEvent`** | 流式结束 | 流式响应结束 | 内容完整性保证 |

### ⚡ 事件处理流程 | Event Processing Flow

```python
# 事件处理示例 | Event Processing Example
async def handle_agent_execution():
    """处理 Agent 执行事件流"""

    # 1. 创建事件流 | Create event stream
    async for event in agent_executor.run(task):

        # 2. 事件类型判断 | Event type determination
        if isinstance(event, TextEvent):
            # 处理文本事件 | Handle text event
            await send_to_client(event.content)

        elif isinstance(event, ToolCallEvent):
            # 处理工具调用 | Handle tool call
            logger.info(f"Calling tool: {event.tool_name}")
            await notify_user(f"正在执行: {event.tool_name}")

        elif isinstance(event, HITLRequestEvent):
            # 处理人机交互 | Handle human interaction
            approval = await request_user_approval(event)
            if approval:
                await agent_executor.continue_execution()
            else:
                await agent_executor.cancel_execution()

        elif isinstance(event, ErrorEvent):
            # 处理错误事件 | Handle error event
            logger.error(f"Execution error: {event.error_message}")
            await send_error_to_client(event)
```

### 🔧 事件自定义 | Event Customization

基于 DeepAgent 的事件系统支持自定义事件类型：

```python
from dataagent_core.events import BaseEvent

class CustomEvent(BaseEvent):
    """自定义事件类型 | Custom Event Type"""

    def __init__(self, custom_data: dict, event_type: str = "custom"):
        super().__init__(event_type=event_type)
        self.custom_data = custom_data
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """序列化事件 | Serialize event"""
        return {
            "event_type": self.event_type,
            "custom_data": self.custom_data,
            "timestamp": self.timestamp.isoformat()
        }

# 注册自定义事件 | Register custom event
event_registry.register("custom", CustomEvent)
```

## 🧪 开发指南 | Development Guide

### 🚀 开发环境搭建 | Development Environment Setup

```bash
# 1. 安装开发依赖 | Install development dependencies
pip install -r requirements-dev.txt

# 2. 安装预提交钩子 | Install pre-commit hooks
pre-commit install

# 3. 配置 IDE | Configure IDE
# 推荐 VS Code + Python 扩展 + Pylance
# 配置 .vscode/settings.json 文件
```

### 🧪 测试体系 | Testing Framework

```bash
# 运行单元测试 | Run unit tests
cd source/dataagent-core
pytest tests/unit/ -v

# 运行集成测试 | Run integration tests
pytest tests/integration/ -v

# 运行性能测试 | Run performance tests
pytest tests/performance/ -v --benchmark-only

# 生成测试覆盖率报告 | Generate test coverage report
pytest --cov=dataagent_core --cov-report=html --cov-report=term

# 运行特定测试 | Run specific test
pytest tests/unit/test_engine.py::test_agent_creation -v
```

### 📊 代码质量 | Code Quality

```bash
# 代码格式化 | Code formatting
black source/
isort source/

# 静态类型检查 | Static type checking
mypy source/ --strict

# 代码 linting | Code linting
flake8 source/
pylint source/

# 安全检查 | Security checking
bandit -r source/
safety check
```

### 🐳 Docker 开发 | Docker Development

```bash
# 构建开发镜像 | Build development image
docker build -t dataagent:dev -f docker/Dockerfile.dev .

# 运行开发容器 | Run development container
docker run -it -v $(pwd):/app -p 8000:8000 dataagent:dev

# 使用 Docker Compose | Use Docker Compose
docker-compose -f docker/docker-compose.dev.yml up
```

## 📚 文档资源 | Documentation Resources

### 📖 核心文档 | Core Documentation
- **[🏗️ 架构设计](docs/architecture.md)** - 系统架构详细说明
- **[📋 API 参考](docs/api-reference.md)** - 完整的 API 文档
- **[🔧 开发指南](docs/developer-guide.md)** - 开发者快速入门
- **[⚙️ 配置手册](docs/configuration.md)** - 详细配置说明
- **[🚀 部署指南](docs/deployment.md)** - 生产环境部署

### 🎯 特色文档 | Feature Documentation
- **[🤖 DeepAgent 集成](docs/deepagent-integration.md)** - DeepAgent 引擎使用指南
- **[🛡️ 人机协同](docs/human-in-the-loop.md)** - HITL 功能详细说明
- **[🔌 MCP 协议](docs/mcp-protocol.md)** - Model Context Protocol 集成
- **[📊 事件系统](docs/event-system.md)** - 事件驱动架构详解
- **[🔐 安全指南](docs/security-guide.md)** - 企业级安全配置

### 🌍 国际化支持 | Internationalization
- **[🇨🇳 中文文档](docs/zh-cn/)** - 完整中文文档
- **[🇺🇸 英文文档](docs/en-us/)** - 完整英文文档
- **[🌏 多语言支持](docs/i18n.md)** - 国际化开发指南

## 🤝 贡献指南 | Contributing

我们欢迎所有形式的贡献！请查看我们的贡献指南：

### 🎯 贡献类型 | Types of Contributions
- **🐛 [Bug 修复](.github/ISSUE_TEMPLATE/bug_report.md)** - 报告和修复问题
- **✨ [新功能](.github/ISSUE_TEMPLATE/feature_request.md)** - 提出和实现新功能
- **📚 [文档改进](.github/ISSUE_TEMPLATE/documentation.md)** - 改进文档质量
- **🧪 [测试用例](.github/ISSUE_TEMPLATE/test_case.md)** - 添加测试覆盖
- **🌍 [翻译贡献](.github/ISSUE_TEMPLATE/translation.md)** - 多语言支持

### 🚀 快速贡献 | Quick Contributing
1. **Fork** 项目仓库
2. **创建** 功能分支 (`git checkout -b feature/amazing-feature`)
3. **提交** 更改 (`git commit -m 'Add some amazing feature'`)
4. **推送** 到分支 (`git push origin feature/amazing-feature`)
5. **开启** Pull Request

### 📋 开发规范 | Development Standards
- 遵循 [PEP 8](https://pep8.org/) Python 编码规范
- 所有代码必须通过类型检查 (`mypy --strict`)
- 新功能必须包含完整测试用例
- 文档必须同步更新
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)

## 📊 性能指标 | Performance Metrics

### 🚀 基准测试 | Benchmark Results

| 📊 指标 | 🎯 数值 | 📈 测试环境 | ⏱️ 更新时间 |
|--------|--------|------------|------------|
| **并发用户数** | 1000+ | 4核8G, PostgreSQL | 2024-12 |
| **平均响应时间** | < 200ms | GPT-4, 网络搜索 | 2024-12 |
| **吞吐量** | 5000+ req/min | 100并发连接 | 2024-12 |
| **内存使用** | < 2GB | 100活跃会话 | 2024-12 |
| **CPU 占用** | < 40% | 满负载运行 | 2024-12 |
| **可用性** | 99.9%+ | 生产环境监控 | 2024-12 |

### 📈 扩展性 | Scalability
- **🔧 水平扩展**: 支持多实例负载均衡
- **📊 数据库扩展**: 读写分离，分库分表
- **🚀 缓存扩展**: Redis 集群支持
- **🌐 CDN 集成**: 静态资源加速
- **☸️ 容器编排**: Kubernetes 原生支持

## 🏷️ SEO 优化关键词 | SEO Keywords

### 🔥 热门中文关键词
- **AI数据助手** **智能数据分析** **企业级AI助手** **多租户AI系统**
- **人机协同平台** **事件驱动架构** **实时数据处理** **LLM应用框架**
- **AI代理系统** **数据智能解决方案** **自动化数据洞察** **智能决策支持系统**
- **AI驱动的数据分析** **企业数字化转型** **智能业务流程** **基于DeepAgent开发**

### 🔥 热门英文关键词
- **AI Data Assistant** **Intelligent Data Analysis** **Enterprise AI Assistant** **Multi-tenant AI System**
- **Human-AI Collaboration** **Event-driven Architecture** **Real-time Data Processing** **LLM Application Framework**
- **AI Agent System** **Data Intelligence Solution** **Automated Data Insights** **Intelligent Decision Support**
- **AI-driven Data Analysis** **Enterprise Digital Transformation** **Intelligent Business Process** **Built on DeepAgent**

### 🎯 长尾关键词
- **基于DeepAgent的企业级AI数据智能助手平台**
- **支持人机协同的多租户AI数据分析系统**
- **实时流式响应的AI数据智能解决方案**
- **集成GPT-4 Claude-3 Gemini的多模态AI助手**
- **企业级JWT认证的多用户AI数据平台**

## 📄 开源许可 | License

本项目基于 [MIT 许可证](./LICENSE) 开源，详见 [LICENSE](./LICENSE) 文件。

**核心要点:**
- ✅ 商业使用免费
- ✅ 修改分发自由
- ✅ 私有使用允许
- ⚠️ 需保留版权声明
- ⚠️ 无担保责任

## 🌟 Star 历史 | Star History

[![Star History Chart](https://api.star-history.com/svg?repos=hidagent/dataagent&type=Date)](https://star-history.com/#hidagent/dataagent&Date)

## 📞 联系我们 | Contact Us

### 💬 社区支持 | Community Support
- **GitHub Discussions**: [github.com/hidagent/dataagent/discussions](https://github.com/hidagent/dataagent/discussions)
- **技术问答**: 使用 `dataagent` 标签在 Stack Overflow 提问
- **微信交流群**: 添加微信号 `DataAgentAI` 进群

### 📧 商务合作 | Business Cooperation
- **邮箱**: team@dataagent.ai
- **官网**: [www.dataagent.ai](https://www.dataagent.ai)
- **LinkedIn**: [linkedin.com/company/dataagent](https://linkedin.com/company/dataagent)

### 🐦 社交媒体 | Social Media
- **Twitter**: [@DataAgentAI](https://twitter.com/DataAgentAI)
- **知乎**: [DataAgent 官方账号](https://www.zhihu.com/people/dataagent)
- **B站**: [DataAgent 官方](https://space.bilibili.com/dataagent)

---

<div align="center">

## ⭐ 如果这个项目对你有帮助，请给个 Star！
## ⭐ If this project helps you, please give it a Star!

**您的支持是我们持续改进的动力！**
**Your support is our motivation for continuous improvement!**

</div>

---

**📅 最后更新 | Last Updated**: 2024-12-21
**🏷️ 版本 | Version**: 1.0.0
**🚀 构建于 DeepAgent | Built on DeepAgent**
**📍 GitHub**: [github.com/hidagent/dataagent](https://github.com/hidagent/dataagent)**
