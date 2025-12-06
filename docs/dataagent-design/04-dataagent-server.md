# DataAgent 架构设计方案

## 第四章：DataAgentServer 详细设计

### 4.1 目录结构

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
│   │       ├── skills.py         # 技能管理
│   │       └── admin.py          # 管理员 API
│   │
│   ├── websocket/                # WebSocket
│   │   ├── __init__.py
│   │   ├── manager.py            # 连接管理
│   │   ├── handlers.py           # 消息处理
│   │   └── protocol.py           # 消息协议
│   │
│   ├── services/                 # 服务层
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── session.py
│   │   └── user.py
│   │
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   └── message.py
│   │
│   ├── db/                       # 数据库
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── repositories/
│   │
│   ├── auth/                     # 认证
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   └── middleware.py
│   │
│   ├── hitl/                     # HITL 实现
│   │   ├── __init__.py
│   │   └── websocket_handler.py
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py
```


### 4.2 WebSocket 消息协议

#### 4.2.1 客户端 -> 服务端

```typescript
// 消息类型
type ClientMessageType = "chat" | "hitl_decision" | "cancel" | "ping";

interface ClientMessage {
  type: ClientMessageType;
  payload: ChatPayload | HITLDecisionPayload | null;
  request_id?: string;  // 可选，用于追踪请求
}

interface ChatPayload {
  message: string;
  session_id?: string;
  assistant_id?: string;
  context?: Record<string, any>;
}

interface HITLDecisionPayload {
  interrupt_id: string;
  decisions: Array<{
    type: "approve" | "reject";
    message?: string;
  }>;
}
```

#### 4.2.2 服务端 -> 客户端

```typescript
type ServerMessageType = 
  | "text"           // 文本输出
  | "tool_call"      // 工具调用
  | "tool_result"    // 工具结果
  | "hitl_request"   // HITL 请求
  | "todo_update"    // Todo 更新
  | "file_operation" // 文件操作
  | "error"          // 错误
  | "done"           // 完成
  | "pong";          // 心跳响应

interface ServerMessage {
  type: ServerMessageType;
  data: any;
  timestamp: number;
  request_id?: string;
}

// 具体数据结构
interface TextData {
  content: string;
  is_final: boolean;
}

interface ToolCallData {
  tool_name: string;
  tool_args: Record<string, any>;
  tool_call_id: string;
}

interface ToolResultData {
  tool_call_id: string;
  result: any;
  status: "success" | "error";
}

interface HITLRequestData {
  interrupt_id: string;
  action_requests: Array<{
    name: string;
    args: Record<string, any>;
    description: string;
  }>;
}

interface FileOperationData {
  operation: "read" | "write" | "edit";
  file_path: string;
  metrics: {
    lines_read?: number;
    lines_written?: number;
    lines_added?: number;
    lines_removed?: number;
  };
  diff?: string;
  status: "success" | "error";
}

interface TodoUpdateData {
  todos: Array<{
    content: string;
    status: "pending" | "in_progress" | "completed";
  }>;
}

interface ErrorData {
  error: string;
  recoverable: boolean;
}

interface DoneData {
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
  };
  cancelled: boolean;
}
```

### 4.3 核心实现

#### 4.3.1 WebSocket 连接管理

```python
# dataagent_server/websocket/manager.py

from typing import Dict, Set
from fastapi import WebSocket
import asyncio


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # session_id -> WebSocket
        self._connections: Dict[str, WebSocket] = {}
        # session_id -> pending HITL decisions
        self._pending_decisions: Dict[str, asyncio.Future] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """建立连接"""
        await websocket.accept()
        self._connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        """断开连接"""
        self._connections.pop(session_id, None)
        # 取消等待中的 HITL 决定
        if session_id in self._pending_decisions:
            self._pending_decisions[session_id].cancel()
            del self._pending_decisions[session_id]
    
    async def send(self, session_id: str, message: dict):
        """发送消息"""
        if session_id in self._connections:
            await self._connections[session_id].send_json(message)
    
    async def send_event(self, session_id: str, event: ExecutionEvent):
        """发送执行事件"""
        await self.send(session_id, {
            "type": event.event_type,
            "data": event.to_dict(),
            "timestamp": event.timestamp,
        })
    
    async def wait_for_decision(
        self, 
        session_id: str, 
        timeout: float = 300,
    ) -> dict | None:
        """等待 HITL 决定"""
        future = asyncio.get_event_loop().create_future()
        self._pending_decisions[session_id] = future
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_decisions.pop(session_id, None)
    
    def resolve_decision(self, session_id: str, decision: dict):
        """解决 HITL 决定"""
        if session_id in self._pending_decisions:
            self._pending_decisions[session_id].set_result(decision)
