# API 参考

## REST API

### 基础信息

- Base URL: `http://localhost:8000/api/v1`
- Content-Type: `application/json`
- 认证: `X-API-Key` Header (可选，通过 `DATAAGENT_API_KEYS` 配置)
- 用户标识: `X-User-ID` Header (用于多租户隔离)

### 健康检查

```
GET /api/v1/health
```

**响应:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime": 123.45
}
```

### 聊天

#### 发送消息（同步）

```
POST /api/v1/chat
```

**请求:**
```json
{
  "message": "你好",
  "session_id": "optional-session-id",
  "assistant_id": "optional-assistant-id",
  "user_context": {
    "user_id": "user123",
    "username": "zhangsan",
    "display_name": "张三",
    "department": "技术部",
    "role": "开发工程师"
  }
}
```

**响应:**
```json
{
  "session_id": "uuid",
  "events": [
    {
      "event_type": "text",
      "content": "你好！有什么可以帮助你的？",
      "is_final": true,
      "timestamp": 1234567890.123
    },
    {
      "event_type": "done",
      "cancelled": false,
      "token_usage": null,
      "timestamp": 1234567890.456
    }
  ]
}
```

#### 发送消息（SSE 流式）

```
POST /api/v1/chat/stream
```

**请求:** 同上

**响应:** Server-Sent Events 流

```
data: {"event_type": "text", "data": {"content": "你好", "is_final": false}}

data: {"event_type": "text", "data": {"content": "！", "is_final": false}}

data: {"event_type": "done", "data": {"cancelled": false}}

