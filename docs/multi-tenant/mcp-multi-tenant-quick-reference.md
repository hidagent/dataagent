# MCP 多租户隔离 - 快速参考

## 核心概念

### 隔离维度

```
┌─────────────────────────────────────────┐
│         多租户 MCP 隔离                   │
├─────────────────────────────────────────┤
│ 1. 配置隔离    - 每个租户独立的 mcp.json │
│ 2. 连接隔离    - 每个租户独立的连接池    │
│ 3. 工具隔离    - 每个租户独立的工具集    │
│ 4. 权限隔离    - API 层级的访问控制      │
│ 5. 资源隔离    - 连接数限制和配额管理    │
└─────────────────────────────────────────┘
```

## 快速检查清单

### ✅ 配置隔离

```python
# 验证配置隔离
store = MCPConfigStore()

alice_config = await store.get_user_config("alice")
bob_config = await store.get_user_config("bob")

# 应该不同
assert alice_config.servers != bob_config.servers
```

### ✅ 连接隔离

```python
# 验证连接隔离
manager = MCPConnectionManager()

alice_tools = manager.get_tools("alice")
bob_tools = manager.get_tools("bob")

# 应该不同
assert alice_tools != bob_tools
```

### ✅ 权限隔离

```python
# 验证权限隔离
# Alice 不能访问 Bob 的配置
try:
    _check_user_access("bob", "alice")
    assert False, "Should have raised HTTPException"
except HTTPException as e:
    assert e.status_code == 403
```

### ✅ 资源隔离

```python
# 验证资源隔离
manager = MCPConnectionManager(
    max_connections_per_user=10,
    max_total_connections=100
)

# 每个租户最多 10 个连接
# 系统最多 100 个连接
```

## 常见操作

### 1. 添加新租户

```bash
# 1. 创建租户目录
mkdir -p ~/.deepagents/new_tenant

# 2. 创建 mcp.json
cat > ~/.deepagents/new_tenant/mcp.json << 'EOF'
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_TOKEN"
      }
    }
  }
}
EOF

# 3. 设置环境变量
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# 4. 启动服务
python -m dataagent_server --user-id new_tenant
```

### 2. 查看租户的 MCP 配置

```bash
# 列出租户的所有 MCP 服务器
curl -H "Authorization: Bearer token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers

# 查看特定服务器的状态
curl -H "Authorization: Bearer token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers/github/status
```

### 3. 添加新的 MCP 服务器

```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "slack",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "$SLACK_TOKEN"
    },
    "autoApprove": ["send_message"]
  }' \
  http://localhost:8000/api/v1/users/alice/mcp-servers
```

### 4. 删除 MCP 服务器

```bash
curl -X DELETE \
  -H "Authorization: Bearer token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers/slack
```

### 5. 禁用/启用 MCP 服务器

```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"disabled": true}' \
  http://localhost:8000/api/v1/users/alice/mcp-servers/github/toggle
```

## 故障排查

### 问题 1: 租户无法连接到 MCP 服务器

```bash
# 检查服务器状态
curl -H "Authorization: Bearer token" \
  http://localhost:8000/api/v1/users/alice/mcp-servers/github/status

# 检查日志
tail -f /opt/dataagent/logs/alice/dataagent.log | grep github

# 常见原因：
# 1. 凭证无效 - 检查环境变量
# 2. 网络连接 - 检查防火墙
# 3. MCP 服务器离线 - 检查服务器状态
```

### 问题 2: 租户之间的工具混淆

```python
# 验证工具隔离
alice_tools = manager.get_tools("alice")
bob_tools = manager.get_tools("bob")

alice_names = {t.name for t in alice_tools}
bob_names = {t.name for t in bob_tools}

# 检查是否有重叠
overlap = alice_names & bob_names
if overlap:
    print(f"❌ 工具隔离失败: {overlap}")
else:
    print("✓ 工具隔离正常")
```

### 问题 3: 连接数过多

```bash
# 检查连接使用情况
curl -H "Authorization: Bearer token" \
  http://localhost:8000/api/v1/health/detailed

# 输出示例
{
  "mcp": {
    "total_connections": 85,
    "active_users": 3,
    "capacity_usage": 0.85
  }
}

# 如果接近限制，考虑：
# 1. 增加 max_total_connections
# 2. 禁用不使用的 MCP 服务器
# 3. 增加服务器实例
```

### 问题 4: 权限被拒绝