```

#### 4.3.2 WebSocket HITL 处理器

```python
# dataagent_server/hitl/websocket_handler.py

from dataagent_core.hitl import HITLHandler, ActionRequest, Decision


class WebSocketHITLHandler(HITLHandler):
    """WebSocket HITL 处理器"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connections = connection_manager
    
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """请求用户审批"""
        # 发送 HITL 请求到前端
        await self.connections.send(session_id, {
            "type": "hitl_request",
            "data": {
                "action_request": action_request,
            },
            "timestamp": time.time(),
        })
        
        # 等待用户响应
        response = await self.connections.wait_for_decision(session_id)
        
        if response is None:
            # 超时，默认拒绝
            return {"type": "reject", "message": "Timeout"}
        
        return response
```

#### 4.3.3 WebSocket 消息处理

```python
# dataagent_server/websocket/handlers.py

from fastapi import WebSocket, WebSocketDisconnect
from dataagent_core.engine import AgentExecutor, AgentConfig
from dataagent_core.session import SessionManager


class WebSocketChatHandler:
    """WebSocket 聊天处理器"""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        session_manager: SessionManager,
    ):
        self.connections = connection_manager
        self.sessions = session_manager
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: str,
    ):
        """处理 WebSocket 连接"""
        session_id = str(uuid.uuid4())
        await self.connections.connect(websocket, session_id)
        
        # 发送连接成功消息
        await self.connections.send(session_id, {
            "type": "connected",
            "data": {"session_id": session_id},
        })
        
        try:
            while True:
                data = await websocket.receive_json()
                await self._handle_message(data, user_id, session_id)
        except WebSocketDisconnect:
            self.connections.disconnect(session_id)
    
    async def _handle_message(
        self,
        data: dict,
        user_id: str,
        session_id: str,
    ):
        """处理消息"""
        msg_type = data.get("type")
        payload = data.get("payload", {})
        request_id = data.get("request_id")
        
        if msg_type == "chat":
            await self._handle_chat(payload, user_id, session_id, request_id)
        elif msg_type == "hitl_decision":
            await self._handle_hitl_decision(payload, session_id)
        elif msg_type == "cancel":
            await self._handle_cancel(session_id)
        elif msg_type == "ping":
            await self.connections.send(session_id, {"type": "pong"})
    
    async def _handle_chat(
        self,
        payload: dict,
        user_id: str,
        session_id: str,
        request_id: str | None,
    ):
        """处理聊天消息"""
        message = payload.get("message", "")
        assistant_id = payload.get("assistant_id", "default")
        
        # 获取或创建会话
        session = await self.sessions.get_or_create_session(
            user_id=user_id,
            assistant_id=assistant_id,
            session_id=session_id,
        )
        
        # 创建 HITL 处理器
        hitl_handler = WebSocketHITLHandler(self.connections)
        
        # 获取执行器
        config = AgentConfig(assistant_id=assistant_id)
        executor = await self.sessions.get_executor(
            session=session,
            config=config,
            hitl_handler=hitl_handler,
        )
        
        # 执行并推送事件
        async for event in executor.execute(message, session_id):
            await self.connections.send_event(session_id, event)
    
    async def _handle_hitl_decision(
        self,
        payload: dict,
        session_id: str,
    ):
        """处理 HITL 决定"""
        decisions = payload.get("decisions", [])
        self.connections.resolve_decision(session_id, decisions[0] if decisions else None)
    
    async def _handle_cancel(self, session_id: str):
        """处理取消请求"""
        # TODO: 实现取消逻辑
        pass
```


### 4.4 REST API 设计

#### 4.4.1 聊天 API

```python
# dataagent_server/api/v1/chat.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: str | None = None
    assistant_id: str = "default"
    context: dict | None = None


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    message_id: str
    content: str
    tool_calls: list[dict] | None = None
    todos: list[dict] | None = None


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """发送消息（非流式）"""
    return await chat_service.process_message(
        user_id=user.id,
        message=request.message,
        session_id=request.session_id,
        assistant_id=request.assistant_id,
    )


@router.post("/message/stream")
async def send_message_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """发送消息（SSE 流式）"""
    async def event_generator():
        async for event in chat_service.process_message_stream(
            user_id=user.id,
            message=request.message,
            session_id=request.session_id,
            assistant_id=request.assistant_id,
        ):
            yield {
                "event": event.event_type,
                "data": json.dumps(event.to_dict()),
            }
    
    return EventSourceResponse(event_generator())
```

#### 4.4.2 会话 API

```python
# dataagent_server/api/v1/sessions.py

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionResponse(BaseModel):
    session_id: str
    assistant_id: str
    created_at: datetime
    last_active: datetime
    message_count: int


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """列出用户会话"""
    return await session_service.list_user_sessions(user.id)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """获取会话详情"""
    session = await session_service.get_session(session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
):
    """删除会话"""
    await session_service.delete_session(session_id, user.id)
    return {"status": "ok"}


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    limit: int = 50,
    offset: int = 0,
):
    """获取会话消息历史"""
    return await session_service.get_messages(
        session_id=session_id,
        user_id=user.id,
        limit=limit,
        offset=offset,
    )
```

### 4.5 服务层

```python
# dataagent_server/services/chat.py

from dataagent_core.engine import AgentFactory, AgentExecutor, AgentConfig
from dataagent_core.session import SessionManager
from dataagent_core.events import ExecutionEvent, TextEvent


class ChatService:
    """聊天服务"""
    
    def __init__(
        self,
        session_manager: SessionManager,
        agent_factory: AgentFactory,
        message_repo: MessageRepository,
    ):
        self.sessions = session_manager
        self.agent_factory = agent_factory
        self.messages = message_repo
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: str | None,
        assistant_id: str,
    ) -> ChatResponse:
        """处理消息（非流式）"""
        full_content = ""
        tool_calls = []
        todos = []
        
        async for event in self.process_message_stream(
            user_id, message, session_id, assistant_id
        ):
            if isinstance(event, TextEvent) and event.is_final:
                full_content = event.content
            elif event.event_type == "tool_call":
                tool_calls.append(event.to_dict())
            elif event.event_type == "todo_update":
                todos = event.todos
        
        return ChatResponse(
            session_id=session_id or "",
            message_id=str(uuid.uuid4()),
            content=full_content,
            tool_calls=tool_calls or None,
            todos=todos or None,
        )
    
    async def process_message_stream(
        self,
        user_id: str,
        message: str,
        session_id: str | None,
        assistant_id: str,
    ) -> AsyncIterator[ExecutionEvent]:
        """处理消息（流式）"""
        # 1. 获取或创建会话
        session = await self.sessions.get_or_create_session(
            user_id=user_id,
            assistant_id=assistant_id,
            session_id=session_id,
        )
        
        # 2. 保存用户消息
        await self.messages.create(
            session_id=session.session_id,
            role="user",
            content=message,
        )
        
        # 3. 获取执行器（SSE 模式使用自动审批）
        config = AgentConfig(
            assistant_id=assistant_id,
            auto_approve=True,  # SSE 模式自动审批
        )
        executor = await self.sessions.get_executor(session, config)
        
        # 4. 执行并收集响应
        full_response = ""
        async for event in executor.execute(message, session.session_id):
            if isinstance(event, TextEvent):
                full_response += event.content
            yield event
        
        # 5. 保存助手响应
        await self.messages.create(
            session_id=session.session_id,
            role="assistant",
            content=full_response,
        )
```

### 4.6 FastAPI 应用入口

```python
# dataagent_server/main.py

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from dataagent_server.api.v1 import chat, sessions, agents, skills
from dataagent_server.websocket import WebSocketChatHandler, ConnectionManager
from dataagent_server.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时初始化
    app.state.connection_manager = ConnectionManager()
    app.state.session_manager = create_session_manager()
    app.state.ws_handler = WebSocketChatHandler(
        app.state.connection_manager,
        app.state.session_manager,
    )
    yield
    # 关闭时清理
    pass


app = FastAPI(
    title="DataAgent Server",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API 路由
app.include_router(chat.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")


# WebSocket 端点
@app.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str | None = None,
):
    """WebSocket 聊天端点"""
    # 验证 token
    user = await verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    # 处理连接
    handler = app.state.ws_handler
    await handler.handle_connection(websocket, user.id)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
```

### 4.7 依赖关系

```toml
# pyproject.toml

[project]
name = "dataagent-server"
dependencies = [
    "dataagent-core",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "websockets>=12.0",
    "sse-starlette>=1.8.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "pydantic-settings>=2.0.0",
]
```

---

下一章：[05-dataagent-cli.md](./05-dataagent-cli.md) - DataAgentCli 设计
