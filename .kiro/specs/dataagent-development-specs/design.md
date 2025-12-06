# Design Document: DataAgent Development Specs

## Overview

本设计文档定义了 DataAgent 平台的技术架构和实现规范，为后续的通用编码 Agent 提供统一的开发标准。

DataAgent 采用三层架构：
- **DataAgentCore**: 核心业务逻辑层，提供 Agent 引擎、事件系统、中间件、工具系统等
- **DataAgentCli**: 终端客户端层，提供命令行交互界面
- **DataAgentServer**: Web 服务层，提供 REST API 和 WebSocket 接口

核心设计原则：
1. **关注点分离**: Core 层不依赖任何 UI 实现，CLI 和 Server 只负责 UI 交互
2. **事件驱动**: Agent 执行通过事件流与 UI 层通信，实现解耦
3. **协议抽象**: HITL 通过协议定义，支持不同的实现（终端、Web）
4. **可扩展性**: 中间件和工具系统支持灵活扩展

## Architecture

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
│   │                                                                      │ │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│   │  │   Session    │  │   Config     │  │    Utils     │              │ │
│   │  │   (会话)     │  │   (配置)     │  │   (工具函数)  │              │ │
│   │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                      External Dependencies                           │ │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│   │  │deepagents│  │LangChain │  │LangGraph │  │ Sandbox  │            │ │
│   │  │  (core)  │  │          │  │          │  │Providers │            │ │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. 事件系统 (Events)

事件系统是 Core 与 UI 层通信的核心机制。所有 Agent 执行过程中的状态变化都通过事件流传递。

```python
# 事件基类
@dataclass
class ExecutionEvent:
    event_type: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            **self._extra_fields(),
        }

# 事件类型
TextEvent          # 文本输出
ToolCallEvent      # 工具调用
ToolResultEvent    # 工具结果
HITLRequestEvent   # HITL 请求
TodoUpdateEvent    # Todo 更新
FileOperationEvent # 文件操作
ErrorEvent         # 错误
DoneEvent          # 完成
```

### 2. HITL 协议 (Human-In-The-Loop)

HITL 协议定义了敏感操作的用户审批机制。

```python
class HITLHandler(Protocol):
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """请求用户审批"""
        ...

class ActionRequest(TypedDict):
    name: str           # 操作名称
    args: dict          # 操作参数
    description: str    # 操作描述

class Decision(TypedDict):
    type: str           # approve / reject
    message: str | None # 可选消息
```

### 3. Agent 工厂 (AgentFactory)

Agent 工厂负责创建和配置 Agent 实例。

```python
@dataclass
class AgentConfig:
    assistant_id: str
    model: str | BaseChatModel | None = None
    enable_memory: bool = True
    enable_skills: bool = True
    enable_shell: bool = True
    auto_approve: bool = False
    sandbox_type: str | None = None
    system_prompt: str | None = None
    extra_tools: list[BaseTool] = field(default_factory=list)
    extra_middleware: list[AgentMiddleware] = field(default_factory=list)

class AgentFactory:
    def create_agent(self, config: AgentConfig) -> tuple[Pregel, CompositeBackend]:
        """创建配置好的 Agent"""
        ...
```

### 4. 执行器 (AgentExecutor)

执行器负责运行 Agent 并产生事件流。

```python
class AgentExecutor:
    async def execute(
        self,
        user_input: str,
        session_id: str,
        context: dict | None = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """执行用户请求，返回事件流"""
        ...
```

### 5. 中间件系统 (Middleware)

中间件用于扩展 Agent 功能。

```python
# 内置中间件
AgentMemoryMiddleware  # 长期记忆
SkillsMiddleware       # 技能系统
ShellMiddleware        # Shell 执行
```

### 6. 工具系统 (Tools)

工具系统提供 Agent 可调用的能力。

```python
# 内置工具
http_request  # HTTP 请求
fetch_url     # 获取 URL 内容
web_search    # Web 搜索 (需要 TAVILY_API_KEY)

# 文件操作追踪
class FileOpTracker:
    def start_operation(self, tool_name: str, args: dict, tool_call_id: str) -> None
    def complete_with_message(self, message: ToolMessage) -> FileOpRecord | None
```

### 7. 会话管理 (Session)

会话管理负责维护用户交互状态。

```python
@dataclass
class Session:
    session_id: str
    user_id: str
    assistant_id: str
    created_at: datetime
    last_active: datetime
    state: dict
    metadata: dict

class SessionStore(ABC):
    async def create(self, user_id: str, assistant_id: str) -> Session
    async def get(self, session_id: str) -> Session | None
    async def update(self, session: Session) -> None
    async def delete(self, session_id: str) -> None
    async def list_by_user(self, user_id: str) -> list[Session]

class SessionManager:
    async def get_or_create_session(self, user_id: str, assistant_id: str, session_id: str | None = None) -> Session
    async def get_executor(self, session: Session, config: AgentConfig, hitl_handler: HITLHandler | None = None) -> AgentExecutor
```

## Data Models

### 事件数据模型

```python
# 文本事件
TextEvent:
    event_type: "text"
    timestamp: float
    content: str
    is_final: bool

# 工具调用事件
ToolCallEvent:
    event_type: "tool_call"
    timestamp: float
    tool_name: str
    tool_args: dict
    tool_call_id: str

# 工具结果事件
ToolResultEvent:
    event_type: "tool_result"
    timestamp: float
    tool_call_id: str
    result: Any
    status: str  # success / error

# 文件操作事件
FileOperationEvent:
    event_type: "file_operation"
    timestamp: float
    operation: str  # read / write / edit
    file_path: str
    metrics: dict   # lines_read, lines_written, lines_added, lines_removed
    diff: str | None
    status: str

# 错误事件
ErrorEvent:
    event_type: "error"
    timestamp: float
    error: str
    recoverable: bool

# 完成事件
DoneEvent:
    event_type: "done"
    timestamp: float
    token_usage: dict | None
    cancelled: bool
```

### 配置数据模型

