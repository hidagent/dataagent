# DataAgent 多租户隔离设计

## 概述

DataAgent 实现了完整的多租户隔离，确保不同租户的数据、配置和资源完全隔离。本文档描述了各个模块的隔离机制。

## 隔离架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DataAgent 多租户系统                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │   Tenant A      │  │   Tenant B      │  │   Tenant C      │      │
│  │  (user_id: a)   │  │  (user_id: b)   │  │  (user_id: c)   │      │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │
│           │                    │                    │                │
│  ┌────────▼────────────────────▼────────────────────▼────────┐      │
│  │                    隔离层                                   │      │
│  ├───────────────────────────────────────────────────────────┤      │
│  │  1. 用户档案隔离 (UserProfileStore)                        │      │
│  │  2. 会话隔离 (SessionStore)                                │      │
│  │  3. 消息隔离 (MessageStore)                                │      │
│  │  4. MCP 配置隔离 (MCPConfigStore)                          │      │
│  │  5. MCP 连接隔离 (MCPConnectionManager)                    │      │
│  │  6. 规则隔离 (RuleStore)                                   │      │
│  │  7. 文件系统隔离 (FileSystem)                              │      │
│  └───────────────────────────────────────────────────────────┘      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 1. 用户档案隔离

### 1.1 设计

每个租户有独立的用户档案，存储用户的基本信息和自定义字段。

```python
# UserProfileStore 按 user_id 隔离
class UserProfileStore(ABC):
    async def get_profile(self, user_id: str) -> UserProfile | None
    async def save_profile(self, profile: UserProfile) -> None
    async def delete_profile(self, user_id: str) -> bool
```

### 1.2 数据模型

```python
@dataclass
class UserProfile:
    user_id: str           # 租户唯一标识
    username: str          # 登录用户名
    display_name: str      # 显示名称
    email: str | None      # 邮箱（敏感信息）
    department: str | None # 部门
    role: str | None       # 角色
    custom_fields: dict    # 自定义字段
```

### 1.3 隔离保证

- 每个 `user_id` 有独立的档案
- 敏感信息（如 email）不会注入到 LLM prompt
- 用户上下文只包含当前用户的信息

## 2. 会话隔离

### 2.1 设计

每个租户的会话完全隔离，一个租户无法访问另一个租户的会话。

```python
# SessionStore 按 user_id 隔离
class SessionStore(ABC):
    async def create(self, user_id: str, assistant_id: str) -> Session
    async def list_by_user(self, user_id: str) -> list[Session]
```

### 2.2 数据模型

```python
@dataclass
class Session:
    session_id: str        # 会话唯一标识
    user_id: str           # 租户标识（隔离键）
    assistant_id: str      # 助手标识
    created_at: datetime   # 创建时间
    last_active: datetime  # 最后活跃时间
    state: dict            # 会话状态
    metadata: dict         # 元数据
```

### 2.3 隔离保证

- 会话按 `user_id` 分组
- `list_by_user()` 只返回该用户的会话
- 会话 ID 是全局唯一的，但只有所有者可以访问

## 3. 消息隔离

### 3.1 设计

消息通过 `session_id` 间接实现租户隔离。

```python
# MessageStore 按 session_id 隔离
class MessageStore(ABC):
    async def save_message(self, session_id: str, role: str, content: str)
    async def get_messages(self, session_id: str) -> list[Message]
    async def delete_messages(self, session_id: str) -> int
```

### 3.2 隔离保证

- 消息属于特定会话
- 会话属于特定用户
- 因此消息间接按用户隔离

## 4. MCP 配置隔离

### 4.1 设计

每个租户有独立的 MCP 服务器配置。

```python
# MCPConfigStore 按 user_id 隔离
class MCPConfigStore(ABC):
    async def get_user_config(self, user_id: str) -> MCPConfig
    async def save_user_config(self, user_id: str, config: MCPConfig)
    async def add_server(self, user_id: str, server: MCPServerConfig)
    async def remove_server(self, user_id: str, server_name: str)
```

### 4.2 隔离保证

- 每个租户有独立的 MCP 服务器列表
- 凭证（API keys、tokens）按租户隔离
- 一个租户无法访问另一个租户的 MCP 配置

## 5. MCP 连接隔离

### 5.1 设计

每个租户有独立的 MCP 连接池。

```python
# MCPConnectionManager 按 user_id 隔离
class MCPConnectionManager:
    # user_id -> {server_name -> MCPConnection}
    _connections: dict[str, dict[str, MCPConnection]]
    
    async def connect(self, user_id: str, config: MCPConfig)
    def get_tools(self, user_id: str) -> list[BaseTool]
    async def disconnect(self, user_id: str, server_name: str)
```

### 5.2 隔离保证

- 每个租户有独立的连接池
- 工具按租户隔离
- 连接数限制按租户计算

## 6. 规则隔离

### 6.1 设计

规则按三个层级存储，其中用户级别按 `user_id` 隔离。

```python
# FileRuleStore 支持多层级规则
class FileRuleStore(RuleStore):
    def __init__(
        self,
        global_dir: Path,    # 全局规则：~/.dataagent/rules/
        user_dir: Path,      # 用户规则：~/.dataagent/users/{user_id}/rules/
        project_dir: Path,   # 项目规则：{project}/.dataagent/rules/
    )
```

### 6.2 规则层级

| 层级 | 路径 | 范围 | 隔离 |
|------|------|------|------|
| Global | `~/.dataagent/rules/` | 所有用户 | 共享 |
| User | `~/.dataagent/users/{user_id}/rules/` | 特定用户 | 按 user_id |
| Project | `{project}/.dataagent/rules/` | 特定项目 | 按项目 |

