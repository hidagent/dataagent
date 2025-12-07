# MCP 多租户隔离示例

## 场景描述

一个 SaaS 平台有三个租户，每个租户需要配置不同的 MCP 服务器，确保数据和工具完全隔离。

```
┌─────────────────────────────────────────────────────────┐
│              DataAgent SaaS 平台                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Tenant A (alice@company.com)                           │
│  ├─ MCP: GitHub (alice 的 token)                        │
│  ├─ MCP: PostgreSQL (alice 的数据库)                    │
│  └─ MCP: Slack (alice 的 workspace)                     │
│                                                          │
│  Tenant B (bob@company.com)                             │
│  ├─ MCP: GitHub (bob 的 token)                          │
│  ├─ MCP: MySQL (bob 的数据库)                           │
│  └─ MCP: Jira (bob 的 workspace)                        │
│                                                          │
│  Tenant C (charlie@company.com)                         │
│  ├─ MCP: GitHub (charlie 的 token)                      │
│  └─ MCP: AWS (charlie 的账户)                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 1. 租户 A 的 MCP 配置

**用户**: alice@company.com (user_id: `alice`)

**配置文件**: `~/.deepagents/alice/mcp.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "$ALICE_GITHUB_TOKEN"
      },
      "autoApprove": ["search_repositories", "get_repository"],
      "disabled": false
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://alice:pass@db.company.com:5432/alice_db"
      },
      "autoApprove": ["read_query"],
      "disabled": false
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "$ALICE_SLACK_TOKEN"
      },
      "autoApprove": ["send_message"],
      "disabled": false
    }
  }
}
```

**环境变量设置** (Alice 的启动脚本):

```bash
#!/bin/bash
export ALICE_GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export ALICE_SLACK_TOKEN="xoxb-xxxxxxxxxxxxxxxxxxxx"

# 启动 DataAgent 服务器
python -m dataagent_server --user-id alice
```

## 2. 租户 B 的 MCP 配置

**用户**: bob@company.com (user_id: `bob`)

**配置文件**: `~/.deepagents/bob/mcp.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "$BOB_GITHUB_TOKEN"
      },
      "autoApprove": ["search_repositories"],
      "disabled": false
    },
    "mysql": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-mysql"],
      "env": {
        "MYSQL_CONNECTION_STRING": "mysql://bob:pass@db.company.com:3306/bob_db"
      },
      "autoApprove": ["read_query"],
      "disabled": false
    },
    "jira": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-jira"],
      "env": {
        "JIRA_URL": "https://jira.company.com",
        "JIRA_API_TOKEN": "$BOB_JIRA_TOKEN"
      },
      "autoApprove": ["search_issues", "get_issue"],
      "disabled": false
    }
  }
}
```

**环境变量设置** (Bob 的启动脚本):

```bash
#!/bin/bash
export BOB_GITHUB_TOKEN="ghp_yyyyyyyyyyyyyyyyyyyy"
export BOB_JIRA_TOKEN="atcyyyyyyyyyyyyyyyyy"

# 启动 DataAgent 服务器
python -m dataagent_server --user-id bob
```

## 3. 租户 C 的 MCP 配置

**用户**: charlie@company.com (user_id: `charlie`)

**配置文件**: `~/.deepagents/charlie/mcp.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "$CHARLIE_GITHUB_TOKEN"
      },
      "disabled": false
    },
    "aws": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-aws"],
      "env": {
        "AWS_ACCESS_KEY_ID": "$CHARLIE_AWS_ACCESS_KEY",
        "AWS_SECRET_ACCESS_KEY": "$CHARLIE_AWS_SECRET_KEY",
        "AWS_REGION": "us-east-1"
      },
      "autoApprove": ["describe_instances", "list_buckets"],
      "disabled": false
    }
  }
}
```

**环境变量设置** (Charlie 的启动脚本):

```bash
#!/bin/bash
export CHARLIE_GITHUB_TOKEN="ghp_zzzzzzzzzzzzzzzzzzzz"
export CHARLIE_AWS_ACCESS_KEY="AKIAIOSFODNN7EXAMPLE"
export CHARLIE_AWS_SECRET_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# 启动 DataAgent 服务器
python -m dataagent_server --user-id charlie
```

## 4. API 使用示例

### 4.1 列出租户的 MCP 服务器

```bash
# Alice 查看自己的 MCP 服务器
curl -H "Authorization: Bearer alice_token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers

# 响应
{
  "servers": [
    {
      "name": "github",
      "status": "connected",
      "connected": true,
      "tools_count": 15,
      "disabled": false
    },
    {
      "name": "postgres",
      "status": "connected",
      "connected": true,
      "tools_count": 8,
      "disabled": false
    },
    {
      "name": "slack",
      "status": "connected",
      "connected": true,
      "tools_count": 5,
      "disabled": false
    }
  ]
}
```

### 4.2 获取租户的工具

```bash
# Alice 获取自己的所有工具
curl -H "Authorization: Bearer alice_token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers/github/status

