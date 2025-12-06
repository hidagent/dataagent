# DataAgent 架构设计方案

## 第三章：DataAgentCore 详细设计

### 3.1 目录结构

```
libs/dataagent-core/
├── pyproject.toml
├── README.md
├── dataagent_core/
│   ├── __init__.py
│   │
│   ├── # ========== 核心引擎 ==========
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── factory.py            # Agent 工厂
│   │   ├── executor.py           # 任务执行器
│   │   ├── streaming.py          # 流式处理
│   │   └── types.py              # 引擎类型定义
│   │
│   ├── # ========== 事件系统 ==========
│   ├── events/
│   │   ├── __init__.py
│   │   ├── base.py               # 事件基类
│   │   ├── text.py               # 文本事件
│   │   ├── tool.py               # 工具事件
│   │   ├── hitl.py               # HITL 事件
│   │   ├── file.py               # 文件操作事件
│   │   └── system.py             # 系统事件
│   │
│   ├── # ========== 中间件系统 ==========
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── base.py               # 中间件基类
│   │   ├── memory.py             # 长期记忆
│   │   ├── skills.py             # 技能系统
│   │   └── shell.py              # Shell 执行
│   │
│   ├── # ========== 工具系统 ==========
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py           # 工具注册表
│   │   ├── web.py                # Web 工具
│   │   ├── file_tracker.py       # 文件操作追踪
│   │   └── data/                 # 数据领域工具
│   │       ├── __init__.py
│   │       ├── sql.py            # SQL 执行
│   │       ├── catalog.py        # 数据目录
│   │       └── report.py         # 报告生成
│   │
│   ├── # ========== 技能系统 ==========
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── loader.py             # 技能加载
│   │   ├── manager.py            # 技能管理
│   │   └── types.py              # 技能类型
│   │
│   ├── # ========== 沙箱集成 ==========
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── factory.py            # 沙箱工厂
│   │   ├── modal.py
│   │   ├── runloop.py
│   │   └── daytona.py
│   │
│   ├── # ========== 会话管理 ==========
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py            # 会话管理器
│   │   ├── state.py              # 会话状态
│   │   ├── store.py              # 存储抽象
│   │   └── stores/               # 存储实现
│   │       ├── __init__.py
│   │       ├── memory.py         # 内存存储
│   │       ├── redis.py          # Redis 存储
│   │       └── database.py       # 数据库存储
│   │
│   ├── # ========== HITL 协议 ==========
│   ├── hitl/
│   │   ├── __init__.py
│   │   ├── protocol.py           # HITL 协议
│   │   ├── types.py              # 类型定义
│   │   └── auto_approve.py       # 自动审批处理器
│   │
│   ├── # ========== 配置管理 ==========
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py           # 核心设置
│   │   ├── models.py             # 模型配置
│   │   └── prompts.py            # 提示词模板
│   │
│   └── # ========== 工具函数 ==========
│       └── utils/
│           ├── __init__.py
│           ├── tokens.py         # Token 计算
│           ├── diff.py           # Diff 计算
│           └── paths.py          # 路径处理
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_engine/
    ├── test_middleware/
    ├── test_tools/
    └── test_session/
```

### 3.2 核心接口设计

#### 3.2.1 Agent 工厂