### 6.3 隔离保证

- 用户级规则按 `user_id` 隔离
- 规则优先级：Project > User > Global
- 用户可以覆盖全局规则

## 7. 文件系统隔离

### 7.1 设计

每个租户有独立的文件系统目录。

```
~/.dataagent/
├── rules/                          # 全局规则（共享）
├── users/
│   ├── alice/                      # 租户 Alice
│   │   ├── rules/                  # Alice 的规则
│   │   ├── mcp.json                # Alice 的 MCP 配置
│   │   ├── agent.md                # Alice 的 Agent 记忆
│   │   └── skills/                 # Alice 的技能
│   ├── bob/                        # 租户 Bob
│   │   ├── rules/                  # Bob 的规则
│   │   ├── mcp.json                # Bob 的 MCP 配置
│   │   ├── agent.md                # Bob 的 Agent 记忆
│   │   └── skills/                 # Bob 的技能
│   └── charlie/                    # 租户 Charlie
│       └── ...
└── config/                         # 全局配置（共享）
```

### 7.2 隔离保证

- 每个租户有独立的目录
- 文件操作限制在租户目录内
- 防止路径遍历攻击

## 8. API 权限隔离

### 8.1 设计

所有 API 端点都进行权限检查。

```python
def _check_user_access(user_id: str, current_user_id: str) -> None:
    """检查用户是否有权访问目标用户的资源"""
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's resources",
        )
```

### 8.2 隔离保证

- 用户只能访问自己的资源
- 管理员可以访问所有资源
- 所有 API 端点都进行权限检查

## 9. 资源配额隔离

### 9.1 设计

每个租户有独立的资源配额。

```python
# 资源限制配置
RESOURCE_LIMITS = {
    "max_sessions_per_user": 100,
    "max_messages_per_session": 1000,
    "max_mcp_connections_per_user": 10,
    "max_rules_per_user": 50,
    "max_storage_per_user_mb": 100,
}
```

### 9.2 隔离保证

- 每个租户有独立的配额
- 一个租户无法耗尽其他租户的资源
- 超出配额时返回错误

## 隔离矩阵

| 资源类型 | 隔离键 | 存储方式 | 隔离级别 |
|---------|--------|---------|---------|
| 用户档案 | `user_id` | 数据库 | 完全隔离 |
| 会话 | `user_id` | 数据库 | 完全隔离 |
| 消息 | `session_id` | 数据库 | 间接隔离 |
| MCP 配置 | `user_id` | 数据库/文件 | 完全隔离 |
| MCP 连接 | `user_id` | 内存 | 完全隔离 |
| 规则 | `user_id` | 文件系统 | 分层隔离 |
| 文件 | `user_id` | 文件系统 | 目录隔离 |
| API 访问 | `user_id` | 运行时 | 权限检查 |

## 安全建议

### 1. 数据库隔离

```sql
-- 所有表都应该有 user_id 字段
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,  -- 隔离键
    ...
    INDEX idx_user_id (user_id)
);

-- 所有查询都应该包含 user_id 过滤
SELECT * FROM sessions WHERE user_id = :user_id;
```

### 2. 文件系统隔离

```python
def get_user_dir(user_id: str) -> Path:
    """获取用户目录，防止路径遍历"""
    # 验证 user_id 格式
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        raise ValueError(f"Invalid user_id: {user_id}")
    
    # 返回用户目录
    return Path.home() / ".dataagent" / "users" / user_id
```

### 3. API 隔离

```python
@router.get("/users/{user_id}/sessions")
async def list_sessions(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    # 权限检查
    _check_user_access(user_id, current_user_id)
    
    # 只返回该用户的会话
    return await session_store.list_by_user(user_id)
```

### 4. 日志隔离

```python
# 日志中包含 user_id，便于审计
logger.info(f"User {user_id} created session {session_id}")
logger.warning(f"User {user_id} attempted to access {target_user_id}'s resources")
```

## 测试验证

### 1. 隔离性测试

```python
async def test_user_isolation():
    """验证用户隔离"""
    # Alice 创建会话
    alice_session = await session_store.create("alice", "assistant")
    
    # Bob 创建会话
    bob_session = await session_store.create("bob", "assistant")
    
    # Alice 只能看到自己的会话
    alice_sessions = await session_store.list_by_user("alice")
    assert len(alice_sessions) == 1
    assert alice_sessions[0].session_id == alice_session.session_id
    
    # Bob 只能看到自己的会话
    bob_sessions = await session_store.list_by_user("bob")
    assert len(bob_sessions) == 1
    assert bob_sessions[0].session_id == bob_session.session_id
```

### 2. 权限测试

```python
async def test_access_control():
    """验证权限控制"""
    # Alice 不能访问 Bob 的资源
    with pytest.raises(HTTPException) as exc:
        _check_user_access("bob", "alice")
    assert exc.value.status_code == 403
    
    # 管理员可以访问任何资源
    _check_user_access("bob", "admin")  # 不抛出异常
```

## 总结

DataAgent 实现了完整的多租户隔离：

✅ **用户档案隔离** - 每个租户有独立的档案  
✅ **会话隔离** - 每个租户有独立的会话  
✅ **消息隔离** - 消息通过会话间接隔离  
✅ **MCP 配置隔离** - 每个租户有独立的 MCP 配置  
✅ **MCP 连接隔离** - 每个租户有独立的连接池  
✅ **规则隔离** - 用户级规则按租户隔离  
✅ **文件系统隔离** - 每个租户有独立的目录  
✅ **API 权限隔离** - 所有 API 都进行权限检查  
✅ **资源配额隔离** - 每个租户有独立的配额  