data: {"event_type": "stream_end", "data": {}}
```

**响应头:**
- `X-Session-ID`: 会话 ID

#### 取消聊天

```
POST /api/v1/chat/{session_id}/cancel
```

**响应:**
```json
{
  "status": "cancelled",
  "session_id": "uuid"
}
```

### 会话管理

#### 列出会话

```
GET /api/v1/sessions?user_id=xxx
```

**响应:**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "user_id": "user-1",
      "assistant_id": "default",
      "created_at": "2024-01-01T00:00:00",
      "last_active": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

#### 获取会话详情

```
GET /api/v1/sessions/{session_id}
```

#### 删除会话

```
DELETE /api/v1/sessions/{session_id}
```

#### 获取会话消息历史

```
GET /api/v1/sessions/{session_id}/messages?limit=100&offset=0
```

**响应:**
```json
{
  "messages": [
    {
      "message_id": "uuid",
      "session_id": "uuid",
      "role": "user",
      "content": "你好",
      "created_at": "2024-01-01T00:00:00",
      "metadata": {}
    }
  ],
  "total": 10,
  "limit": 100,
  "offset": 0
}
```

### 助手管理

#### 列出助手

```
GET /api/v1/assistants
```

**响应:**
```json
{
  "assistants": [
    {
      "assistant_id": "default",
      "name": "Default Assistant",
      "description": "默认助手",
      "model": null,
      "system_prompt": null,
      "tools": null,
      "auto_approve": false,
      "metadata": null
    }
  ],
  "total": 1
}
```

#### 获取助手详情

```
GET /api/v1/assistants/{assistant_id}
```

#### 创建助手

```
POST /api/v1/assistants
```

**请求:**
```json
{
  "name": "代码助手",
  "description": "专注于代码开发的助手",
  "model": "gpt-4",
  "system_prompt": "你是一个专业的代码开发助手...",
  "tools": ["shell", "file_write"],
  "auto_approve": false,
  "metadata": {"category": "development"}
}
```

#### 更新助手

```
PUT /api/v1/assistants/{assistant_id}
```

#### 删除助手

```
DELETE /api/v1/assistants/{assistant_id}
```

### 用户档案管理

#### 列出用户档案

```
GET /api/v1/user-profiles
```

**响应:**
```json
{
  "profiles": [
    {
      "user_id": "user123",
      "username": "zhangsan",
      "display_name": "张三",
      "email": "zhangsan@example.com",
      "department": "技术部",
      "role": "开发工程师",
      "custom_fields": {},
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

#### 获取用户档案

```
GET /api/v1/user-profiles/{user_id}
```

#### 创建用户档案

```
POST /api/v1/user-profiles
```

**请求:**
```json
{
  "user_id": "user123",
  "username": "zhangsan",
  "display_name": "张三",
  "email": "zhangsan@example.com",
  "department": "技术部",
  "role": "开发工程师",
  "custom_fields": {"team": "AI团队"}
}
```

#### 更新用户档案

```
PUT /api/v1/user-profiles/{user_id}
```

#### 删除用户档案

```
DELETE /api/v1/user-profiles/{user_id}
```

### 用户记忆管理

#### 获取用户记忆状态

```
GET /api/v1/users/{user_id}/memory/status
```

**响应:**
```json
{
  "exists": true,
  "path": "/home/user/.deepagents/users/user123",
  "size_bytes": 1024,
  "file_count": 5
}
```

#### 清除用户记忆

```
DELETE /api/v1/users/{user_id}/memory
```

**响应:**
```json
{
  "success": true,
  "message": "Memory cleared for user user123"
}
```

### MCP 服务器管理

MCP (Model Context Protocol) 服务器用于扩展 Agent 的工具能力。

#### 列出 MCP 服务器

```
GET /api/v1/users/{user_id}/mcp-servers
```

**响应:**
```json
{
  "servers": [
    {
      "name": "aws-docs",
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {},
      "url": null,
      "disabled": false,
      "auto_approve": [],
      "status": "connected",
      "connected": true,
      "tools_count": 5,
      "error": null
    }
  ]
}
```

#### 添加 MCP 服务器

```
POST /api/v1/users/{user_id}/mcp-servers
```

**请求 (命令行方式):**
```json
{
  "name": "my-mcp-server",
  "command": "uvx",
  "args": ["my-mcp-package@latest"],
  "env": {"API_KEY": "xxx"},
  "disabled": false,
  "autoApprove": ["tool1", "tool2"]
}
```

**请求 (HTTP/SSE 方式):**
```json
{
  "name": "remote-mcp",
  "url": "http://localhost:3000/mcp",
  "transport": "sse",
  "headers": {"Authorization": "Bearer xxx"},
  "disabled": false
}
```

#### 获取 MCP 服务器详情

```
GET /api/v1/users/{user_id}/mcp-servers/{server_name}
```

#### 更新 MCP 服务器

```
PUT /api/v1/users/{user_id}/mcp-servers/{server_name}
```

#### 删除 MCP 服务器

```
DELETE /api/v1/users/{user_id}/mcp-servers/{server_name}
```

#### 获取 MCP 服务器状态

```
GET /api/v1/users/{user_id}/mcp-servers/{server_name}/status
```

**响应:**
```json
{
  "name": "aws-docs",
  "status": "connected",
  "connected": true,
  "tools_count": 5,
  "tools": ["search_docs", "get_doc", "list_services", "get_api", "get_examples"],
  "error": null,
  "disabled": false
}
```

#### 启用/禁用 MCP 服务器

```
POST /api/v1/users/{user_id}/mcp-servers/{server_name}/toggle
```

**请求:**
```json
{
  "disabled": true
}
```

#### 连接 MCP 服务器

```
POST /api/v1/users/{user_id}/mcp-servers/{server_name}/connect
```

**响应:**
```json
{
  "success": true,
  "status": "connected",
  "tools_count": 5,
  "tools": ["tool1", "tool2", "tool3", "tool4", "tool5"],
  "error": null
}
```

#### 断开 MCP 服务器

```
POST /api/v1/users/{user_id}/mcp-servers/{server_name}/disconnect
```

### 工作目录管理

工作目录用于多租户文件系统隔离，每个用户有独立的工作目录。

#### 列出工作目录

```
GET /api/v1/workspaces
```

**响应:**
```json
{
  "workspaces": [
    {
      "workspace_id": "uuid",
      "name": "我的工作目录",
      "path": "/var/dataagent/workspaces/user123",
      "description": "默认工作目录",
      "max_size_bytes": 1073741824,
      "max_files": 10000,
      "current_size_bytes": 1024000,
      "current_file_count": 50,
      "is_default": true,
      "is_active": true,
      "permission": "admin",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "last_accessed_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

#### 获取默认工作目录

```
GET /api/v1/workspaces/default
```

#### 创建工作目录

```
POST /api/v1/workspaces
```

**请求:**
```json
{
  "name": "项目工作目录",
  "path": "/var/dataagent/workspaces/user123/project1",
  "description": "项目专用工作目录",
  "max_size_bytes": 2147483648,
  "max_files": 20000,
  "is_default": false
}
```

#### 获取工作目录详情

```
GET /api/v1/workspaces/{workspace_id}
```

#### 更新工作目录

```
PATCH /api/v1/workspaces/{workspace_id}
```

**请求:**
```json
{
  "name": "更新后的名称",
  "description": "更新后的描述",
  "max_size_bytes": 3221225472,
  "is_default": true
}
```

#### 删除工作目录

```
DELETE /api/v1/workspaces/{workspace_id}
```

#### 设置默认工作目录

```
POST /api/v1/workspaces/{workspace_id}/set-default
```

**说明:**
- 每个用户登录时会自动创建默认工作目录
- Agent 执行文件操作时会使用用户的默认工作目录
- 工作目录路径可通过环境变量 `DATAAGENT_WORKSPACE_BASE_PATH` 配置基础路径

### 规则管理

规则用于定制 Agent 的行为和响应方式。

#### 列出规则

```
GET /api/v1/users/{user_id}/rules?scope=user
```

**参数:**
- `scope`: 可选，过滤规则范围 (global, user, project, session)

**响应:**
```json
{
  "rules": [
    {
      "name": "code-style",
      "description": "代码风格规范",
      "content": "请遵循 PEP8 代码风格...",
      "scope": "user",
      "inclusion": "always",
      "file_match_pattern": null,
      "priority": 50,
      "override": false,
      "enabled": true,
      "source_path": "/home/user/.deepagents/users/user123/rules/code-style.md"
    }
  ],
  "total": 1
}
```

#### 获取规则详情

```
GET /api/v1/users/{user_id}/rules/{rule_name}
```

#### 创建规则

```
POST /api/v1/users/{user_id}/rules
```

**请求:**
```json
{
  "name": "code-review",
  "description": "代码审查规范",
  "content": "在审查代码时，请关注以下几点：\n1. 代码可读性\n2. 性能优化\n3. 安全性",
  "scope": "user",
  "inclusion": "always",
  "file_match_pattern": null,
  "priority": 50,
  "override": false,
  "enabled": true
}
```

**inclusion 可选值:**
- `always`: 始终包含
- `file_match`: 当文件匹配 `file_match_pattern` 时包含
- `manual`: 手动触发时包含

#### 更新规则

```
PUT /api/v1/users/{user_id}/rules/{rule_name}
```

**请求:**
```json
{
  "description": "更新后的描述",
  "content": "更新后的内容",
  "enabled": false
}
```

#### 删除规则

```
DELETE /api/v1/users/{user_id}/rules/{rule_name}
```

#### 验证规则内容

```
POST /api/v1/users/{user_id}/rules/validate
```

**请求:**
```json
{
  "content": "规则内容..."
}
```

**响应:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["建议添加更详细的描述"]
}
```

#### 检测规则冲突

```
GET /api/v1/users/{user_id}/rules/conflicts/list
```

**响应:**
```json
{
  "conflicts": [
    {
      "rule1_name": "rule-a",
      "rule1_scope": "global",
      "rule2_name": "rule-b",
      "rule2_scope": "user",
      "conflict_type": "override",
      "resolution": "user scope rule takes precedence",
      "details": ""
    }
  ],
  "warnings": [],
  "total_conflicts": 1
}
```

#### 重新加载规则

```
POST /api/v1/users/{user_id}/rules/reload
```

**响应:**
```json
{
  "success": true,
  "rules_count": 10,
  "message": "Reloaded 10 rules successfully"
}
```

---

## WebSocket 协议

### 连接

```
ws://localhost:8000/ws/chat/{session_id}
```

### 客户端消息格式

```typescript
interface ClientMessage {
  type: "chat" | "hitl_decision" | "cancel" | "ping" | "set_user_context";
  payload: object;
}
```

#### 聊天消息

```json
{
  "type": "chat",
  "payload": {
    "message": "你好",
    "user_id": "user123",
    "user_context": {
      "user_id": "user123",
      "display_name": "张三",
      "department": "技术部"
    }
  }
}
```

#### 设置用户上下文

```json
{
  "type": "set_user_context",
  "payload": {
    "user_id": "user123",
    "username": "zhangsan",
    "display_name": "张三",
    "department": "技术部",
    "role": "开发工程师",
    "custom_fields": {}
  }
}
```

#### HITL 决定

```json
{
  "type": "hitl_decision",
  "payload": {
    "decisions": [
      {"type": "approve"}
    ]
  }
}
```

#### 取消

```json
{
  "type": "cancel",
  "payload": {}
}
```

#### 心跳

```json
{
  "type": "ping",
  "payload": {}
}
```

### 服务端消息格式

```typescript
interface ServerMessage {
  event_type: string;
  data: object;
  timestamp: number;
}
```

#### 连接成功

```json
{
  "event_type": "connected",
  "data": {"session_id": "uuid"},
  "timestamp": 1234567890.123
}
```

#### 文本输出

```json
{
  "event_type": "text",
  "data": {
    "content": "你好！",
    "is_final": false
  },
  "timestamp": 1234567890.123
}
```

#### 工具调用

```json
{
  "event_type": "tool_call",
  "data": {
    "tool_name": "web_search",
    "tool_args": {"query": "天气"},
    "tool_call_id": "call_xxx"
  },
  "timestamp": 1234567890.123
}
```

#### 工具结果

```json
{
  "event_type": "tool_result",
  "data": {
    "tool_call_id": "call_xxx",
    "result": "搜索结果...",
    "status": "success"
  },
  "timestamp": 1234567890.123
}
```

#### HITL 请求

```json
{
  "event_type": "hitl",
  "data": {
    "action": {
      "name": "shell",
      "args": {"command": "ls -la"},
      "description": "执行 Shell 命令"
    }
  },
  "timestamp": 1234567890.123
}
```

#### 文件操作

```json
{
  "event_type": "file_operation",
  "data": {
    "operation": "write",
    "file_path": "/path/to/file.py",
    "metrics": {
      "lines_written": 10,
      "lines_added": 5,
      "lines_removed": 2
    },
    "diff": "...",
    "status": "success"
  },
  "timestamp": 1234567890.123
}
```

#### Todo 更新

```json
{
  "event_type": "todo_update",
  "data": {
    "todos": [
      {"content": "任务1", "status": "completed"},
      {"content": "任务2", "status": "in_progress"}
    ]
  },
  "timestamp": 1234567890.123
}
```

#### 错误

```json
{
  "event_type": "error",
  "data": {
    "error_code": "EXECUTION_ERROR",
    "message": "执行失败",
    "recoverable": true
  },
  "timestamp": 1234567890.123
}
```

#### 完成

```json
{
  "event_type": "done",
  "data": {
    "cancelled": false,
    "token_usage": {
      "input_tokens": 100,
      "output_tokens": 50
    }
  },
  "timestamp": 1234567890.123
}
```

#### 心跳响应

```json
{
  "event_type": "pong",
  "data": {},
  "timestamp": 1234567890.123
}
```

---

## 错误响应

所有 API 错误返回统一格式：

```json
{
  "detail": "错误描述"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 配置参考

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATAAGENT_HOST` | 监听地址 | `0.0.0.0` |
| `DATAAGENT_PORT` | 监听端口 | `8000` |
| `DATAAGENT_WORKERS` | 工作进程数 | `1` |
| `DATAAGENT_API_KEYS` | API Key 列表 (逗号分隔) | 空 |
| `DATAAGENT_AUTH_DISABLED` | 禁用认证 | `false` |
| `DATAAGENT_CORS_ORIGINS` | CORS 允许的源 | `*` |
| `DATAAGENT_SESSION_TIMEOUT` | 会话超时 (秒) | `3600` |
| `DATAAGENT_MAX_CONNECTIONS` | 最大连接数 | `200` |
| `DATAAGENT_SESSION_STORE` | 存储类型 | `memory` |
| `DATAAGENT_POSTGRES_HOST` | PostgreSQL 主机 | `localhost` |
| `DATAAGENT_POSTGRES_PORT` | PostgreSQL 端口 | `5432` |
| `DATAAGENT_POSTGRES_USER` | PostgreSQL 用户 | `postgres` |
| `DATAAGENT_POSTGRES_PASSWORD` | PostgreSQL 密码 | 空 |
| `DATAAGENT_POSTGRES_DATABASE` | PostgreSQL 数据库 | `dataagent` |
| `DATAAGENT_WORKSPACE_BASE_PATH` | 用户工作目录基础路径 | `/var/dataagent/workspaces` |
| `DATAAGENT_WORKSPACE_DEFAULT_MAX_SIZE_BYTES` | 默认工作目录最大大小 | `1073741824` (1GB) |
| `DATAAGENT_WORKSPACE_DEFAULT_MAX_FILES` | 默认工作目录最大文件数 | `10000` |