```python
# dataagent_core/engine/factory.py

from dataclasses import dataclass, field
from typing import Any
from langchain.tools import BaseTool
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langgraph.pregel import Pregel
from deepagents.backends import CompositeBackend

from dataagent_core.config import Settings
from dataagent_core.hitl import HITLHandler


@dataclass
class AgentConfig:
    """Agent 配置"""
    # 必需参数
    assistant_id: str
    
    # 模型配置
    model: str | BaseChatModel | None = None  # None 时使用默认模型
    
    # 功能开关
    enable_memory: bool = True
    enable_skills: bool = True
    enable_shell: bool = True
    auto_approve: bool = False
    
    # 沙箱配置
    sandbox_type: str | None = None  # modal, runloop, daytona
    sandbox_id: str | None = None
    
    # 自定义配置
    system_prompt: str | None = None
    extra_tools: list[BaseTool] = field(default_factory=list)
    extra_middleware: list[AgentMiddleware] = field(default_factory=list)
    
    # 运行时配置
    recursion_limit: int = 1000
    timeout: float | None = None


class AgentFactory:
    """Agent 工厂 - 核心创建逻辑"""
    
    def __init__(
        self,
        settings: Settings,
        hitl_handler: HITLHandler | None = None,
    ):
        """
        Args:
            settings: 全局设置
            hitl_handler: HITL 处理器，None 时使用自动审批
        """
        self.settings = settings
        self.hitl_handler = hitl_handler
    
    def create_agent(
        self,
        config: AgentConfig,
    ) -> tuple[Pregel, CompositeBackend]:
        """
        创建配置好的 Agent
        
        Returns:
            (agent_graph, backend) 元组
        """
        # 1. 创建或获取模型
        model = self._resolve_model(config.model)
        
        # 2. 设置 Agent 目录
        agent_dir = self._setup_agent_dir(config.assistant_id)
        
        # 3. 构建中间件栈
        middleware = self._build_middleware(config, agent_dir)
        
        # 4. 构建工具列表
        tools = self._build_tools(config)
        
        # 5. 创建后端
        backend = self._create_backend(config)
        
        # 6. 配置 HITL
        interrupt_on = self._build_interrupt_config(config)
        
        # 7. 获取 system prompt
        system_prompt = self._build_system_prompt(config)
        
        # 8. 创建 Agent
        agent = create_deep_agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            backend=backend,
            middleware=middleware,
            interrupt_on=interrupt_on,
            checkpointer=InMemorySaver(),
        ).with_config({"recursion_limit": config.recursion_limit})
        
        return agent, backend
    
    def _resolve_model(self, model: str | BaseChatModel | None) -> BaseChatModel:
        """解析模型配置"""
        if model is None:
            return self.settings.create_default_model()
        if isinstance(model, str):
            return self.settings.create_model(model)
        return model
    
    def _setup_agent_dir(self, assistant_id: str) -> Path:
        """设置 Agent 目录"""
        agent_dir = self.settings.ensure_agent_dir(assistant_id)
        agent_md = agent_dir / "agent.md"
        if not agent_md.exists():
            agent_md.write_text(self.settings.default_agent_prompt)
        return agent_dir
    
    def _build_middleware(
        self, 
        config: AgentConfig, 
        agent_dir: Path,
    ) -> list[AgentMiddleware]:
        """构建中间件栈"""
        middleware = []
        
        if config.enable_memory:
            middleware.append(
                AgentMemoryMiddleware(
                    settings=self.settings,
                    assistant_id=config.assistant_id,
                )
            )
        
        if config.enable_skills:
            middleware.append(
                SkillsMiddleware(
                    skills_dir=agent_dir / "skills",
                    assistant_id=config.assistant_id,
                    project_skills_dir=self.settings.get_project_skills_dir(),
                )
            )
        
        if config.enable_shell and config.sandbox_type is None:
            middleware.append(
                ShellMiddleware(
                    workspace_root=str(Path.cwd()),
                    env=os.environ,
                )
            )
        
        middleware.extend(config.extra_middleware)
        return middleware
    
    def _build_tools(self, config: AgentConfig) -> list[BaseTool]:
        """构建工具列表"""
        tools = [http_request, fetch_url]
        
        if self.settings.has_tavily:
            tools.append(web_search)
        
        tools.extend(config.extra_tools)
        return tools
    
    def _create_backend(self, config: AgentConfig) -> CompositeBackend:
        """创建后端"""
        if config.sandbox_type:
            sandbox = create_sandbox(
                config.sandbox_type,
                sandbox_id=config.sandbox_id,
            )
            return CompositeBackend(default=sandbox, routes={})
        else:
            return CompositeBackend(
                default=FilesystemBackend(),
                routes={},
            )
    
    def _build_interrupt_config(self, config: AgentConfig) -> dict:
        """构建 HITL 中断配置"""
        if config.auto_approve:
            return {}
        
        return {
            "shell": self._create_interrupt_config("shell"),
            "execute": self._create_interrupt_config("execute"),
            "write_file": self._create_interrupt_config("write_file"),
            "edit_file": self._create_interrupt_config("edit_file"),
            "web_search": self._create_interrupt_config("web_search"),
            "fetch_url": self._create_interrupt_config("fetch_url"),
            "task": self._create_interrupt_config("task"),
        }
    
    def _build_system_prompt(self, config: AgentConfig) -> str:
        """构建 system prompt"""
        if config.system_prompt:
            return config.system_prompt
        return get_default_system_prompt(
            assistant_id=config.assistant_id,
            sandbox_type=config.sandbox_type,
        )
```

#### 3.2.2 任务执行器

