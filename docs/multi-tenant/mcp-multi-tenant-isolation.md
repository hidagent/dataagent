# MCP 多租户隔离方案

## 概述

基于现有的 Agent 级别配置机制，可以实现完整的 MCP 多租户隔离。该方案确保不同租户的 MCP 配置、连接和工具完全隔离。

## 架构设计

### 1. 隔离层次

```
┌─────────────────────────────────────────────────────────┐
│                    多租户系统                             │
├─────────────────────────────────────────────────────────┤
│  Tenant A          │  Tenant B          │  Tenant C      │
│  (user_id: a1)     │  (user_id: b1)     │  (user_id: c1) │
├────────────────────┼────────────────────┼────────────────┤
│ MCP Config Store   │ MCP Config Store   │ MCP Config Store│
│ (user_id: a1)      │ (user_id: b1)      │ (user_id: c1)  │
├────────────────────┼────────────────────┼────────────────┤
│ MCP Connections    │ MCP Connections    │ MCP Connections│
│ (user_id: a1)      │ (user_id: b1)      │ (user_id: c1)  │
├────────────────────┼────────────────────┼────────────────┤
│ MCP Tools          │ MCP Tools          │ MCP Tools      │
│ (user_id: a1)      │ (user_id: b1)      │ (user_id: c1)  │
└────────────────────┴────────────────────┴────────────────┘
```

### 2. 隔离维度

| 维度 | 隔离方式 | 实现机制 |
|------|--------|--------|
| **配置隔离** | 每个租户独立的 MCP 配置 | `MCPConfigStore.get_user_config(user_id)` |
| **连接隔离** | 每个租户独立的连接池 | `MCPConnectionManager._connections[user_id]` |
| **工具隔离** | 每个租户只能访问自己的工具 | `MCPConnectionManager.get_tools(user_id)` |
| **权限隔离** | API 层级的访问控制 | `_check_user_access(user_id, current_user_id)` |
| **资源隔离** | 每个租户的连接数限制 | `max_connections_per_user` |

## 实现细节

### 1. 配置存储隔离

**当前实现** ✅

```python
# MCPConfigStore 已支持按 user_id 隔离
async def get_user_config(self, user_id: str) -> MCPConfig:
    """获取特定用户的 MCP 配置"""
    
async def save_user_config(self, user_id: str, config: MCPConfig) -> None:
    """保存特定用户的 MCP 配置"""
```

**数据库隔离**

```sql
-- MySQL 表结构已包含 user_id 隔离
CREATE TABLE mcp_servers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,  -- 租户隔离键
    server_name VARCHAR(255) NOT NULL,
    ...
    UNIQUE KEY unique_user_server (user_id, server_name),
    INDEX idx_user_id (user_id)
);
```

### 2. 连接隔离

**当前实现** ✅

```python
class MCPConnectionManager:
    # user_id -> {server_name -> MCPConnection}
    _connections: dict[str, dict[str, MCPConnection]] = {}
    
    async def connect(self, user_id: str, config: MCPConfig):
        """为特定用户创建连接"""
        if user_id not in self._connections:
            self._connections[user_id] = {}
        # 每个用户有独立的连接池
```

**隔离保证**

- 每个 `user_id` 有独立的连接字典
- 连接数限制按用户计算：`max_connections_per_user`
- 用户 A 的连接不会被用户 B 访问

### 3. 工具隔离

**当前实现** ✅

```python
def get_tools(self, user_id: str) -> list[BaseTool]:
    """获取特定用户的工具"""
    if user_id not in self._connections:
        return []
    
    tools = []
    for connection in self._connections[user_id].values():
        if connection.connected:
            tools.extend(connection.tools)
    return tools
```

### 4. API 权限隔离

**当前实现** ✅

```python
def _check_user_access(user_id: str, current_user_id: str) -> None:
    """检查用户是否有权访问目标用户的资源"""
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's MCP configuration",
        )

# 所有 MCP API 端点都使用此检查
@router.get("/users/{user_id}/mcp-servers")
async def list_mcp_servers(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    ...
):
    _check_user_access(user_id, current_user_id)
    # ...
```

### 5. 资源隔离

**当前实现** ✅

```python
class MCPConnectionManager:
    def __init__(
        self,
        max_connections_per_user: int = 10,      # 每用户限制
        max_total_connections: int = 100,        # 全局限制
    ):
        pass
    
    async def connect(self, user_id: str, config: MCPConfig):
        # 检查用户连接数
        if len(user_connections) >= self.max_connections_per_user:
            logger.warning(f"User {user_id} reached max connections")
            break
        
        # 检查全局连接数
        if self._total_connections >= self.max_total_connections:
            logger.warning(f"Total connections limit reached")
            break
```

## 多租户场景

### 场景 1: 不同租户配置不同的 MCP 服务器

```
Tenant A (user_id: alice):
  - MCP Server: github (alice 的 GitHub token)
  - MCP Server: postgres (alice 的数据库)

Tenant B (user_id: bob):
  - MCP Server: github (bob 的 GitHub token)
  - MCP Server: slack (bob 的 Slack workspace)
```

**隔离保证**

- Alice 的 GitHub token 不会被 Bob 访问
- Bob 的 Slack 工具不会被 Alice 使用
- 每个租户的配置完全独立

### 场景 2: 共享 MCP 服务器（不同凭证）

```
Shared PostgreSQL Server:
  - Tenant A: 连接到 database_a (user_id: alice)
  - Tenant B: 连接到 database_b (user_id: bob)
```