```python
# Agent 配置
AgentConfig:
    assistant_id: str
    model: str | BaseChatModel | None
    enable_memory: bool
    enable_skills: bool
    enable_shell: bool
    auto_approve: bool
    sandbox_type: str | None
    system_prompt: str | None
    extra_tools: list[BaseTool]
    extra_middleware: list[AgentMiddleware]
    recursion_limit: int
    timeout: float | None

# 会话状态
SessionState:
    thread_id: str
    auto_approve: bool
    current_todos: list
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 事件序列化往返一致性
*For any* ExecutionEvent 实例, 调用 to_dict() 序列化后再反序列化应该能够重建等价的事件对象
**Validates: Requirements 14.5**

### Property 2: 事件必须包含基础字段
*For any* ExecutionEvent 实例, 序列化结果必须包含 event_type 和 timestamp 字段
**Validates: Requirements 2.6, 14.3**

### Property 3: 事件序列化结果是有效 JSON
*For any* ExecutionEvent 实例, to_dict() 的结果必须能够被 json.dumps() 成功序列化
**Validates: Requirements 14.2**

### Property 4: TextEvent 包含必需字段
*For any* 文本内容, 创建的 TextEvent 必须包含 content 和 is_final 字段
**Validates: Requirements 2.2**

### Property 5: ToolCallEvent 包含必需字段
*For any* 工具调用, 创建的 ToolCallEvent 必须包含 tool_name、tool_args、tool_call_id 字段
**Validates: Requirements 2.3**

### Property 6: ToolResultEvent 包含必需字段
*For any* 工具结果, 创建的 ToolResultEvent 必须包含 tool_call_id、result、status 字段
**Validates: Requirements 2.4**

### Property 7: HITL 拒绝导致执行取消
*For any* HITL 请求, 当用户返回 Decision(type="reject") 时, 执行器必须发出 DoneEvent(cancelled=True)
**Validates: Requirements 3.4, 5.5**

### Property 8: 无 HITLHandler 时自动批准
*For any* HITL 请求, 当未配置 HITLHandler 时, 系统必须自动批准所有操作
**Validates: Requirements 3.5**

### Property 9: AgentFactory 返回正确的元组
*For any* AgentConfig, AgentFactory.create_agent() 必须返回 (Pregel, CompositeBackend) 元组
**Validates: Requirements 4.2**

### Property 10: 启用 memory 时添加 MemoryMiddleware
*For any* AgentConfig 其中 enable_memory=True, 创建的 Agent 必须包含 AgentMemoryMiddleware
**Validates: Requirements 4.4**

### Property 11: 启用 skills 时添加 SkillsMiddleware
*For any* AgentConfig 其中 enable_skills=True, 创建的 Agent 必须包含 SkillsMiddleware
**Validates: Requirements 4.5**

### Property 12: 执行器返回事件迭代器
*For any* 用户输入, AgentExecutor.execute() 必须返回 AsyncIterator[ExecutionEvent]
**Validates: Requirements 5.1**

### Property 13: 异常转换为 ErrorEvent
*For any* 执行过程中的异常, 执行器必须捕获并转换为 ErrorEvent, 而非抛出异常
**Validates: Requirements 5.3, 11.1**

### Property 14: 正常完成发出 DoneEvent
*For any* 正常完成的执行, 执行器必须发出 DoneEvent(cancelled=False)
**Validates: Requirements 5.4**

### Property 15: 文件操作被追踪
*For any* 文件操作 (read_file, write_file, edit_file), FileOpTracker 必须追踪并发出 FileOperationEvent
**Validates: Requirements 5.6, 8.2**

### Property 16: Settings 从环境变量加载
*For any* 环境变量配置, Settings 必须正确加载 API keys
**Validates: Requirements 6.1**

### Property 17: ensure_agent_dir 创建目录
*For any* assistant_id, Settings.ensure_agent_dir() 必须创建对应的目录
**Validates: Requirements 6.3**

### Property 18: 未设置环境变量时使用默认值
*For any* 未设置的环境变量, Settings 必须使用合理的默认值
**Validates: Requirements 6.4**

### Property 19: 自定义中间件被注入
*For any* AgentConfig.extra_middleware, 创建的 Agent 必须包含这些中间件
**Validates: Requirements 7.5**

### Property 20: 自定义工具被注入
*For any* AgentConfig.extra_tools, 创建的 Agent 必须包含这些工具
**Validates: Requirements 8.3**

### Property 21: 会话超时自动清理
*For any* 超时的会话, SessionManager 必须自动清理会话资源
**Validates: Requirements 13.4**

### Property 22: 模块依赖单向性
*For any* 模块导入, DataAgentCli 和 DataAgentServer 可以导入 DataAgentCore, 但 DataAgentCore 不能导入 CLI 或 Server
**Validates: Requirements 1.5**

---

## DataAgentServer 设计

### Server Overview

DataAgentServer 是 DataAgent 平台的 Web 服务层，通过 FastAPI 提供 REST API 和 WebSocket 接口，支持 Web 客户端与 Agent 的交互。

核心功能：
- REST API：提供同步聊天、会话管理、Agent 管理等接口
- WebSocket：提供实时流式聊天和 HITL 交互
- 认证授权：支持 API Key 认证
- 配置管理：支持环境变量和命令行配置

### Server Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DataAgentServer 架构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        FastAPI Application                           │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────┐   ┌─────────────────────────────────┐  │  │
│   │  │      REST API           │   │         WebSocket               │  │  │
│   │  │    /api/v1/*            │   │        /ws/chat/*               │  │  │
│   │  │                         │   │                                 │  │  │
│   │  │  ┌─────────────────┐   │   │  ┌─────────────────────────┐   │  │  │
│   │  │  │ /chat           │   │   │  │ ConnectionManager       │   │  │  │
│   │  │  │ /sessions       │   │   │  │ WebSocketChatHandler    │   │  │  │
│   │  │  │ /agents         │   │   │  │ WebSocketHITLHandler    │   │  │  │
│   │  │  │ /health         │   │   │  └─────────────────────────┘   │  │  │
│   │  │  └─────────────────┘   │   │                                 │  │  │
│   │  └─────────────────────────┘   └─────────────────────────────────┘  │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │                     Middleware Layer                         │   │  │
│   │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │  │
│   │  │  │  CORS    │  │   Auth   │  │ Logging  │  │RequestID │    │   │  │
│   │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         DataAgentCore                                │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│   │  │SessionManager│  │AgentExecutor │  │    Events    │              │  │
│   │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Server Directory Structure

```
libs/dataagent-server/
├── pyproject.toml
├── README.md
├── dataagent_server/
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   │
│   ├── api/                      # REST API
│   │   ├── __init__.py
│   │   ├── deps.py               # 依赖注入
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat.py           # 聊天 API
│   │       ├── sessions.py       # 会话管理
│   │       ├── agents.py         # Agent 管理
│   │       └── health.py         # 健康检查
│   │
│   ├── ws/                       # WebSocket
│   │   ├── __init__.py
│   │   ├── manager.py            # 连接管理
│   │   └── handlers.py           # 消息处理
│   │
│   ├── hitl/                     # HITL 实现
│   │   ├── __init__.py
│   │   └── websocket_handler.py
│   │
│   ├── models/                   # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── session.py
│   │   └── common.py
│   │
│   ├── auth/                     # 认证
│   │   ├── __init__.py
│   │   └── api_key.py
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_api/
    ├── test_ws/
    └── test_models/