```python
# dataagent_core/engine/executor.py

from typing import AsyncIterator
from dataagent_core.events import (
    ExecutionEvent, TextEvent, ToolCallEvent, ToolResultEvent,
    HITLRequestEvent, TodoUpdateEvent, FileOperationEvent,
    ErrorEvent, DoneEvent,
)
from dataagent_core.hitl import HITLHandler, Decision
from dataagent_core.tools import FileOpTracker


class AgentExecutor:
    """Agent 执行器 - 核心执行逻辑"""
    
    def __init__(
        self,
        agent: Pregel,
        backend: CompositeBackend,
        hitl_handler: HITLHandler | None = None,
        assistant_id: str | None = None,
    ):
        self.agent = agent
        self.backend = backend
        self.hitl_handler = hitl_handler
        self.assistant_id = assistant_id
        
        # 状态追踪
        self._file_tracker = FileOpTracker(
            assistant_id=assistant_id,
            backend=backend,
        )
    
    async def execute(
        self,
        user_input: str,
        session_id: str,
        context: dict | None = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """
        执行用户请求，返回事件流
        
        Args:
            user_input: 用户输入
            session_id: 会话 ID
            context: 额外上下文
            
        Yields:
            ExecutionEvent: 执行事件
        """
        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {"assistant_id": self.assistant_id},
        }
        
        stream_input = {"messages": [{"role": "user", "content": user_input}]}
        
        try:
            async for event in self._execute_stream(stream_input, config):
                yield event
        except Exception as e:
            yield ErrorEvent(
                event_type="error",
                timestamp=time.time(),
                error=str(e),
                recoverable=False,
            )
    
    async def _execute_stream(
        self,
        stream_input: dict,
        config: dict,
    ) -> AsyncIterator[ExecutionEvent]:
        """内部执行流"""
        
        while True:
            pending_interrupts = {}
            
            async for chunk in self.agent.astream(
                stream_input,
                stream_mode=["messages", "updates"],
                subgraphs=True,
                config=config,
                durability="exit",
            ):
                if not isinstance(chunk, tuple) or len(chunk) != 3:
                    continue
                
                _namespace, stream_mode, data = chunk
                
                # 处理 updates 流
                if stream_mode == "updates":
                    async for event in self._handle_updates(data, pending_interrupts):
                        yield event
                
                # 处理 messages 流
                elif stream_mode == "messages":
                    async for event in self._handle_messages(data):
                        yield event
            
            # 处理 HITL 中断
            if pending_interrupts:
                hitl_response = await self._handle_hitl(pending_interrupts)
                
                if hitl_response is None:
                    # 用户拒绝，结束执行
                    yield DoneEvent(
                        event_type="done",
                        timestamp=time.time(),
                        cancelled=True,
                    )
                    return
                
                # 恢复执行
                stream_input = Command(resume=hitl_response)
            else:
                # 正常结束
                yield DoneEvent(
                    event_type="done",
                    timestamp=time.time(),
                )
                return
    
    async def _handle_updates(
        self,
        data: dict,
        pending_interrupts: dict,
    ) -> AsyncIterator[ExecutionEvent]:
        """处理 updates 流"""
        if not isinstance(data, dict):
            return
        
        # 检查中断
        if "__interrupt__" in data:
            for interrupt in data["__interrupt__"]:
                try:
                    request = validate_hitl_request(interrupt.value)
                    pending_interrupts[interrupt.id] = request
                except ValidationError:
                    pass
        
        # 检查 todo 更新
        chunk_data = next(iter(data.values())) if data else None
        if chunk_data and isinstance(chunk_data, dict) and "todos" in chunk_data:
            yield TodoUpdateEvent(
                event_type="todo_update",
                timestamp=time.time(),
                todos=chunk_data["todos"],
            )
    
    async def _handle_messages(
        self,
        data: tuple,
    ) -> AsyncIterator[ExecutionEvent]:
        """处理 messages 流"""
        if not isinstance(data, tuple) or len(data) != 2:
            return
        
        message, _metadata = data
        
        # 处理工具消息
        if isinstance(message, ToolMessage):
            async for event in self._handle_tool_message(message):
                yield event
            return
        
        # 处理 AI 消息
        if hasattr(message, "content_blocks"):
            for block in message.content_blocks:
                async for event in self._handle_content_block(block):
                    yield event
    
    async def _handle_content_block(
        self,
        block: dict,
    ) -> AsyncIterator[ExecutionEvent]:
        """处理内容块"""
        block_type = block.get("type")
        
        if block_type == "text":
            yield TextEvent(
                event_type="text",
                timestamp=time.time(),
                content=block.get("text", ""),
                is_final=False,
            )
        
        elif block_type in ("tool_call_chunk", "tool_call"):
            # 解析工具调用
            tool_call = self._parse_tool_call(block)
            if tool_call:
                yield ToolCallEvent(
                    event_type="tool_call",
                    timestamp=time.time(),
                    tool_name=tool_call["name"],
                    tool_args=tool_call["args"],
                    tool_call_id=tool_call["id"],
                )
                
                # 追踪文件操作
                self._file_tracker.start_operation(
                    tool_call["name"],
                    tool_call["args"],
                    tool_call["id"],
                )
    
    async def _handle_tool_message(
        self,
        message: ToolMessage,
    ) -> AsyncIterator[ExecutionEvent]:
        """处理工具结果"""
        tool_call_id = message.tool_call_id
        status = getattr(message, "status", "success")
        content = message.content
        
        yield ToolResultEvent(
            event_type="tool_result",
            timestamp=time.time(),
            tool_call_id=tool_call_id,
            result=content,
            status=status,
        )
        
        # 完成文件操作追踪
        record = self._file_tracker.complete_with_message(message)
        if record:
            yield FileOperationEvent(
                event_type="file_operation",
                timestamp=time.time(),
                operation=record.tool_name,
                file_path=record.display_path,
                metrics=record.metrics,
                diff=record.diff,
                status=record.status,
            )
    
    async def _handle_hitl(
        self,
        pending_interrupts: dict,
    ) -> dict | None:
        """处理 HITL 中断"""
        if not self.hitl_handler:
            # 无处理器，自动批准
            return self._auto_approve_all(pending_interrupts)
        
        hitl_response = {}
        
        for interrupt_id, request in pending_interrupts.items():
            decisions = []
            
            for action_request in request["action_requests"]:
                decision = await self.hitl_handler.request_approval(
                    action_request,
                    session_id=self._current_session_id,
                )
                decisions.append(decision)
                
                if decision.get("type") == "reject":
                    return None  # 用户拒绝
            
            hitl_response[interrupt_id] = {"decisions": decisions}
        
        return hitl_response
    
    def _auto_approve_all(self, pending_interrupts: dict) -> dict:
        """自动批准所有请求"""
        return {
            interrupt_id: {
                "decisions": [
                    {"type": "approve"}
                    for _ in request["action_requests"]
                ]
            }
            for interrupt_id, request in pending_interrupts.items()
        }
```

