# DataAgent 架构设计方案

## 第二章：deepagents_cli 可拆解性分析

### 2.1 现有模块清单

```
deepagents_cli/
├── __init__.py              # 入口导出
├── __main__.py              # python -m 入口
├── main.py                  # CLI 主循环
├── agent.py                 # Agent 创建
├── agent_memory.py          # 长期记忆中间件
├── commands.py              # 斜杠命令处理
├── config.py                # 配置和设置
├── execution.py             # 任务执行
├── file_ops.py              # 文件操作追踪
├── input.py                 # 终端输入处理
├── shell.py                 # Shell 中间件
├── token_utils.py           # Token 计算
├── tools.py                 # 自定义工具
├── ui.py                    # 终端 UI 渲染
├── default_agent_prompt.md  # 默认提示词
├── skills/                  # 技能系统
│   ├── __init__.py
│   ├── commands.py          # 技能命令
│   ├── load.py              # 技能加载
│   └── middleware.py        # 技能中间件
└── integrations/            # 沙箱集成
    ├── __init__.py
    ├── daytona.py
    ├── modal.py
    ├── runloop.py
    └── sandbox_factory.py
```

### 2.2 模块分类与复用性评估

#### 2.2.1 核心模块（可完全复用）

| 模块 | 功能 | 复用方式 | 改动量 |
|------|------|---------|--------|
| `agent.py` | Agent 创建工厂 | 直接迁移 | 低 |
| `agent_memory.py` | 长期记忆中间件 | 直接迁移 | 低 |
| `shell.py` | Shell 执行中间件 | 直接迁移 | 无 |
| `file_ops.py` | 文件操作追踪和 Diff | 直接迁移 | 无 |
| `tools.py` | Web 工具 (search, fetch, http) | 直接迁移 | 无 |
| `token_utils.py` | Token 计算 | 直接迁移 | 无 |
| `skills/middleware.py` | 技能中间件 | 直接迁移 | 低 |
| `skills/load.py` | 技能加载器 | 直接迁移 | 无 |
| `integrations/*` | 沙箱集成 | 直接迁移 | 无 |

#### 2.2.2 混合模块（需拆分）

| 模块 | 可复用部分 | CLI 特有部分 |
|------|-----------|-------------|
| `config.py` | Settings 类、模型创建 | COLORS、ASCII_ART、console |
| `execution.py` | 核心执行逻辑、事件处理 | 终端渲染、termios HITL |

#### 2.2.3 CLI 特有模块（不复用）

| 模块 | 功能 | 说明 |
|------|------|------|
| `main.py` | CLI 主循环 | 终端特有 |
| `commands.py` | 斜杠命令 | 终端特有 |
| `input.py` | 输入处理、自动补全 | 终端特有 |
| `ui.py` | 终端 UI 渲染 | 终端特有 |
| `skills/commands.py` | 技能 CLI 命令 | 终端特有 |

### 2.3 关键模块详细分析

#### 2.3.1 agent.py 分析

```python
# 核心函数 - 可完全复用
def create_cli_agent(
    model: str | BaseChatModel,
    assistant_id: str,
    *,
    tools: list[BaseTool] | None = None,
    sandbox: SandboxBackendProtocol | None = None,
    sandbox_type: str | None = None,
    system_prompt: str | None = None,
    auto_approve: bool = False,
    enable_memory: bool = True,
    enable_skills: bool = True,
    enable_shell: bool = True,
) -> tuple[Pregel, CompositeBackend]:
    """
    这个函数是核心，可以直接迁移到 DataAgentCore
    只需要：
    1. 移除对 console 的依赖
    2. 将 settings 作为参数传入而非全局变量
    """
```

**迁移策略**：
- 重命名为 `AgentFactory.create_agent()`
- 将 `settings` 改为依赖注入
- 移除 `console.print()` 调用

#### 2.3.2 execution.py 分析

```python
# 核心执行逻辑 - 需要抽象
async def execute_task(
    user_input: str,
    agent,
    assistant_id: str | None,
    session_state,
    token_tracker: TokenTracker | None = None,
    backend=None,
) -> None:
    """
    这个函数混合了：
    1. 核心执行逻辑（可复用）
    2. 终端渲染（CLI 特有）
    3. HITL 交互（需抽象）
    """
```