# 响应
{
  "name": "github",
  "status": "connected",
  "connected": true,
  "tools_count": 15,
  "tools": [
    "search_repositories",
    "get_repository",
    "list_issues",
    "create_issue",
    "update_issue",
    ...
  ],
  "disabled": false
}
```

### 4.3 权限隔离验证

```bash
# Alice 尝试访问 Bob 的 MCP 配置 - 应该被拒绝
curl -H "Authorization: Bearer alice_token" \
  http://localhost:8000/api/v1/users/bob/mcp-servers

# 响应 (403 Forbidden)
{
  "detail": "Access denied to other user's MCP configuration"
}
```

### 4.4 添加新的 MCP 服务器

```bash
# Alice 添加一个新的 MCP 服务器
curl -X POST \
  -H "Authorization: Bearer alice_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "notion",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-notion"],
    "env": {
      "NOTION_API_KEY": "$ALICE_NOTION_KEY"
    },
    "autoApprove": ["search_pages"],
    "disabled": false
  }' \
  http://localhost:8000/api/v1/users/alice/mcp-servers

# 响应 (201 Created)
{
  "name": "notion",
  "status": "disconnected",
  "connected": false,
  "tools_count": 0,
  "disabled": false
}
```

## 5. 多租户隔离验证

### 5.1 配置隔离

```python
# 测试代码
import asyncio
from dataagent_core.mcp import SQLiteMCPConfigStore

async def test_config_isolation():
    store = SQLiteMCPConfigStore("sqlite:///mcp_config.db")
    
    # Alice 的配置
    alice_config = await store.get_user_config("alice")
    print(f"Alice's servers: {list(alice_config.servers.keys())}")
    # 输出: Alice's servers: ['github', 'postgres', 'slack']
    
    # Bob 的配置
    bob_config = await store.get_user_config("bob")
    print(f"Bob's servers: {list(bob_config.servers.keys())}")
    # 输出: Bob's servers: ['github', 'mysql', 'jira']
    
    # Charlie 的配置
    charlie_config = await store.get_user_config("charlie")
    print(f"Charlie's servers: {list(charlie_config.servers.keys())}")
    # 输出: Charlie's servers: ['github', 'aws']
    
    # 验证隔离
    assert alice_config.servers.keys() != bob_config.servers.keys()
    assert bob_config.servers.keys() != charlie_config.servers.keys()
    print("✓ 配置隔离验证通过")

asyncio.run(test_config_isolation())
```

### 5.2 连接隔离

```python
# 测试代码
import asyncio
from dataagent_core.mcp import MCPConnectionManager, MCPConfig

async def test_connection_isolation():
    manager = MCPConnectionManager(
        max_connections_per_user=10,
        max_total_connections=100
    )
    
    # Alice 连接
    alice_config = MCPConfig(servers={...})
    alice_conns = await manager.connect("alice", alice_config)
    
    # Bob 连接
    bob_config = MCPConfig(servers={...})
    bob_conns = await manager.connect("bob", bob_config)
    
    # Charlie 连接
    charlie_config = MCPConfig(servers={...})
    charlie_conns = await manager.connect("charlie", charlie_config)
    
    # 验证隔离
    alice_tools = manager.get_tools("alice")
    bob_tools = manager.get_tools("bob")
    charlie_tools = manager.get_tools("charlie")
    
    print(f"Alice's tools: {len(alice_tools)}")
    print(f"Bob's tools: {len(bob_tools)}")
    print(f"Charlie's tools: {len(charlie_tools)}")
    
    # 验证不同租户的工具不同
    alice_tool_names = {t.name for t in alice_tools}
    bob_tool_names = {t.name for t in bob_tools}
    
    # Alice 有 Slack 工具，Bob 没有
    assert any("slack" in t.lower() for t in alice_tool_names)
    assert not any("slack" in t.lower() for t in bob_tool_names)
    
    # Bob 有 Jira 工具，Alice 没有
    assert any("jira" in t.lower() for t in bob_tool_names)
    assert not any("jira" in t.lower() for t in alice_tool_names)
    
    print("✓ 连接隔离验证通过")

