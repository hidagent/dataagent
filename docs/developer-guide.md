# 开发人员手册

本文档帮助新同学快速参与 DataAgent 项目的开发和维护。

## 目录

1. [开发环境搭建](#开发环境搭建)
2. [开发模式快速启动](#开发模式快速启动)
3. [项目结构](#项目结构)
4. [核心概念](#核心概念)
5. [开发流程](#开发流程)
6. [代码规范](#代码规范)
7. [测试指南](#测试指南)
8. [常见问题](#常见问题)

---

## 开发环境搭建

### 开发模式默认配置

为了简化开发人员的配置工作，开发模式下使用以下默认配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 默认用户 | `dataagent` | Demo 默认使用此用户，无需注册登录 |
| 默认密码 | `dataagent` | 开发模式下的默认密码 |
| 数据库 | SQLite | 自动创建 `~/.dataagent/dataagent.db` |
| 认证 | 禁用 | `auth_disabled=True`，无需 API Key |

**数据存储位置**：
- 数据库文件：`~/.dataagent/dataagent.db`
- Agent 数据：`~/.deepagents/`

**环境变量覆盖**（可选）：
```bash
# 切换到 MySQL 存储
export DATAAGENT_SESSION_STORE=mysql
export DATAAGENT_MYSQL_HOST=localhost
export DATAAGENT_MYSQL_USER=root
export DATAAGENT_MYSQL_PASSWORD=password
export DATAAGENT_MYSQL_DATABASE=dataagent

# 启用认证
export DATAAGENT_AUTH_DISABLED=false
export DATAAGENT_API_KEYS='["your-api-key"]'
```

### 1. 环境要求

- Python 3.11+
- Git
- 推荐使用 VS Code 或 PyCharm

### 2. 克隆项目

```bash
git clone <repository-url>
cd dataagent
```

### 3. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 4. 安装开发依赖

```bash
# 安装所有组件（开发模式，按依赖顺序）
pip install -e source/dataagent-core[test]
pip install -e source/dataagent-cli
pip install -e source/dataagent-server[dev]
pip install -e source/dataagent-harbor[dev]

# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov hypothesis
```

### 5. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置 API Keys
```

### 6. 验证安装

```bash
# 运行测试
pytest source/dataagent-core/tests -v
pytest source/dataagent-server/tests -v
```

---

## 开发模式快速启动

项目提供了两种快速启动方式，方便开发调试时快速验证代码修改效果。

### 方式一：使用 Makefile

```bash
# 查看所有可用命令
make help
```

**安装命令**：

```bash
# 安装所有包（开发模式）
make install

# 安装包含开发依赖
make install-dev

# 强制重新安装（代码修改后）
make reinstall
```

**运行命令**：

```bash
# 运行 CLI
make run-cli                        # 启动交互式 CLI
make run-cli-agent AGENT=mybot      # 使用指定 Agent
make run-cli-auto                   # 启用自动审批模式
make cli-help                       # 显示 CLI 帮助

# 运行 Server（带热重载，代码修改自动生效）
make run-server                     # 默认端口 8000
make run-server-port PORT=9000      # 自定义端口

# 运行 Demo（带热重载）
make run-demo                       # 启动 Streamlit Demo

# 运行 Server + Demo（推荐，开发时最常用）
make run-dev                        # 同时启动 Server 和 Demo
```

**测试命令**：

```bash
make test                           # 运行所有测试
make test-core                      # 仅运行 Core 测试
make test-server                    # 仅运行 Server 测试
make test-harbor                    # 仅运行 Harbor 测试
make test-cov                       # 运行测试并生成覆盖率报告
make test-file FILE=path/to/test.py # 运行指定测试文件
```

**代码质量**：

```bash
make lint                           # 运行代码检查
make format                         # 格式化代码
make typecheck                      # 类型检查
make clean                          # 清理缓存文件
```

### 方式二：使用开发脚本

```bash
# 查看帮助
./scripts/dev.sh help
```

**运行 CLI**：

```bash
./scripts/dev.sh cli                    # 启动 CLI
./scripts/dev.sh cli --agent mybot      # 使用指定 Agent
./scripts/dev.sh cli --auto-approve     # 自动审批模式
./scripts/dev.sh cli help               # 显示 CLI 帮助
```

**运行 Server**：

```bash
./scripts/dev.sh server                 # 启动 Server（端口 8000，热重载）
./scripts/dev.sh server --port 9000     # 自定义端口
```

**运行 Demo**：

```bash
./scripts/dev.sh demo                   # 仅启动 Demo
./scripts/dev.sh dev                    # 同时启动 Server + Demo（推荐）
./scripts/dev.sh dev 9000               # 使用自定义端口启动 Server + Demo
```

**运行测试**：

```bash
./scripts/dev.sh test                   # 运行所有测试
./scripts/dev.sh test core              # 仅运行 Core 测试
./scripts/dev.sh test server            # 仅运行 Server 测试
./scripts/dev.sh test harbor            # 仅运行 Harbor 测试
```

**安装**：

```bash
./scripts/dev.sh install                # 安装所有包
```

### 开发工作流示例

**场景 1：修改 CLI 代码后验证**

```bash
# 修改 source/dataagent-cli/dataagent_cli/commands.py 后
./scripts/dev.sh cli help               # 立即查看效果，无需重新安装
```

**场景 2：修改 Server 代码后验证（推荐方式）**

```bash
# 启动 Server + Demo（最常用的开发方式）
./scripts/dev.sh dev

# 修改 source/dataagent-server/dataagent_server/api/v1/chat.py
# Server 会自动重载，在 Demo 页面刷新即可看到效果
# 按 Ctrl+C 同时停止 Server 和 Demo
```

**场景 3：仅修改 Server 代码**

```bash
# 启动 Server（热重载模式）
make run-server

# 修改 source/dataagent-server/dataagent_server/api/v1/chat.py
# Server 会自动重载，无需重启
```

**场景 4：修改 Core 代码后验证**

```bash
# 启动开发环境
./scripts/dev.sh dev

# 修改 source/dataagent-core/dataagent_core/events/__init__.py
# Server 会自动检测到 Core 代码变化并重载，无需重新安装！

# 如果需要运行测试
make test-core                          # 运行测试验证
```

**场景 5：修改 Demo 代码后验证**

```bash
# 启动 Demo（热重载模式）
./scripts/dev.sh demo

# 修改 source/dataagent-server-demo/dataagent_server_demo/app.py
# Demo 会自动重载，浏览器自动刷新
```

### 特点说明

| 特点 | 说明 |
|------|------|
| 自动设置 PYTHONPATH | 脚本自动配置路径，无需手动设置 |
| Core 热重载 | 修改 `dataagent-core` 代码后，Server 自动重载，无需重新安装 |
| Server 热重载 | 修改 `dataagent-server` 代码后自动重载 |
| Demo 热重载 | 修改 Demo 代码后浏览器自动刷新 |
| 无需重装 | 所有模块修改后只需重启或等待自动重载 |

---

## 项目结构

```
dataagent/
├── source/                        # DataAgent 源代码
│   ├── dataagent-core/            # 核心业务逻辑
│   │   ├── dataagent_core/
│   │   │   ├── engine/            # Agent 工厂和执行器
│   │   │   ├── events/            # 事件系统
│   │   │   ├── middleware/        # 中间件
│   │   │   ├── tools/             # 工具系统
│   │   │   ├── hitl/              # HITL 协议
│   │   │   ├── session/           # 会话管理
│   │   │   ├── mcp/               # MCP 集成
│   │   │   └── config/            # 配置管理
│   │   └── tests/
│   │
│   ├── dataagent-cli/             # CLI 客户端
│   │   ├── dataagent_cli/
│   │   │   ├── renderer.py        # 终端渲染
│   │   │   ├── hitl.py            # 终端 HITL
│   │   │   └── main.py            # 入口
│   │   └── tests/
│   │
│   ├── dataagent-server/          # Web 服务
│   │   ├── dataagent_server/
│   │   │   ├── api/v1/            # REST API (chat, sessions, mcp, users)
│   │   │   ├── ws/                # WebSocket
│   │   │   ├── auth/              # API Key 认证
│   │   │   ├── hitl/              # WebSocket HITL 处理
│   │   │   ├── models/            # Pydantic 数据模型
│   │   │   └── config/            # 配置
│   │   └── tests/
│   │
│   ├── dataagent-harbor/          # 测试框架
│   └── dataagent-server-demo/     # Streamlit Demo 应用
│
├── libs/                          # 依赖库 (deepagents, deepagents-cli, harbor)
├── docs/                          # 文档
└── .kiro/specs/                   # 需求和设计文档
```

---

## 核心概念

### 1. 事件系统

所有 Agent 执行过程通过事件流传递：

```python
from dataagent_core.events import (
    ExecutionEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    HITLRequestEvent,
    DoneEvent,
)

# 事件都继承自 ExecutionEvent
# 每个事件都有 event_type 和 timestamp
# 通过 to_dict() 序列化为 JSON
```

**事件类型：**

| 事件 | 说明 |
|------|------|
| `TextEvent` | 文本输出 |
| `ToolCallEvent` | 工具调用 |
| `ToolResultEvent` | 工具结果 |
| `HITLRequestEvent` | HITL 请求 |
| `TodoUpdateEvent` | Todo 更新 |
| `FileOperationEvent` | 文件操作 |
| `ErrorEvent` | 错误 |
| `DoneEvent` | 完成 |

### 2. Agent 工厂

创建和配置 Agent：

```python
from dataagent_core.engine import AgentFactory, AgentConfig
from dataagent_core.config import Settings

settings = Settings.from_environment()
factory = AgentFactory(settings=settings)

config = AgentConfig(
    assistant_id="my-agent",
    enable_memory=True,
    enable_skills=True,
    auto_approve=False,
)

agent, backend = factory.create_agent(config)
```

### 3. 执行器

运行 Agent 并产生事件流：

```python
from dataagent_core.engine import AgentExecutor

executor = AgentExecutor(
    agent=agent,
    backend=backend,
    hitl_handler=hitl_handler,
)

async for event in executor.execute(user_input, session_id):
    # 处理事件
    print(event.to_dict())
```

### 4. HITL 协议

敏感操作需要用户审批：

```python
from dataagent_core.hitl import HITLHandler, ActionRequest, Decision

class MyHITLHandler:
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        # 实现审批逻辑
        return {"type": "approve", "message": None}
```

### 5. 会话管理

```python
from dataagent_core.session import SessionManager, MemorySessionStore

store = MemorySessionStore()
manager = SessionManager(store=store, agent_factory=factory)

session = await manager.get_or_create_session(
    user_id="user-1",
    assistant_id="my-agent",
)
```

---

## 开发流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 运行特定测试
pytest source/dataagent-core/tests/test_events -v

# 运行所有测试
pytest source/dataagent-core/tests -v
pytest source/dataagent-server/tests -v

# 带覆盖率
pytest source/dataagent-core/tests --cov=dataagent_core
```

### 3. 代码检查

```bash
# 类型检查
mypy source/dataagent-core/dataagent_core

# 格式化
black source/dataagent-core
isort source/dataagent-core
```

### 4. 提交代码

```bash
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
```

---

## 代码规范

### Python 风格

- 使用 Python 3.11+ 语法特性
- 遵循 PEP 8，行宽 100 字符
- 使用类型注解：`list[str]` 而非 `List[str]`
- 优先使用 `dataclass` 或 Pydantic `BaseModel`

### 命名规范

```python
# 类名：PascalCase
class AgentExecutor:
    pass

# 函数/方法：snake_case
def create_agent():
    pass

# 常量：UPPER_SNAKE_CASE
MAX_CONNECTIONS = 200

# 私有成员：前缀下划线
def _internal_method():
    pass
```

### 文档字符串

```python
def create_agent(self, config: AgentConfig) -> tuple[Pregel, CompositeBackend]:
    """创建配置好的 Agent。
    
    Args:
        config: Agent 配置对象。
        
    Returns:
        (agent, backend) 元组。
        
    Raises:
        ValueError: 如果配置无效。
    """
    pass
```

### 异步代码

```python
# 使用 async/await
async def execute(self, message: str) -> AsyncIterator[ExecutionEvent]:
    async for event in self._execute_stream():
        yield event

# 避免回调风格
```

---

## 测试指南

### 测试框架

- **pytest**: 主测试框架
- **pytest-asyncio**: 异步测试
- **hypothesis**: 属性测试

### 测试结构

```
tests/
├── conftest.py           # 共享 fixtures
├── test_events/
│   ├── test_serialization.py
│   └── test_properties.py
├── test_engine/
│   ├── test_factory.py
│   └── test_executor.py
└── test_api/
    └── test_endpoints.py
```

### 编写测试

```python
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# 单元测试
def test_text_event_contains_required_fields():
    event = TextEvent(content="hello", is_final=True)
    result = event.to_dict()
    assert "event_type" in result
    assert "content" in result

# 异步测试
@pytest.mark.asyncio
async def test_executor_returns_events():
    executor = create_test_executor()
    events = []
    async for event in executor.execute("test", "session-1"):
        events.append(event)
    assert len(events) > 0

# 属性测试
@settings(max_examples=100)
@given(content=st.text(), is_final=st.booleans())
def test_text_event_serialization_roundtrip(content, is_final):
    event = TextEvent(content=content, is_final=is_final)
    result = event.to_dict()
    assert result["content"] == content
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_events/test_serialization.py

# 运行特定测试
pytest tests/test_events/test_serialization.py::test_text_event

# 显示详细输出
pytest -v

# 带覆盖率报告
pytest --cov=dataagent_core --cov-report=html
```

---

## 常见问题

### Q: 如何添加新的事件类型？

1. 在 `dataagent_core/events/__init__.py` 中定义新事件类
2. 继承 `ExecutionEvent` 并实现 `_extra_fields()`
3. 注册事件类型用于反序列化
4. 添加测试

```python
@dataclass
class MyNewEvent(ExecutionEvent):
    event_type: str = field(default="my_new", init=False)
    my_field: str = ""
    
    def _extra_fields(self) -> dict:
        return {"my_field": self.my_field}
```

### Q: 如何添加新的中间件？

1. 在 `dataagent_core/middleware/` 中创建新文件
2. 实现 LangChain `AgentMiddleware` 协议
3. 在 `AgentFactory` 中添加配置选项

### Q: 如何添加新的 REST API 端点？

1. 在 `dataagent_server/api/v1/` 中创建或修改路由文件
2. 定义 Pydantic 请求/响应模型
3. 在 `main.py` 中注册路由
4. 添加测试

### Q: 如何调试 Agent 执行？

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 或使用 LangSmith 追踪
export LANGSMITH_API_KEY=xxx
export LANGSMITH_TRACING_V2=true
```

### Q: 如何配置 MCP Server？

MCP (Model Context Protocol) 配置支持两种模式：

**CLI 模式**：创建配置文件 `~/.deepagents/{assistant_id}/mcp.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/workspace"],
      "env": {},
      "disabled": false,
      "autoApprove": []
    },
    "database": {
      "command": "uvx",
      "args": ["mcp-server-mysql"],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "root"
      },
      "disabled": false,
      "autoApprove": ["query"]
    }
  }
}
```

**Server 模式**：通过 REST API 动态配置（每用户独立配置）

```bash
# 添加 MCP Server
curl -X POST http://localhost:8000/api/v1/users/{user_id}/mcp-servers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "filesystem",
    "command": "uvx",
    "args": ["mcp-server-filesystem", "/workspace"],
    "env": {},
    "disabled": false,
    "auto_approve": []
  }'

# 列出 MCP Servers
curl http://localhost:8000/api/v1/users/{user_id}/mcp-servers \
  -H "X-API-Key: your-api-key"

# 获取单个 MCP Server
curl http://localhost:8000/api/v1/users/{user_id}/mcp-servers/filesystem \
  -H "X-API-Key: your-api-key"

# 更新 MCP Server
curl -X PUT http://localhost:8000/api/v1/users/{user_id}/mcp-servers/filesystem \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "filesystem",
    "command": "uvx",
    "args": ["mcp-server-filesystem", "/new-workspace"],
    "disabled": false
  }'

# 删除 MCP Server
curl -X DELETE http://localhost:8000/api/v1/users/{user_id}/mcp-servers/filesystem \
  -H "X-API-Key: your-api-key"
```

**核心组件**：

| 组件 | 说明 |
|------|------|
| `MCPConfig` | MCP 配置数据模型，支持 JSON 序列化 |
| `MCPServerConfig` | 单个 MCP Server 配置 |
| `MCPConnectionManager` | 管理多用户 MCP 连接池 |
| `MCPConfigStore` | 配置存储抽象（支持内存/MySQL） |

**代码示例**：

```python
from dataagent_core.mcp import (
    MCPConfig,
    MCPServerConfig,
    MCPConnectionManager,
    MemoryMCPConfigStore,
)

# 创建配置
config = MCPConfig()
config.add_server(MCPServerConfig(
    name="filesystem",
    command="uvx",
    args=["mcp-server-filesystem", "/workspace"],
))

# 连接管理
manager = MCPConnectionManager(
    max_connections_per_user=10,
    max_total_connections=100,
)

# 为用户连接 MCP Servers
connections = await manager.connect(user_id="user-1", config=config)

# 获取用户的 MCP 工具
tools = manager.get_tools(user_id="user-1")
```

### Q: 如何实现多租户用户隔离？

DataAgent 已实现完整的多租户用户隔离机制：

**1. 会话隔离**

`SessionStore` 的查询方法自动按 `user_id` 过滤：

```python
from dataagent_core.session import SessionManager

manager = SessionManager(timeout_seconds=3600)
await manager.start()

# 获取用户会话（自动隔离）
session = await manager.get_or_create_session(
    user_id="user-123",
    assistant_id="my-agent",
)

# 列出用户会话（只返回该用户的会话）
sessions = await manager.list_user_sessions(user_id="user-123")
```

**2. 记忆隔离**

用户记忆存储在独立目录 `~/.deepagents/users/{user_id}/`：

```bash
# 查看用户记忆状态
curl http://localhost:8000/api/v1/users/{user_id}/memory/status \
  -H "X-API-Key: your-api-key"

# 清除用户记忆
curl -X DELETE http://localhost:8000/api/v1/users/{user_id}/memory \
  -H "X-API-Key: your-api-key"
```

**3. MCP 隔离**

每个用户独立的 MCP 连接池，通过 `MCPConnectionManager` 管理：

```python
from dataagent_core.mcp import MCPConnectionManager

manager = MCPConnectionManager(
    max_connections_per_user=10,   # 每用户最大连接数
    max_total_connections=100,     # 全局最大连接数
)

# 为用户连接 MCP（隔离的连接池）
await manager.connect(user_id="user-123", config=mcp_config)

# 获取用户的 MCP 工具（只返回该用户的工具）
tools = manager.get_tools(user_id="user-123")

# 断开用户的 MCP 连接
await manager.disconnect(user_id="user-123")
```

**4. API 访问控制**

REST API 自动验证用户权限：

```python
# 用户只能访问自己的资源
# 访问其他用户资源会返回 403 Forbidden
def _check_user_access(user_id: str, current_user_id: str) -> None:
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's resources",
        )
```

**隔离架构图**：

```
┌─────────────────────────────────────────────────────────────┐
│                    DataAgent Server                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User A                          User B                     │
│  ┌─────────────────┐            ┌─────────────────┐        │
│  │ Sessions        │            │ Sessions        │        │
│  │ Memory          │            │ Memory          │        │
│  │ MCP Connections │            │ MCP Connections │        │
│  │ MCP Config      │            │ MCP Config      │        │
│  └─────────────────┘            └─────────────────┘        │
│                                                             │
│  Storage: ~/.deepagents/users/user-a/                       │
│  Storage: ~/.deepagents/users/user-b/                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Q: 测试失败怎么办？

1. 检查环境变量是否配置正确
2. 确保依赖版本正确：`pip install -e source/dataagent-core[test]`
3. 查看测试输出的详细错误信息
4. 使用 `pytest -v --tb=long` 获取完整堆栈

---

## 参考资源

- [需求文档](.kiro/specs/dataagent-development-specs/requirements.md)
- [设计文档](.kiro/specs/dataagent-development-specs/design.md)
- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