```bash
# Alice 尝试访问 Bob 的配置
curl -H "Authorization: Bearer alice_token" \
  http://localhost:8000/api/v1/users/bob/mcp-servers

# 响应 (403 Forbidden)
{
  "detail": "Access denied to other user's MCP configuration"
}

# 解决方案：
# 1. 确保使用正确的 user_id
# 2. 检查认证 token 是否有效
# 3. 管理员可以使用 admin token 访问任何用户的配置
```

## 性能优化建议

### 1. 连接池配置

```python
# 根据租户数量调整
manager = MCPConnectionManager(
    max_connections_per_user=10,      # 每个租户 10 个
    max_total_connections=100 * num_tenants  # 总数
)
```

### 2. 缓存工具列表

```python
# 缓存工具列表，避免重复查询
cache = MCPToolCache(ttl=300)  # 5 分钟过期
tools = await cache.get_tools("alice", manager)
```

### 3. 异步连接

```python
# 使用异步连接，提高并发性能
connections = await manager.connect("alice", config)
```

## 安全最佳实践

### 1. 环境变量管理

```bash
# ✅ 推荐
export ALICE_GITHUB_TOKEN="ghp_xxxx"
export BOB_GITHUB_TOKEN="ghp_yyyy"

# ❌ 不推荐
# 在 mcp.json 中硬编码凭证
```

### 2. 定期审计

```bash
# 定期检查租户的 MCP 配置
python scripts/audit_mcp_configs.py

# 输出示例
alice:
  - github: connected, 15 tools
  - postgres: connected, 8 tools
  - slack: connected, 5 tools
bob:
  - github: connected, 15 tools
  - mysql: connected, 10 tools
  - jira: connected, 12 tools
```

### 3. 日志监控

```bash
# 监控 MCP 操作日志
tail -f /opt/dataagent/logs/audit.log | grep "mcp_event"

# 输出示例
{"event_type": "connection_established", "user_id": "alice", "server_name": "github"}
{"event_type": "tool_executed", "user_id": "alice", "tool_name": "search_repositories"}
{"event_type": "connection_failed", "user_id": "bob", "server_name": "jira", "error": "..."}
```

## 监控指标

### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|--------|
| `mcp_connections_active` | 活跃连接数 | > 80% 容量 |
| `mcp_tool_executions_total` | 工具执行总数 | - |
| `mcp_tool_duration_seconds` | 工具执行时间 | > 30s |
| `mcp_connection_failures` | 连接失败数 | > 5/分钟 |

### 查看指标

```bash
# Prometheus 查询
curl 'http://localhost:9090/api/v1/query?query=mcp_connections_active'

# 输出示例
{
  "data": {
    "result": [
      {"metric": {"user_id": "alice"}, "value": [1234567890, "8"]},
      {"metric": {"user_id": "bob"}, "value": [1234567890, "6"]},
      {"metric": {"user_id": "charlie"}, "value": [1234567890, "5"]}
    ]
  }
}
```

## 测试命令

### 单元测试

```bash
# 运行多租户隔离测试
pytest source/dataagent-core/tests/test_mcp/test_multi_tenant_isolation.py -v

# 输出示例
test_config_isolation.py::test_different_tenants_have_different_configs PASSED
test_connection_isolation.py::test_different_tenants_have_different_connections PASSED
test_resource_isolation.py::test_total_connection_limit PASSED
```

### 集成测试

```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up

# 运行集成测试
pytest tests/integration/test_multi_tenant.py -v

# 清理
docker-compose -f docker-compose.test.yml down
```

### 负载测试

```bash
# 使用 locust 进行负载测试
locust -f tests/load/locustfile.py --host=http://localhost:8000

# 模拟 3 个租户，每个租户 10 个并发请求
# 持续 5 分钟
```

## 常用命令

```bash
# 启动单个租户
python -m dataagent_server --user-id alice

# 启动多个租户（Docker）
docker-compose up -d

# 查看日志
docker-compose logs -f dataagent-alice

# 健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed

# 停止服务
docker-compose down

# 清理数据
rm -rf ~/.deepagents/*/
```

## 参考资源

- [MCP 多租户隔离设计](./mcp-multi-tenant-isolation.md)
- [MCP 多租户部署指南](./mcp-multi-tenant-deployment.md)
- [MCP 多租户示例](../examples/mcp/multi-tenant-example.md)
- [MCP 配置参考](../examples/mcp/README.md)

## 支持

遇到问题？

1. 查看日志：`tail -f /opt/dataagent/logs/dataagent.log`
2. 检查配置：`cat ~/.deepagents/{user_id}/mcp.json`
3. 运行诊断：`python scripts/diagnose_mcp.py`
4. 提交 Issue：https://github.com/your-repo/issues