**实现方式**

```python
# 两个租户配置相同的服务器名称，但使用不同的连接字符串
# Tenant A 的 mcp.json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://user:pass@localhost/database_a"
      }
    }
  }
}

# Tenant B 的 mcp.json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://user:pass@localhost/database_b"
      }
    }
  }
}
```

### 场景 3: 租户级别的工具权限控制

```python
# 在 Agent 执行时，只加载该租户的工具
async def get_agent_tools(user_id: str, mcp_manager: MCPConnectionManager):
    """获取特定租户的工具"""
    tools = mcp_manager.get_tools(user_id)
    
    # 可选：按角色进一步过滤
    if user_role == "viewer":
        tools = [t for t in tools if not t.name.startswith("delete_")]
    
    return tools
```

## 安全建议

### 1. 环境变量隔离

```bash
# 不要在 mcp.json 中硬编码敏感信息
# ❌ 错误
{
  "env": {
    "API_KEY": "sk-1234567890"
  }
}

# ✅ 正确
{
  "env": {
    "API_KEY": "$TENANT_API_KEY"
  }
}

# 在启动时注入
export TENANT_API_KEY="sk-1234567890"
```

### 2. 连接数限制

```python
# 防止单个租户耗尽系统资源
manager = MCPConnectionManager(
    max_connections_per_user=10,      # 每个租户最多 10 个连接
    max_total_connections=100,        # 系统最多 100 个连接
)
```

### 3. 审计日志

```python
# 记录所有 MCP 操作
logger.info(f"User {user_id} connected to MCP server {server_name}")
logger.info(f"User {user_id} executed tool {tool_name}")
logger.warning(f"User {user_id} failed to connect to {server_name}: {error}")
```

### 4. 访问控制

```python
# API 层级的权限检查
def _check_user_access(user_id: str, current_user_id: str) -> None:
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
```

## 部署配置

### 1. 生产环境配置

```python
# settings.py
MCP_CONFIG = {
    "max_connections_per_user": 10,
    "max_total_connections": 1000,
    "connection_timeout": 30,
    "enable_audit_log": True,
}

# 初始化
manager = MCPConnectionManager(
    max_connections_per_user=MCP_CONFIG["max_connections_per_user"],
    max_total_connections=MCP_CONFIG["max_total_connections"],
)
```

### 2. 数据库配置

```python
# 使用 SQLite 或 MySQL 存储配置
from dataagent_core.mcp import SQLiteMCPConfigStore, MySQLMCPConfigStore

# SQLite（开发环境）
store = SQLiteMCPConfigStore("sqlite:///mcp_config.db")

# MySQL（生产环境）
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine("mysql+aiomysql://user:pass@localhost/db")
store = MySQLMCPConfigStore(engine)
```

### 3. 监控和告警

```python
# 监控连接数
async def monitor_connections(manager: MCPConnectionManager):
    total = manager.total_connections
    users = manager.get_user_count()
    
    if total > 80:  # 80% 容量
        logger.warning(f"MCP connections at {total}/{manager.max_total_connections}")
    
    return {
        "total_connections": total,
        "active_users": users,
        "capacity_usage": total / manager.max_total_connections,
    }
```

## 测试

### 1. 隔离性测试

```python
# 测试不同租户的配置隔离
async def test_config_isolation():
    store = MemoryMCPConfigStore()
    
    # 租户 A 添加服务器
    config_a = MCPConfig(servers={
        "server1": MCPServerConfig(name="server1", command="cmd1")
    })
    await store.save_user_config("user_a", config_a)
    
    # 租户 B 添加不同的服务器
    config_b = MCPConfig(servers={
        "server2": MCPServerConfig(name="server2", command="cmd2")
    })
    await store.save_user_config("user_b", config_b)
    
    # 验证隔离
    assert (await store.get_user_config("user_a")).servers.keys() == {"server1"}
    assert (await store.get_user_config("user_b")).servers.keys() == {"server2"}
```

### 2. 连接隔离测试

```python
# 测试不同租户的连接隔离
async def test_connection_isolation():
    manager = MCPConnectionManager()
    
    # 租户 A 连接
    config_a = MCPConfig(servers={...})
    conns_a = await manager.connect("user_a", config_a)
    
    # 租户 B 连接
    config_b = MCPConfig(servers={...})
    conns_b = await manager.connect("user_b", config_b)
    
    # 验证隔离
    assert manager.get_tools("user_a") != manager.get_tools("user_b")
    assert "user_a" in manager._connections
    assert "user_b" in manager._connections
```

### 3. 权限隔离测试

```python
# 测试 API 权限隔离
def test_api_access_control():
    # 用户 A 不能访问用户 B 的配置
    with pytest.raises(HTTPException) as exc:
        _check_user_access("user_b", "user_a")
    assert exc.value.status_code == 403
    
    # 管理员可以访问任何用户的配置
    _check_user_access("user_b", "admin")  # 不抛出异常
```

## 总结

你的代码已经实现了完整的 MCP 多租户隔离：

✅ **配置隔离** - 每个租户独立的 MCP 配置存储  
✅ **连接隔离** - 每个租户独立的连接池  
✅ **工具隔离** - 每个租户只能访问自己的工具  
✅ **权限隔离** - API 层级的访问控制  
✅ **资源隔离** - 连接数限制和配额管理  

只需要在部署时正确配置和监控，就能确保多租户环境下的完整隔离。
