# API 参考

## REST API

### 基础信息

- Base URL: `http://localhost:8000/api/v1`
- Content-Type: `application/json`
- 认证: `X-API-Key` Header (可选，通过 `DATAAGENT_API_KEYS` 配置)

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

#### 发送消息

```
POST /api/v1/chat
```

**请求:**
```json
{
  "message": "你好",
  "session_id": "optional-session-id",
  "assistant_id": "optional-assistant-id"
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

---

## WebSocket 协议

### 连接

```
ws://localhost:8000/ws/chat/{session_id}
```

### 客户端消息格式

```typescript
interface ClientMessage {
  type: "chat" | "hitl_decision" | "cancel" | "ping";
  payload: object;
}
```

#### 聊天消息

```json
{
  "type": "chat",
  "payload": {
    "message": "你好"
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
| `DATAAGENT_MYSQL_HOST` | MySQL 主机 | `localhost` |
| `DATAAGENT_MYSQL_PORT` | MySQL 端口 | `3306` |
| `DATAAGENT_MYSQL_USER` | MySQL 用户 | `root` |
| `DATAAGENT_MYSQL_PASSWORD` | MySQL 密码 | 空 |
| `DATAAGENT_MYSQL_DATABASE` | MySQL 数据库 | `dataagent` |