### 3.3 事件系统

```python
# dataagent_core/events/base.py

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class ExecutionEvent:
    """执行事件基类"""
    event_type: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            **self._extra_fields(),
        }
    
    def _extra_fields(self) -> dict:
        """子类实现，返回额外字段"""
        return {}


# dataagent_core/events/text.py

@dataclass
class TextEvent(ExecutionEvent):
    """文本输出事件"""
    content: str = ""
    is_final: bool = False
    
    def _extra_fields(self) -> dict:
        return {
            "content": self.content,
            "is_final": self.is_final,
        }


# dataagent_core/events/tool.py

@dataclass
class ToolCallEvent(ExecutionEvent):
    """工具调用事件"""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_call_id: str = ""
    
    def _extra_fields(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_call_id": self.tool_call_id,
        }


@dataclass
class ToolResultEvent(ExecutionEvent):
    """工具结果事件"""
    tool_call_id: str = ""
    result: Any = None
    status: str = "success"
    
    def _extra_fields(self) -> dict:
        return {
            "tool_call_id": self.tool_call_id,
            "result": self.result,
            "status": self.status,
        }


# dataagent_core/events/hitl.py

@dataclass
class HITLRequestEvent(ExecutionEvent):
    """HITL 请求事件"""
    interrupt_id: str = ""
    action_requests: list = field(default_factory=list)
    
    def _extra_fields(self) -> dict:
        return {
            "interrupt_id": self.interrupt_id,
            "action_requests": self.action_requests,
        }


# dataagent_core/events/file.py

@dataclass
class FileOperationEvent(ExecutionEvent):
    """文件操作事件"""
    operation: str = ""  # read, write, edit
    file_path: str = ""
    metrics: dict = field(default_factory=dict)
    diff: str | None = None
    status: str = "success"
    
    def _extra_fields(self) -> dict:
        return {
            "operation": self.operation,
            "file_path": self.file_path,
            "metrics": self.metrics,
            "diff": self.diff,
            "status": self.status,
        }


# dataagent_core/events/system.py

@dataclass
class TodoUpdateEvent(ExecutionEvent):
    """Todo 更新事件"""
    todos: list = field(default_factory=list)
    
    def _extra_fields(self) -> dict:
        return {"todos": self.todos}


@dataclass
class ErrorEvent(ExecutionEvent):
    """错误事件"""
    error: str = ""
    recoverable: bool = True
    
    def _extra_fields(self) -> dict:
        return {
            "error": self.error,
            "recoverable": self.recoverable,
        }


@dataclass
class DoneEvent(ExecutionEvent):
    """完成事件"""
    token_usage: dict | None = None
    cancelled: bool = False
    
    def _extra_fields(self) -> dict:
        return {
            "token_usage": self.token_usage,
            "cancelled": self.cancelled,
        }
```