```

### Server Components and Interfaces

#### 1. REST API 路由

```python
# API 端点定义
POST /api/v1/chat              # 发送消息（同步）
GET  /api/v1/sessions          # 列出用户会话
GET  /api/v1/sessions/{id}     # 获取会话详情
DELETE /api/v1/sessions/{id}   # 删除会话
GET  /api/v1/agents            # 列出可用 Agent
GET  /api/v1/health            # 健康检查
```

#### 2. WebSocket 协议

```python
# WebSocket 端点
/ws/chat/{session_id}

# 客户端消息格式
{
    "type": "chat" | "hitl_decision" | "cancel" | "ping",
    "payload": {...}
}

# 服务端消息格式
{
    "event_type": "text" | "tool_call" | "tool_result" | "hitl_request" | "done" | ...,
    "data": {...},
    "timestamp": float
}
```

#### 3. 连接管理器

```python
class ConnectionManager:
    """WebSocket 连接管理器"""
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None
    def disconnect(self, session_id: str) -> None
    async def send_event(self, session_id: str, event: ExecutionEvent) -> None
    async def wait_for_decision(self, session_id: str, timeout: float) -> dict | None
    def resolve_decision(self, session_id: str, decision: dict) -> None
```

#### 4. WebSocket HITL 处理器

```python
class WebSocketHITLHandler(HITLHandler):
    """WebSocket HITL 处理器"""
    
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision
```

#### 5. 认证中间件

```python
class APIKeyAuth:
    """API Key 认证"""
    
    def __init__(self, api_keys: list[str], disabled: bool = False)
    async def __call__(self, request: Request) -> str | None
```

### Server Data Models

```python
# 聊天请求
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    assistant_id: str | None = None

# 聊天响应
class ChatResponse(BaseModel):
    session_id: str
    events: list[dict]

# 会话信息
class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    assistant_id: str
    created_at: datetime
    last_active: datetime

# 错误响应
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict | None = None

# WebSocket 消息
class WebSocketMessage(BaseModel):
    type: str
    payload: dict
