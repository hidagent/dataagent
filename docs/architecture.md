# 架构概览

## 系统架构

DataAgent 采用三层架构设计：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DataAgent 架构                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐         ┌─────────────────────────────────────────┐  │
│   │  DataAgentCli   │         │           DataAgentServer               │  │
│   │   (终端交互)     │         │            (FastAPI)                    │  │
│   │                 │         │                                         │  │
│   │  ┌───────────┐  │         │  ┌─────────────┐   ┌─────────────────┐ │  │
│   │  │ Terminal  │  │         │  │  REST API   │   │    WebSocket    │ │  │
│   │  │   HITL    │  │         │  │  /api/v1/*  │   │   /ws/chat/*    │ │  │
│   │  └───────────┘  │         │  └──────┬──────┘   └────────┬────────┘ │  │
│   └────────┬────────┘         └─────────┼───────────────────┼──────────┘  │
│            │                            │                   │             │
│            │                            ▼                   ▼             │
│            │         ┌──────────────────────────────────────────────────┐ │
│            │         │              Event Stream                        │ │
│            │         │    AsyncIterator[ExecutionEvent]                 │ │
│            │         └──────────────────────────────────────────────────┘ │
│            │                            ▲                                 │
│            │                            │                                 │
│            ▼                            ▼                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                         DataAgentCore                                │ │
│   │                                                                      │ │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│   │  │ AgentFactory │  │AgentExecutor │  │    Events    │              │ │
│   │  │  (创建Agent)  │  │  (执行任务)   │  │   (事件流)   │              │ │
│   │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│   │                                                                      │ │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│   │  │  Middleware  │  │    Tools     │  │     HITL     │              │ │
│   │  │   (中间件)    │  │   (工具)     │  │   (人机交互)  │              │ │
│   │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 核心组件

### DataAgentCore

核心业务逻辑层，提供：

| 模块 | 说明 |
|------|------|
| `engine/` | Agent 工厂和执行器 |
| `events/` | 事件系统 (TextEvent, ToolCallEvent, etc.) |
| `middleware/` | 中间件 (Memory, Skills, Shell) |
| `tools/` | 工具系统 (HTTP, Web Search, File Tracker) |
| `hitl/` | HITL 协议定义 |
| `session/` | 会话管理和存储 |
| `config/` | 配置管理 |

### DataAgentCli

终端客户端层，提供：

| 模块 | 说明 |
|------|------|
| `renderer.py` | 终端渲染 (Rich) |
| `hitl.py` | 终端 HITL 处理 |
| `main.py` | CLI 入口 |

### DataAgentServer

Web 服务层，提供：

| 模块 | 说明 |
|------|------|
| `api/v1/` | REST API 路由 |
| `ws/` | WebSocket 处理 |
| `auth/` | API Key 认证 |
| `models/` | Pydantic 数据模型 |

## 核心设计原则

### 1. 事件驱动

Agent 执行过程通过事件流与 UI 层通信：

```python
async for event in executor.execute(message, session_id):
    # TextEvent - 文本输出
    # ToolCallEvent - 工具调用
    # ToolResultEvent - 工具结果
    # HITLRequestEvent - HITL 请求
    # DoneEvent - 执行完成
    await render(event)
```

### 2. HITL 协议抽象

敏感操作需要用户审批，通过协议定义支持不同实现：

```python
class HITLHandler(Protocol):
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        ...
```

- CLI: `TerminalHITLHandler` - 终端交互审批
- Server: `WebSocketHITLHandler` - WebSocket 推送审批

### 3. 关注点分离

- Core 层不依赖任何 UI 实现
- CLI 和 Server 只负责 UI 交互和事件渲染
- 依赖关系：CLI/Server → Core

## 数据流

### CLI 数据流

```
用户输入 → DataAgentCli → DataAgentCore → LLM
                ↓              ↓           ↓
           终端渲染 ← Events ← Execution ← Tool Calls
```

### Server 数据流

```
WebSocket → DataAgentServer → DataAgentCore → LLM
    ↓             ↓               ↓           ↓
  前端渲染 ← Events Push ← Execution ← Tool Calls
```

## 会话存储

支持多种存储后端：

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| Memory | 内存存储 | 开发测试 |
| MySQL | 数据库存储 | 生产环境 |

配置方式：

```bash
# 内存存储 (默认)
DATAAGENT_SESSION_STORE=memory

# MySQL 存储
DATAAGENT_SESSION_STORE=mysql
DATAAGENT_MYSQL_HOST=localhost
DATAAGENT_MYSQL_DATABASE=dataagent
```

## 详细设计

更多设计细节请参考：
- `.kiro/specs/dataagent-development-specs/design.md`
