# 开发人员手册

本文档帮助新同学快速参与 DataAgent 项目的开发和维护。

## 目录

1. [开发环境搭建](#开发环境搭建)
2. [项目结构](#项目结构)
3. [核心概念](#核心概念)
4. [开发流程](#开发流程)
5. [代码规范](#代码规范)
6. [测试指南](#测试指南)
7. [常见问题](#常见问题)

---

## 开发环境搭建

### 1. 环境要求

- Python 3.11+
- Git
- 推荐使用 VS Code 或 PyCharm

### 2. 克隆项目

```bash
git clone <repository-url>
cd deepagents
```

### 3. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 4. 安装开发依赖

```bash
# 安装所有组件（开发模式）
pip install -e libs/dataagent-core[dev]
pip install -e libs/dataagent-cli[dev]
pip install -e libs/dataagent-server[dev]
pip install -e libs/dataagent-harbor[dev]

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
pytest libs/dataagent-core/tests -v
pytest libs/dataagent-server/tests -v
```

---

## 项目结构

```
deepagents/
├── libs/                          # 核心库
│   ├── dataagent-core/            # 核心业务逻辑
│   │   ├── dataagent_core/
│   │   │   ├── engine/            # Agent 工厂和执行器
│   │   │   ├── events/            # 事件系统
│   │   │   ├── middleware/        # 中间件
│   │   │   ├── tools/             # 工具系统
│   │   │   ├── hitl/              # HITL 协议
│   │   │   ├── session/           # 会话管理
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
│   │   │   ├── api/v1/            # REST API
│   │   │   ├── ws/                # WebSocket
│   │   │   ├── auth/              # 认证
│   │   │   ├── models/            # 数据模型
│   │   │   └── config/            # 配置
│   │   └── tests/
│   │
│   ├── dataagent-harbor/          # 测试框架
│   └── dataagent-server-demo/     # Demo 应用
│
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
pytest libs/dataagent-core/tests/test_events -v

# 运行所有测试
pytest libs/dataagent-core/tests -v
pytest libs/dataagent-server/tests -v

# 带覆盖率
pytest libs/dataagent-core/tests --cov=dataagent_core
```

### 3. 代码检查

```bash
# 类型检查
mypy libs/dataagent-core/dataagent_core

# 格式化
black libs/dataagent-core
isort libs/dataagent-core
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

### Q: 如何配置 MCP Server？（规划中）

**CLI 模式**：创建配置文件 `~/.deepagents/{assistant_id}/mcp.json`

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/workspace"],
      "env": {},
      "disabled": false,
      "timeout": 30
    },
    {
      "name": "database",
      "command": "uvx",
      "args": ["mcp-server-mysql"],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "root"
      },
      "disabled": false
    }
  ]
}
```

**Server 模式**：通过 REST API 动态配置

```bash
# 添加 MCP Server
curl -X POST http://localhost:8000/api/v1/users/{user_id}/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem",
    "command": "uvx",
    "args": ["mcp-server-filesystem", "/workspace"]
  }'

# 列出 MCP Servers
curl http://localhost:8000/api/v1/users/{user_id}/mcp-servers

# 删除 MCP Server
curl -X DELETE http://localhost:8000/api/v1/users/{user_id}/mcp-servers/filesystem
```

### Q: 如何实现多租户用户隔离？（规划中）

1. **会话隔离**：`SessionStore` 的查询方法自动按 `user_id` 过滤
2. **记忆隔离**：`AgentMemoryMiddleware` 存储路径包含 `user_id`
3. **文件隔离**：使用 `SandboxedFilesystemBackend` 限制操作范围
4. **MCP 隔离**：每个用户独立的 MCP 连接池

```python
# 创建用户隔离的 Agent
config = AgentConfig(
    assistant_id="my-agent",
    user_id="user-123",  # 指定用户 ID
    workspace_root=Path("/data/workspaces/user-123"),  # 用户工作区
)
```

### Q: 测试失败怎么办？

1. 检查环境变量是否配置正确
2. 确保依赖版本正确：`pip install -e libs/dataagent-core[dev]`
3. 查看测试输出的详细错误信息
4. 使用 `pytest -v --tb=long` 获取完整堆栈

---

## 参考资源

- [需求文档](.kiro/specs/dataagent-development-specs/requirements.md)
- [设计文档](.kiro/specs/dataagent-development-specs/design.md)
- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