```

### Server Configuration

```python
class ServerSettings(BaseSettings):
    """服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    api_keys: list[str] = []
    cors_origins: list[str] = ["*"]
    session_timeout: int = 3600
    auth_disabled: bool = False
    max_connections: int = 200  # 最大并发连接数
    
    model_config = SettingsConfigDict(
        env_prefix="DATAAGENT_",
        env_file=".env",
    )
```

### High Concurrency Design

为支持 100+ 用户同时问答，采用以下设计策略：

#### 1. 异步非阻塞架构

```python
# 所有 I/O 操作使用 async/await
async def handle_chat(self, session_id: str, message: str):
    # 异步执行，不阻塞其他请求
    async for event in executor.execute(message, session_id):
        await self.connections.send_event(session_id, event)
```

#### 2. 连接管理器线程安全设计

```python
import asyncio
from collections.abc import MutableMapping

class ConnectionManager:
    """线程安全的 WebSocket 连接管理器"""
    
    def __init__(self, max_connections: int = 200):
        self._connections: dict[str, WebSocket] = {}
        self._pending_decisions: dict[str, asyncio.Future] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}  # 用于取消
        self._lock = asyncio.Lock()
        self._max_connections = max_connections
    
    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """建立连接，返回是否成功"""
        async with self._lock:
            if len(self._connections) >= self._max_connections:
                return False  # 连接数已满
            await websocket.accept()
            self._connections[session_id] = websocket
            return True
```

#### 3. 多进程部署

```bash
# 使用 uvicorn 多 worker 模式
uvicorn dataagent_server.main:app --workers 4 --host 0.0.0.0 --port 8000
```

#### 4. 负载过高保护

```python
from fastapi import HTTPException, status

async def check_capacity(self):
    """检查系统容量"""
    if len(self._connections) >= self._max_connections:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable, please try again later"
        )
```

### Chat Cancellation Design

支持用户随时终止正在进行的问答：

#### 1. WebSocket 取消协议

```python
# 客户端发送取消消息
{
    "type": "cancel",
    "payload": {
        "session_id": "xxx"
    }
}

# 服务端响应
{
    "event_type": "done",
    "data": {
        "cancelled": true,
        "reason": "user_cancelled"
    },
    "timestamp": 1234567890.123
}
```

#### 2. 任务取消机制

```python
class ConnectionManager:
    async def start_task(self, session_id: str, coro) -> asyncio.Task:
        """启动可取消的任务"""
        task = asyncio.create_task(coro)
        async with self._lock:
            self._active_tasks[session_id] = task
        return task
    
    async def cancel_task(self, session_id: str) -> bool:
        """取消正在执行的任务"""
        async with self._lock:
            task = self._active_tasks.get(session_id)
            if task and not task.done():
                task.cancel()
                return True
            return False
```

#### 3. REST API 取消端点

```python
@router.post("/{session_id}/cancel")
async def cancel_chat(
    session_id: str,
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """终止正在进行的问答"""
    cancelled = await connection_manager.cancel_task(session_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active chat found for this session"
        )
    return {"status": "cancelled", "session_id": session_id}
```

#### 4. 执行器取消支持

```python
class AgentExecutor:
    async def execute(
        self,
        user_input: str,
        session_id: str,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """支持取消的执行"""
        try:
            async for event in self._execute_stream(...):
                if cancellation_token and cancellation_token.is_set():
                    yield DoneEvent(cancelled=True, reason="user_cancelled")
                    return
                yield event
        except asyncio.CancelledError:
            yield DoneEvent(cancelled=True, reason="user_cancelled")
            raise
```

## DataAgentServer Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 23: API 端点注册完整性
*For any* 必需的 API 端点（/api/v1/chat, /api/v1/sessions, /api/v1/health 等），该端点必须在 FastAPI 应用中注册
**Validates: Requirements 16.2**

### Property 24: API 响应 JSON 格式
*For any* API 请求，响应的 Content-Type 必须为 application/json
**Validates: Requirements 16.3**

### Property 25: 错误响应格式一致性
*For any* 失败的 API 请求，响应必须包含 error_code 和 message 字段
**Validates: Requirements 16.4**

### Property 26: WebSocket 消息格式验证
*For any* 客户端 WebSocket 消息，必须包含 type 和 payload 字段，否则服务器应返回错误
**Validates: Requirements 17.3**

### Property 27: 服务端事件推送格式
*For any* Agent 产生的 ExecutionEvent，通过 WebSocket 推送时必须包含 event_type 和 timestamp 字段
**Validates: Requirements 17.4, 17.5**

### Property 28: WebSocket 连接断开资源清理
*For any* WebSocket 连接断开，ConnectionManager 必须清理该 session_id 对应的所有资源
**Validates: Requirements 17.6**

### Property 29: HITL 超时自动拒绝
*For any* HITL 请求，当等待超过配置的超时时间时，系统必须自动返回 reject 决定
**Validates: Requirements 18.5**

### Property 30: API Key 认证有效性
*For any* 未携带有效 API Key 的请求（且认证未禁用），API 必须返回 401 状态码
**Validates: Requirements 19.3**

### Property 31: 多 API Key 支持
*For any* 配置的 API Key 列表中的任意 Key，使用该 Key 的请求必须通过认证
**Validates: Requirements 19.4**

### Property 32: 配置默认值
*For any* 未设置的配置项，ServerSettings 必须提供合理的默认值
**Validates: Requirements 20.4**

### Property 33: Pydantic 模型字段完整性
*For any* API 数据模型（ChatRequest, ChatResponse, SessionInfo, ErrorResponse），必须包含规范定义的所有必需字段
**Validates: Requirements 21.2, 21.3, 21.4, 21.5**

### Property 34: 健康检查响应格式
*For any* /api/v1/health 请求，响应必须包含 status、version、uptime 字段
**Validates: Requirements 22.4**

### Property 35: 请求 ID 追踪
*For any* API 请求，系统必须生成并记录唯一的 request_id
**Validates: Requirements 22.5**

### Property 36: 并发连接隔离性
*For any* 两个并发的 WebSocket 连接，一个连接的请求处理不应阻塞另一个连接的请求处理
**Validates: Requirements 23.4**

### Property 37: 连接管理器线程安全
*For any* 并发的连接/断开操作，ConnectionManager 的内部状态必须保持一致
**Validates: Requirements 23.5**

### Property 38: 系统过载保护
*For any* 超过最大连接数的连接请求，系统必须返回 503 状态码
**Validates: Requirements 23.6**

### Property 39: 取消消息响应
*For any* cancel 类型的 WebSocket 消息，服务器必须停止当前 Agent 执行并发送 DoneEvent(cancelled=True)
**Validates: Requirements 24.2, 24.3**

### Property 40: 取消操作及时性
*For any* 取消请求，系统必须在 1 秒内响应终止操作
**Validates: Requirements 24.5**

### Property 41: 取消后资源清理
*For any* 被取消的问答，系统必须清理相关的任务和资源
**Validates: Requirements 24.6**

### Property 42: MySQL 会话存储往返一致性
*For any* Session 对象，通过 MySQLSessionStore 创建后再获取，应该返回等价的 Session 对象
**Validates: Requirements 25.4**

### Property 43: 存储类型配置有效性
*For any* DATAAGENT_SESSION_STORE 配置值（memory/mysql），系统必须创建对应类型的 SessionStore 实例
**Validates: Requirements 25.2**

### Property 44: 数据库连接池管理
*For any* 并发的数据库操作，连接池必须正确管理连接的获取和释放
**Validates: Requirements 25.8**

### Property 45: 消息历史记录完整性
*For any* 完成的问答，用户消息和 Agent 响应必须被保存到 messages 表
**Validates: Requirements 26.1**

### Property 46: 消息查询分页正确性
*For any* 分页查询参数（limit, offset），返回的消息数量和顺序必须正确
**Validates: Requirements 26.4**

---

## MySQL Session Storage Design

### Database Schema

```sql
-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    assistant_id VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    state JSON,
    metadata JSON,
    INDEX idx_user_id (user_id),
    INDEX idx_assistant_id (assistant_id),
    INDEX idx_last_active (last_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 消息历史表
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role ENUM('user', 'assistant', 'system') NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### MySQLSessionStore Implementation

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, update

class MySQLSessionStore(SessionStore):
    """MySQL 会话存储实现"""
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        self._engine = create_async_engine(
            f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}",
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=3600,
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_tables(self) -> None:
        """初始化数据库表"""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def create(self, user_id: str, assistant_id: str) -> Session:
        """创建新会话"""
        ...
    
    async def get(self, session_id: str) -> Session | None:
        """获取会话"""
        ...
    
    async def update(self, session: Session) -> None:
        """更新会话"""
        ...
    
    async def delete(self, session_id: str) -> None:
        """删除会话"""
        ...
    
    async def list_by_user(self, user_id: str) -> list[Session]:
        """列出用户会话"""
        ...
    
    async def list_by_assistant(self, assistant_id: str) -> list[Session]:
        """列出助手会话"""
        ...
    
    async def cleanup_expired(self, timeout_seconds: float) -> int:
        """清理过期会话"""
        ...
```

### Message Store Interface

```python
class MessageStore(ABC):
    """消息存储抽象类"""
    
    @abstractmethod
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """保存消息，返回 message_id"""
        ...
    
    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """获取会话消息"""
        ...
    
    @abstractmethod
    async def delete_messages(self, session_id: str) -> int:
        """删除会话所有消息"""
        ...

class MySQLMessageStore(MessageStore):
    """MySQL 消息存储实现"""
    ...
```

### Storage Factory

```python
class SessionStoreFactory:
    """会话存储工厂"""
    
    @staticmethod
    def create(store_type: str, **kwargs) -> SessionStore:
        """根据配置创建存储实例"""
        if store_type == "memory":
            return MemorySessionStore()
        elif store_type == "mysql":
            return MySQLSessionStore(
                host=kwargs.get("host", "localhost"),
                port=kwargs.get("port", 3306),
                user=kwargs.get("user", "root"),
                password=kwargs.get("password", ""),
                database=kwargs.get("database", "dataagent"),
            )
        else:
            raise ValueError(f"Unknown store type: {store_type}")
```

### Updated Server Configuration

```python
class ServerSettings(BaseSettings):
    """服务配置"""
    # ... 现有配置 ...
    
    # 会话存储配置
    session_store: str = "memory"  # memory / mysql
    
    # MySQL 配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "dataagent"
    mysql_pool_size: int = 10
    mysql_max_overflow: int = 20
    
    model_config = SettingsConfigDict(
        env_prefix="DATAAGENT_",
        env_file=".env",
    )
```

---

## Phase 8: MCP Server 配置与多租户设计

### MCP Configuration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MCP Server 配置架构                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        CLI 模式 (静态配置)                           │  │
│   │                                                                      │  │
│   │  ~/.deepagents/{assistant_id}/mcp.json                              │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │ {                                                            │   │  │
│   │  │   "servers": [                                               │   │  │
│   │  │     {                                                        │   │  │
│   │  │       "name": "filesystem",                                  │   │  │
│   │  │       "command": "uvx",                                      │   │  │
│   │  │       "args": ["mcp-server-filesystem", "/workspace"],       │   │  │
│   │  │       "env": {},                                             │   │  │
│   │  │       "disabled": false                                      │   │  │
│   │  │     }                                                        │   │  │
│   │  │   ]                                                          │   │  │
│   │  │ }                                                            │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      Server 模式 (动态配置)                          │  │
│   │                                                                      │  │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │  │
│   │  │  REST API    │───▶│ MCPConfigMgr │───▶│  MySQL / ConfigFile  │  │  │
│   │  │  /mcp-servers│    │              │    │                      │  │  │
│   │  └──────────────┘    └──────────────┘    └──────────────────────┘  │  │
│   │                             │                                       │  │
│   │                             ▼                                       │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │              MCPConnectionPool (per user)                    │   │  │
│   │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                      │   │  │
│   │  │  │ Server1 │  │ Server2 │  │ Server3 │  ...                 │   │  │
│   │  │  └─────────┘  └─────────┘  └─────────┘                      │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MCP Configuration Data Models

```python
# MCP Server 配置模型
@dataclass
class MCPServerConfig:
    """单个 MCP Server 的配置"""
    name: str                          # 服务器名称（唯一标识）
    command: str                       # 启动命令 (e.g., "uvx", "npx", "python")
    args: list[str] = field(default_factory=list)  # 命令参数
    env: dict[str, str] = field(default_factory=dict)  # 环境变量
    disabled: bool = False             # 是否禁用
    timeout: int = 30                  # 连接超时（秒）

@dataclass
class MCPConfig:
    """MCP 配置集合"""
    servers: list[MCPServerConfig] = field(default_factory=list)
    
    @classmethod
    def from_file(cls, path: Path) -> "MCPConfig":
        """从 JSON 文件加载配置"""
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        servers = [MCPServerConfig(**s) for s in data.get("servers", [])]
        return cls(servers=servers)
    
    def to_file(self, path: Path) -> None:
        """保存配置到 JSON 文件"""
        data = {"servers": [asdict(s) for s in self.servers]}
        path.write_text(json.dumps(data, indent=2))

# Pydantic 模型用于 API
class MCPServerConfigRequest(BaseModel):
    """MCP Server 配置请求模型"""
    name: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}
    disabled: bool = False
    timeout: int = 30

class MCPServerConfigResponse(BaseModel):
    """MCP Server 配置响应模型"""
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    disabled: bool
    timeout: int
    status: str  # connected / disconnected / error
```

### MCP Connection Manager

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import BaseTool

class MCPConnectionManager:
    """MCP Server 连接管理器"""
    
    def __init__(
        self,
        max_servers_per_user: int = 5,
        connection_timeout: int = 30,
    ):
        self._connections: dict[str, MultiServerMCPClient] = {}  # user_id -> client
        self._tools_cache: dict[str, list[BaseTool]] = {}  # user_id -> tools
        self._lock = asyncio.Lock()
        self._max_servers = max_servers_per_user
        self._timeout = connection_timeout
    
    async def connect_user_servers(
        self,
        user_id: str,
        config: MCPConfig,
    ) -> list[BaseTool]:
        """为用户连接 MCP Servers 并返回工具列表"""
        async with self._lock:
            # 断开旧连接
            if user_id in self._connections:
                await self._disconnect_user(user_id)
            
            # 过滤启用的服务器
            enabled_servers = [s for s in config.servers if not s.disabled]
            if len(enabled_servers) > self._max_servers:
                enabled_servers = enabled_servers[:self._max_servers]
            
            if not enabled_servers:
                return []
            
            # 构建 MCP 客户端配置
            server_configs = {
                s.name: {
                    "command": s.command,
                    "args": s.args,
                    "env": s.env,
                }
                for s in enabled_servers
            }
            
            try:
                client = MultiServerMCPClient(server_configs)
                tools = await asyncio.wait_for(
                    client.get_tools(),
                    timeout=self._timeout,
                )
                self._connections[user_id] = client
                self._tools_cache[user_id] = tools
                return tools
            except asyncio.TimeoutError:
                logger.warning(f"MCP connection timeout for user {user_id}")
                return []
            except Exception as e:
                logger.error(f"MCP connection error for user {user_id}: {e}")
                return []
    
    async def get_user_tools(self, user_id: str) -> list[BaseTool]:
        """获取用户的 MCP 工具列表"""
        return self._tools_cache.get(user_id, [])
    
    async def disconnect_user(self, user_id: str) -> None:
        """断开用户的 MCP 连接"""
        async with self._lock:
            await self._disconnect_user(user_id)
    
    async def _disconnect_user(self, user_id: str) -> None:
        """内部断开方法（需要持有锁）"""
        if user_id in self._connections:
            try:
                await self._connections[user_id].close()
            except Exception as e:
                logger.warning(f"Error closing MCP connection: {e}")
            del self._connections[user_id]
        self._tools_cache.pop(user_id, None)
    
    async def health_check(self, user_id: str) -> dict[str, str]:
        """检查用户 MCP 连接健康状态"""
        # 返回每个服务器的状态
        ...
```

### Multi-Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           多租户隔离架构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         Tenant Layer                                 │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│   │  │   Tenant A   │  │   Tenant B   │  │   Tenant C   │              │  │
│   │  │  (企业客户)   │  │  (企业客户)   │  │  (个人用户)   │              │  │
│   │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │  │
│   └─────────┼─────────────────┼─────────────────┼───────────────────────┘  │
│             │                 │                 │                          │
│   ┌─────────▼─────────────────▼─────────────────▼───────────────────────┐  │
│   │                          User Layer                                  │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │                    User Isolation                            │   │  │
│   │  │                                                              │   │  │
│   │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │  │
│   │  │  │ Sessions │  │ Memory   │  │ History  │  │Workspace │    │   │  │
│   │  │  │ 会话隔离  │  │ 记忆隔离  │  │ 历史隔离  │  │ 文件隔离  │    │   │  │
│   │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │  │
│   │  │                                                              │   │  │
│   │  │  ┌──────────────────────────────────────────────────────┐   │   │  │
│   │  │  │              MCP Server Isolation                     │   │   │  │
│   │  │  │  每个用户独立的 MCP Server 连接池                       │   │   │  │
│   │  │  └──────────────────────────────────────────────────────┘   │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        Storage Layer                                 │  │
│   │                                                                      │  │
│   │  /data/                                                             │  │
│   │  ├── workspaces/                    # 用户工作区                     │  │
│   │  │   ├── {user_id_1}/                                               │  │
│   │  │   │   ├── files/                 # 用户文件                       │  │
│   │  │   │   ├── uploads/               # 上传文件                       │  │
│   │  │   │   └── outputs/               # 输出文件                       │  │
│   │  │   └── {user_id_2}/                                               │  │
│   │  │                                                                   │  │
│   │  ├── memories/                      # 记忆存储                       │  │
│   │  │   └── {user_id}/{assistant_id}/                                  │  │
│   │  │                                                                   │  │
│   │  └── mcp-configs/                   # MCP 配置                       │  │
│   │      └── {user_id}/mcp.json                                         │  │
│   │                                                                      │  │
│   │  MySQL:                                                             │  │
│   │  ├── sessions (user_id 索引)                                        │  │
│   │  ├── messages (session_id 索引)                                     │  │
│   │  ├── mcp_servers (user_id 索引)                                     │  │
│   │  └── tenants (租户配置)                                              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### User Workspace Manager

```python
from pathlib import Path
import shutil

class UserWorkspaceManager:
    """用户工作区管理器"""
    
    def __init__(
        self,
        workspace_root: Path,
        default_quota_bytes: int = 1024 * 1024 * 1024,  # 1GB
    ):
        self._root = workspace_root
        self._default_quota = default_quota_bytes
    
    def get_user_workspace(self, user_id: str) -> Path:
        """获取用户工作区路径"""
        return self._root / user_id
    
    def ensure_user_workspace(self, user_id: str) -> Path:
        """确保用户工作区存在"""
        workspace = self.get_user_workspace(user_id)
        (workspace / "files").mkdir(parents=True, exist_ok=True)
        (workspace / "uploads").mkdir(parents=True, exist_ok=True)
        (workspace / "outputs").mkdir(parents=True, exist_ok=True)
        return workspace
    
    def validate_path(self, user_id: str, path: Path) -> bool:
        """验证路径是否在用户工作区内"""
        workspace = self.get_user_workspace(user_id)
        try:
            resolved = path.resolve()
            return resolved.is_relative_to(workspace.resolve())
        except ValueError:
            return False
    
    def get_workspace_usage(self, user_id: str) -> int:
        """获取用户工作区使用量（字节）"""
        workspace = self.get_user_workspace(user_id)
        if not workspace.exists():
            return 0
        total = 0
        for f in workspace.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total
    
    def check_quota(self, user_id: str, additional_bytes: int = 0) -> bool:
        """检查是否超出配额"""
        usage = self.get_workspace_usage(user_id)
        return (usage + additional_bytes) <= self._default_quota
    
    def cleanup_workspace(self, user_id: str) -> None:
        """清理用户工作区"""
        workspace = self.get_user_workspace(user_id)
        if workspace.exists():
            shutil.rmtree(workspace)
```

### Sandboxed Filesystem Backend

```python
class SandboxedFilesystemBackend(FilesystemBackend):
    """沙箱化的文件系统后端，限制操作范围"""
    
    def __init__(
        self,
        user_id: str,
        workspace_manager: UserWorkspaceManager,
    ):
        self._user_id = user_id
        self._workspace_manager = workspace_manager
        self._workspace = workspace_manager.ensure_user_workspace(user_id)
        super().__init__(root=self._workspace)
    
    def _validate_path(self, path: str | Path) -> Path:
        """验证并解析路径"""
        resolved = (self._workspace / path).resolve()
        if not self._workspace_manager.validate_path(self._user_id, resolved):
            raise PermissionError(f"Access denied: path outside workspace")
        return resolved
    
    async def read_file(self, path: str) -> str:
        validated = self._validate_path(path)
        return validated.read_text()
    
    async def write_file(self, path: str, content: str) -> None:
        validated = self._validate_path(path)
        # 检查配额
        if not self._workspace_manager.check_quota(
            self._user_id, len(content.encode())
        ):
            raise PermissionError("Workspace quota exceeded")
        validated.parent.mkdir(parents=True, exist_ok=True)
        validated.write_text(content)
```

### Updated AgentConfig for Multi-Tenant

```python
@dataclass
class AgentConfig:
    """Configuration for creating an agent."""
    assistant_id: str
    user_id: str | None = None          # 用户 ID（多租户模式必需）
    tenant_id: str | None = None        # 租户 ID（企业模式）
    model: str | BaseChatModel | None = None
    enable_memory: bool = True
    enable_skills: bool = True
    enable_shell: bool = True
    enable_mcp: bool = True             # 是否启用 MCP
    auto_approve: bool = False
    sandbox_type: str | None = None
    sandbox_id: str | None = None
    system_prompt: str | None = None
    extra_tools: list[BaseTool] = field(default_factory=list)
    extra_middleware: list[AgentMiddleware] = field(default_factory=list)
    mcp_config: MCPConfig | None = None  # MCP 配置
    workspace_root: Path | None = None   # 用户工作区根目录
    recursion_limit: int = 1000
```

### MCP Configuration REST API

```python
# api/v1/mcp.py

@router.get("/users/{user_id}/mcp-servers")
async def list_mcp_servers(
    user_id: str,
    current_user: str = Depends(get_current_user),
    mcp_config_store: MCPConfigStore = Depends(get_mcp_config_store),
) -> list[MCPServerConfigResponse]:
    """列出用户的 MCP Server 配置"""
    # 权限检查：只能查看自己的配置或管理员可查看所有
    if current_user != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    config = await mcp_config_store.get_user_config(user_id)
    return [
        MCPServerConfigResponse(
            **asdict(s),
            status="unknown",  # 实际状态需要从连接管理器获取
        )
        for s in config.servers
    ]

@router.post("/users/{user_id}/mcp-servers")
async def add_mcp_server(
    user_id: str,
    server: MCPServerConfigRequest,
    current_user: str = Depends(get_current_user),
    mcp_config_store: MCPConfigStore = Depends(get_mcp_config_store),
) -> MCPServerConfigResponse:
    """添加 MCP Server 配置"""
    if current_user != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    config = await mcp_config_store.get_user_config(user_id)
    
    # 检查是否已存在同名服务器
    if any(s.name == server.name for s in config.servers):
        raise HTTPException(status_code=409, detail="Server already exists")
    
    new_server = MCPServerConfig(**server.model_dump())
    config.servers.append(new_server)
    await mcp_config_store.save_user_config(user_id, config)
    
    return MCPServerConfigResponse(**asdict(new_server), status="disconnected")

@router.delete("/users/{user_id}/mcp-servers/{server_name}")
async def delete_mcp_server(
    user_id: str,
    server_name: str,
    current_user: str = Depends(get_current_user),
    mcp_config_store: MCPConfigStore = Depends(get_mcp_config_store),
    mcp_connection_manager: MCPConnectionManager = Depends(get_mcp_connection_manager),
) -> dict:
    """删除 MCP Server 配置"""
    if current_user != user_id and not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    config = await mcp_config_store.get_user_config(user_id)
    config.servers = [s for s in config.servers if s.name != server_name]
    await mcp_config_store.save_user_config(user_id, config)
    
    # 断开连接（如果有）
    await mcp_connection_manager.disconnect_user(user_id)
    
    return {"status": "deleted", "server_name": server_name}
```

### Database Schema for MCP Configuration

```sql
-- MCP Server 配置表
CREATE TABLE IF NOT EXISTS mcp_servers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    command VARCHAR(256) NOT NULL,
    args JSON,
    env JSON,
    disabled BOOLEAN DEFAULT FALSE,
    timeout INT DEFAULT 30,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_server (user_id, name),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 租户配置表
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    max_users INT DEFAULT 100,
    max_sessions_per_user INT DEFAULT 10,
    max_mcp_servers INT DEFAULT 5,
    workspace_quota_bytes BIGINT DEFAULT 1073741824,  -- 1GB
    features_enabled JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户-租户关联表
CREATE TABLE IF NOT EXISTS user_tenants (
    user_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    role VARCHAR(32) DEFAULT 'member',  -- admin / member
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, tenant_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### MCP Correctness Properties

### Property 47: CLI MCP 配置加载
*For any* 有效的 mcp.json 配置文件，CLI 启动时必须成功加载并解析配置
**Validates: Requirements 29.1, 29.2**

### Property 48: MCP Server 连接失败不阻塞
*For any* MCP Server 连接失败，系统必须记录警告并继续运行，不阻塞主流程
**Validates: Requirements 29.5**

### Property 49: 用户 MCP 配置隔离
*For any* 两个不同用户，用户 A 的 MCP 配置变更不影响用户 B 的 MCP 工具
**Validates: Requirements 30.4**

### Property 50: MCP 连接池资源释放
*For any* 用户会话结束，系统必须释放该用户的 MCP Server 连接
**Validates: Requirements 31.3**

### Property 51: 用户会话隔离
*For any* 用户 A 的会话查询，结果必须只包含用户 A 的会话
**Validates: Requirements 32.5**

### Property 52: 用户工作区路径沙箱
*For any* 文件操作请求，如果路径在用户工作区外，系统必须拒绝操作
**Validates: Requirements 32.6, 33.4**

### Property 53: 用户工作区配额检查
*For any* 写入操作，如果超出用户配额，系统必须拒绝操作
**Validates: Requirements 33.6**

### Property 54: 用户记忆隔离
*For any* 记忆加载操作，系统必须只加载当前用户的记忆数据
**Validates: Requirements 34.3**

---

## DataAgentServerDemo MCP 配置设计

### Demo MCP 配置界面架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DataAgent Server Demo                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  [💬 对话]  [🔌 MCP 配置]                                            │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      MCP 配置标签页                                  │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │  已配置的 MCP Servers                                        │   │  │
│   │  │  ┌─────────────────────────────────────────────────────┐    │   │  │
│   │  │  │ 🔧 filesystem  🟢 connected  [删除]                  │    │   │  │
│   │  │  │ 🔧 database    🔴 disconnected  [删除]               │    │   │  │
│   │  │  └─────────────────────────────────────────────────────┘    │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │  添加新的 MCP Server                                         │   │  │
│   │  │  名称: [________________]                                    │   │  │
│   │  │  命令: [________________]                                    │   │  │
│   │  │  参数: [________________] (JSON 数组)                        │   │  │
│   │  │  环境变量: [____________] (JSON 对象)                        │   │  │
│   │  │  [ ] 禁用                                                    │   │  │
│   │  │  [➕ 添加 MCP Server]                                        │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────────────────────────────────────────┐   │  │
│   │  │  📖 配置示例                                                 │   │  │
│   │  │  - 文件系统 MCP Server                                       │   │  │
│   │  │  - 数据库 MCP Server                                         │   │  │
│   │  │  - 自定义 Python MCP Server                                  │   │  │
│   │  └─────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Demo MCP API 客户端函数

```python
async def get_mcp_servers(
    http_url: str,
    user_id: str,
    api_key: str | None = None,
) -> list:
    """获取用户的 MCP Server 配置列表"""
    ...

async def add_mcp_server(
    http_url: str,
    user_id: str,
    server_config: dict,
    api_key: str | None = None,
) -> bool:
    """添加 MCP Server 配置"""
    ...

async def delete_mcp_server(
    http_url: str,
    user_id: str,
    server_name: str,
    api_key: str | None = None,
) -> bool:
    """删除 MCP Server 配置"""
    ...
```

### Demo MCP 配置界面组件

```python
def render_mcp_config(http_url: str, api_key: str | None):
    """渲染 MCP 配置面板"""
    st.subheader("🔌 MCP Server 配置")
    
    # 1. 显示已配置的 MCP Servers
    mcp_servers = asyncio.run(get_mcp_servers(...))
    for server in mcp_servers:
        with st.expander(f"🔧 {server['name']}"):
            st.code(json.dumps(server, indent=2))
            if st.button(f"删除 {server['name']}"):
                asyncio.run(delete_mcp_server(...))
    
    # 2. 添加新 MCP Server 表单
    with st.form("add_mcp_server"):
        name = st.text_input("名称")
        command = st.text_input("命令")
        args = st.text_input("参数 (JSON 数组)")
        env = st.text_input("环境变量 (JSON 对象)")
        if st.form_submit_button("➕ 添加"):
            asyncio.run(add_mcp_server(...))
    
    # 3. 配置示例
    with st.expander("📖 配置示例"):
        st.markdown("...")
```

### Property 55: Demo MCP 配置界面完整性
*For any* Demo 应用启动，MCP 配置标签页必须可访问且包含列表、添加、删除功能
**Validates: Requirements 36.1, 36.2, 36.3, 36.4**

### Property 56: Demo MCP API 错误处理
*For any* MCP API 调用失败，Demo 界面必须显示友好提示而非崩溃
**Validates: Requirements 36.7**

---

## Error Handling

### 错误分类

1. **可恢复错误 (recoverable=True)**
   - 网络超时
   - API 限流
   - 临时文件访问失败
   
2. **不可恢复错误 (recoverable=False)**
   - 配置错误
   - 认证失败
   - 致命的内部错误

### 错误处理策略

```python
# 执行器中的错误处理
async def execute(self, user_input: str, session_id: str, context: dict | None = None) -> AsyncIterator[ExecutionEvent]:
    try:
        async for event in self._execute_stream(stream_input, config, session_id):
            yield event
    except Exception as e:
        yield ErrorEvent(
            event_type="error",
            timestamp=time.time(),
            error=str(e),
            recoverable=False,
        )
```

### 日志规范

```python
import logging

logger = logging.getLogger(__name__)

# 日志级别使用
logger.debug("详细调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## Testing Strategy

### 双重测试方法

本项目采用单元测试和属性测试相结合的方法：

1. **单元测试**: 验证特定示例和边界情况
2. **属性测试**: 验证应该在所有输入上成立的通用属性

### 测试框架

- **pytest**: 主测试框架
- **pytest-asyncio**: 异步测试支持
- **hypothesis**: 属性测试库

### 属性测试规范

每个属性测试必须：
1. 使用 `@given` 装饰器定义输入生成策略
2. 配置至少 100 次迭代
3. 使用注释标记对应的正确性属性

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@settings(max_examples=100)
@given(content=st.text(), is_final=st.booleans())
def test_text_event_serialization_roundtrip(content: str, is_final: bool):
    """
    **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
    """
    event = TextEvent(content=content, is_final=is_final)
    serialized = event.to_dict()
    # 验证可以反序列化
    assert serialized["event_type"] == "text"
    assert serialized["content"] == content
    assert serialized["is_final"] == is_final
```

### 测试目录结构

```
tests/
├── conftest.py              # 共享 fixtures
├── test_events/
│   ├── test_serialization.py
│   └── test_properties.py   # 属性测试
├── test_engine/
│   ├── test_factory.py
│   └── test_executor.py
├── test_middleware/
│   ├── test_memory.py
│   └── test_skills.py
├── test_hitl/
│   └── test_protocol.py
└── test_session/
    └── test_manager.py
```

### 覆盖率要求

- 核心模块 (engine, events, hitl): ≥ 80%
- 中间件模块: ≥ 70%
- 工具模块: ≥ 70%