**拆分策略**：

```python
# DataAgentCore - 核心执行器
class AgentExecutor:
    async def execute(self, user_input, session_id) -> AsyncIterator[ExecutionEvent]:
        """返回事件流，不做任何渲染"""
        ...

# DataAgentCli - 终端渲染
class TerminalRenderer:
    async def render_events(self, events: AsyncIterator[ExecutionEvent]):
        """将事件渲染到终端"""
        ...

# DataAgentServer - WebSocket 推送
class WebSocketPusher:
    async def push_events(self, events: AsyncIterator[ExecutionEvent], ws):
        """将事件推送到 WebSocket"""
        ...
```

#### 2.3.3 config.py 分析

```python
# 可复用部分
@dataclass
class Settings:
    """全局设置 - 可复用"""
    openai_api_key: str | None
    anthropic_api_key: str | None
    # ...

def create_model() -> BaseChatModel:
    """模型创建 - 可复用"""
    ...

# CLI 特有部分
COLORS = {...}           # 终端颜色
DEEP_AGENTS_ASCII = ...  # ASCII 艺术
console = Console()      # Rich console
```

**拆分策略**：
- `Settings` 和 `create_model()` 迁移到 Core
- `COLORS`、`console` 等保留在 CLI

### 2.4 HITL (Human-in-the-Loop) 抽象

现有实现（CLI 特有）：

```python
# execution.py - 使用 termios 实现终端交互
def prompt_for_tool_approval(action_request, assistant_id) -> Decision:
    """终端 HITL - 使用方向键选择"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    # ... 终端交互逻辑
```

**抽象为协议**：

```python
# DataAgentCore - HITL 协议
class HITLHandler(Protocol):
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """请求用户审批 - 不同端实现不同"""
        ...

# CLI 实现
class TerminalHITLHandler(HITLHandler):
    async def request_approval(self, action_request, session_id):
        # 使用 termios 实现
        ...

# Server 实现
class WebSocketHITLHandler(HITLHandler):
    async def request_approval(self, action_request, session_id):
        # 发送到前端，等待响应
        await self.send_to_client(session_id, action_request)
        return await self.wait_for_decision(session_id)
```

### 2.5 事件系统设计

将执行过程抽象为事件流：

```python
# 事件类型
@dataclass
class ExecutionEvent:
    event_type: str
    timestamp: float

@dataclass
class TextEvent(ExecutionEvent):
    """文本输出"""
    content: str
    is_final: bool = False

@dataclass
class ToolCallEvent(ExecutionEvent):
    """工具调用"""
    tool_name: str
    tool_args: dict
    tool_call_id: str

@dataclass
class ToolResultEvent(ExecutionEvent):
    """工具结果"""
    tool_call_id: str
    result: Any
    status: str  # success, error

@dataclass
class HITLRequestEvent(ExecutionEvent):
    """HITL 请求"""
    interrupt_id: str
    action_requests: list[ActionRequest]

@dataclass
class TodoUpdateEvent(ExecutionEvent):
    """Todo 更新"""
    todos: list[dict]

@dataclass
class FileOperationEvent(ExecutionEvent):
    """文件操作"""
    operation: str  # read, write, edit
    file_path: str
    metrics: FileOpMetrics
    diff: str | None = None

@dataclass
class ErrorEvent(ExecutionEvent):
    """错误"""
    error: str
    recoverable: bool = True

@dataclass
class DoneEvent(ExecutionEvent):
    """完成"""
    token_usage: dict | None = None
```

### 2.6 拆解结论

| 指标 | 数值 |
|------|------|
| 总代码行数 | ~3500 行 |
| 可复用代码 | ~2500 行 (71%) |
| 需重构代码 | ~500 行 (14%) |
| CLI 特有代码 | ~500 行 (14%) |

**结论：可以拆解**，主要工作：
1. 将核心模块迁移到 DataAgentCore
2. 抽象 HITL 协议
3. 设计事件系统
4. 拆分 config.py 和 execution.py

---

下一章：[03-dataagent-core.md](./03-dataagent-core.md) - DataAgentCore 详细设计