### 3.4 HITL 协议

```python
# dataagent_core/hitl/protocol.py

from typing import Protocol, TypedDict
from abc import abstractmethod


class ActionRequest(TypedDict):
    """操作请求"""
    name: str
    args: dict
    description: str


class Decision(TypedDict):
    """审批决定"""
    type: str  # approve, reject
    message: str | None


class HITLHandler(Protocol):
    """HITL 处理器协议"""
    
    @abstractmethod
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """
        请求用户审批
        
        Args:
            action_request: 操作请求
            session_id: 会话 ID
            
        Returns:
            用户决定
        """
        ...
    
    async def notify_auto_approved(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> None:
        """
        通知自动审批（可选实现）
        
        Args:
            action_request: 操作请求
            session_id: 会话 ID
        """
        pass


# dataagent_core/hitl/auto_approve.py

class AutoApproveHandler:
    """自动审批处理器"""
    
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        return {"type": "approve", "message": None}
```

### 3.5 会话管理

```python
# dataagent_core/session/state.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Session:
    """会话"""
    session_id: str
    user_id: str
    assistant_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    state: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


# dataagent_core/session/store.py

from abc import ABC, abstractmethod


class SessionStore(ABC):
    """会话存储抽象"""
    
    @abstractmethod
    async def create(self, user_id: str, assistant_id: str) -> Session:
        ...
    
    @abstractmethod
    async def get(self, session_id: str) -> Session | None:
        ...
    
    @abstractmethod
    async def update(self, session: Session) -> None:
        ...
    
    @abstractmethod
    async def delete(self, session_id: str) -> None:
        ...
    
    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Session]:
        ...


# dataagent_core/session/manager.py

class SessionManager:
    """会话管理器"""
    
    def __init__(
        self,
        store: SessionStore,
        agent_factory: AgentFactory,
    ):
        self.store = store
        self.agent_factory = agent_factory
        self._executors: dict[str, AgentExecutor] = {}
    
    async def get_or_create_session(
        self,
        user_id: str,
        assistant_id: str,
        session_id: str | None = None,
    ) -> Session:
        """获取或创建会话"""
        if session_id:
            session = await self.store.get(session_id)
            if session:
                return session
        
        return await self.store.create(user_id, assistant_id)
    
    async def get_executor(
        self,
        session: Session,
        config: AgentConfig,
        hitl_handler: HITLHandler | None = None,
    ) -> AgentExecutor:
        """获取会话对应的执行器"""
        if session.session_id in self._executors:
            return self._executors[session.session_id]
        
        agent, backend = self.agent_factory.create_agent(config)
        executor = AgentExecutor(
            agent=agent,
            backend=backend,
            hitl_handler=hitl_handler,
            assistant_id=session.assistant_id,
        )
        
        self._executors[session.session_id] = executor
        return executor
```

### 3.6 依赖关系

```
pyproject.toml 依赖:

[project]
name = "dataagent-core"
dependencies = [
    "deepagents>=0.2.8",
    "langchain>=1.0.7",
    "langchain-openai>=0.1.0",
    "langchain-anthropic>=0.1.0",
    "langgraph>=0.2.0",
    "requests>=2.31.0",
    "tavily-python>=0.3.0",
    "markdownify>=0.13.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
sandbox = [
    "modal>=0.65.0",
    "daytona>=0.113.0",
    "runloop-api-client>=0.69.0",
]
redis = [
    "redis>=5.0.0",
]
```

---

下一章：[04-dataagent-server.md](./04-dataagent-server.md) - DataAgentServer 详细设计