asyncio.run(test_connection_isolation())
```

### 5.3 工具隔离

```python
# 测试代码
async def test_tool_isolation():
    manager = MCPConnectionManager()
    
    # 获取每个租户的工具
    alice_tools = manager.get_tools("alice")
    bob_tools = manager.get_tools("bob")
    charlie_tools = manager.get_tools("charlie")
    
    # 验证工具集合不重叠
    alice_tool_names = {t.name for t in alice_tools}
    bob_tool_names = {t.name for t in bob_tools}
    charlie_tool_names = {t.name for t in charlie_tools}
    
    # 虽然都有 GitHub，但工具应该是独立的连接
    # 每个租户的 GitHub 工具使用各自的 token
    
    # 验证 Alice 有 Slack 工具
    assert any("slack" in t.lower() for t in alice_tool_names)
    
    # 验证 Bob 有 Jira 工具
    assert any("jira" in t.lower() for t in bob_tool_names)
    
    # 验证 Charlie 有 AWS 工具
    assert any("aws" in t.lower() for t in charlie_tool_names)
    
    print("✓ 工具隔离验证通过")

asyncio.run(test_tool_isolation())
```

## 6. 资源限制示例

### 6.1 连接数限制

```python
# 配置
manager = MCPConnectionManager(
    max_connections_per_user=10,      # 每个租户最多 10 个连接
    max_total_connections=100,        # 系统最多 100 个连接
)

# 场景：Alice 尝试添加第 11 个 MCP 服务器
# 结果：会被限制，日志输出：
# "User alice reached max connections (10)"
```

### 6.2 监控连接使用

```python
# 监控脚本
async def monitor_mcp_usage(manager: MCPConnectionManager):
    total = manager.total_connections
    users = manager.get_user_count()
    capacity = total / manager.max_total_connections
    
    print(f"Total connections: {total}/{manager.max_total_connections}")
    print(f"Active users: {users}")
    print(f"Capacity usage: {capacity:.1%}")
    
    if capacity > 0.8:
        print("⚠️  Warning: MCP connections at 80% capacity")
    
    # 按用户统计
    for user_id in ["alice", "bob", "charlie"]:
        status = manager.get_connection_status(user_id)
        print(f"\n{user_id}:")
        for server_name, info in status.items():
            print(f"  {server_name}: {info['tools_count']} tools, "
                  f"connected={info['connected']}")
```

## 7. 安全最佳实践

### 7.1 环境变量管理

```bash
# ✅ 推荐：使用环境变量
export ALICE_GITHUB_TOKEN="ghp_xxxx"
export ALICE_SLACK_TOKEN="xoxb_xxxx"

# ❌ 不推荐：硬编码在配置文件中
{
  "env": {
    "GITHUB_TOKEN": "ghp_xxxx"  # 不要这样做！
  }
}
```

### 7.2 审计日志

```python
# 记录所有 MCP 操作
import logging

logger = logging.getLogger("mcp_audit")

# 连接事件
logger.info(f"User alice connected to MCP server github")

# 工具执行事件
logger.info(f"User alice executed tool search_repositories")

# 错误事件
logger.warning(f"User bob failed to connect to jira: Connection timeout")

# 权限事件
logger.warning(f"User alice attempted to access bob's MCP configuration")
```

### 7.3 定期审查

```python
# 定期审查租户的 MCP 配置
async def audit_mcp_configs(store: MCPConfigStore):
    for user_id in ["alice", "bob", "charlie"]:
        config = await store.get_user_config(user_id)
        
        print(f"\n{user_id}'s MCP Configuration:")
        for server_name, server in config.servers.items():
            print(f"  {server_name}:")
            print(f"    - Command: {server.command}")
            print(f"    - Disabled: {server.disabled}")
            print(f"    - Auto-approve tools: {server.auto_approve}")
            
            # 检查敏感信息
            if server.env:
                print(f"    - Environment variables: {list(server.env.keys())}")
```

## 8. 故障排查

### 8.1 租户无法连接到 MCP 服务器

```bash
# 检查配置
curl -H "Authorization: Bearer alice_token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers/github/status

# 如果返回错误，检查：
# 1. 环境变量是否正确设置
# 2. 凭证是否有效
# 3. 网络连接是否正常
# 4. MCP 服务器是否在线
```

### 8.2 租户之间的工具混淆

```python
# 验证工具隔离
alice_tools = manager.get_tools("alice")
bob_tools = manager.get_tools("bob")

# 检查是否有重复的工具实例
alice_tool_ids = {id(t) for t in alice_tools}
bob_tool_ids = {id(t) for t in bob_tools}

if alice_tool_ids & bob_tool_ids:
    print("❌ 工具隔离失败：发现共享的工具实例")
else:
    print("✓ 工具隔离正常")
```

## 总结

这个多租户隔离示例展示了：

✅ **配置隔离** - 每个租户有独立的 mcp.json  
✅ **凭证隔离** - 使用环境变量，不同租户的凭证分离  
✅ **连接隔离** - 每个租户有独立的连接池  
✅ **工具隔离** - 每个租户只能访问自己的工具  
✅ **权限隔离** - API 层级的访问控制  
✅ **资源隔离** - 连接数限制和配额管理  
✅ **审计日志** - 记录所有操作用于审计  

通过这些机制，可以在多租户环境中安全地隔离 MCP 配置和工具。
