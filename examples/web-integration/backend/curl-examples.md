# DataAgent cURL 命令示例

本文档提供使用 cURL 与 DataAgent Server 交互的完整示例。

## 基础配置

```bash
# 设置服务器地址
export DATAAGENT_URL="http://localhost:8000"

# 设置 API Key（如果启用了认证）
export DATAAGENT_API_KEY="your-api-key"

# 设置用户 ID
export DATAAGENT_USER_ID="demo-user"
```

## 健康检查

```bash
curl -s "$DATAAGENT_URL/api/v1/health" | jq
```

响应示例：
```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime": 123.45
}
```

## 聊天 API

### 发送消息（同步）

```bash
curl -X POST "$DATAAGENT_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -H "X-API-Key: $DATAAGENT_API_KEY" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "session_id": null
  }' | jq
```

响应示例：
```json
{
  "session_id": "abc123-...",
  "events": [
    {
      "event_type": "text",
      "content": "你好！我是 DataAgent...",
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

### 发送消息（SSE 流式）

```bash
curl -X POST "$DATAAGENT_URL/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "请用一句话介绍 Python"
  }' --no-buffer
```

响应示例（SSE 格式）：
```
data: {"event_type": "text", "data": {"content": "Python", "is_final": false}}

data: {"event_type": "text", "data": {"content": " 是一种", "is_final": false}}

data: {"event_type": "text", "data": {"content": "简洁易学的编程语言。", "is_final": true}}

data: {"event_type": "done", "data": {"cancelled": false}}

data: {"event_type": "stream_end", "data": {}}
```

### 继续会话

```bash
# 使用之前返回的 session_id 继续对话
curl -X POST "$DATAAGENT_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "message": "继续上面的话题",
    "session_id": "abc123-..."
  }' | jq
```

### 带用户上下文的请求

```bash
curl -X POST "$DATAAGENT_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "message": "你好",
    "user_context": {
      "user_id": "user123",
      "username": "zhangsan",
      "display_name": "张三",
      "department": "技术部",
      "role": "开发工程师"
    }
  }' | jq
```

### 取消聊天

```bash
curl -X POST "$DATAAGENT_URL/api/v1/chat/abc123-.../cancel" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

## 会话管理

### 列出会话

```bash
curl -s "$DATAAGENT_URL/api/v1/sessions?user_id=$DATAAGENT_USER_ID" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 获取会话详情

```bash
curl -s "$DATAAGENT_URL/api/v1/sessions/abc123-..." \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 获取会话消息历史

```bash
curl -s "$DATAAGENT_URL/api/v1/sessions/abc123-.../messages?limit=50&offset=0" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 删除会话

```bash
curl -X DELETE "$DATAAGENT_URL/api/v1/sessions/abc123-..." \
  -H "X-User-ID: $DATAAGENT_USER_ID"
```

## 助手管理

### 列出助手

```bash
curl -s "$DATAAGENT_URL/api/v1/assistants" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 获取助手详情

```bash
curl -s "$DATAAGENT_URL/api/v1/assistants/default" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 创建助手

```bash
curl -X POST "$DATAAGENT_URL/api/v1/assistants" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "代码助手",
    "description": "专注于代码开发的助手",
    "system_prompt": "你是一个专业的代码开发助手...",
    "auto_approve": false
  }' | jq
```

### 更新助手

```bash
curl -X PUT "$DATAAGENT_URL/api/v1/assistants/abc123" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "代码助手 v2",
    "description": "更新后的描述"
  }' | jq
```

### 删除助手

```bash
curl -X DELETE "$DATAAGENT_URL/api/v1/assistants/abc123" \
  -H "X-User-ID: $DATAAGENT_USER_ID"
```

## 用户管理

### 获取用户记忆状态

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/memory/status" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 清除用户记忆

```bash
curl -X DELETE "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/memory" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

## 用户档案管理

### 列出用户档案

```bash
curl -s "$DATAAGENT_URL/api/v1/user-profiles" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 创建用户档案

```bash
curl -X POST "$DATAAGENT_URL/api/v1/user-profiles" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "user_id": "user123",
    "username": "zhangsan",
    "display_name": "张三",
    "email": "zhangsan@example.com",
    "department": "技术部",
    "role": "开发工程师",
    "custom_fields": {"team": "AI团队"}
  }' | jq
```

### 获取用户档案

```bash
curl -s "$DATAAGENT_URL/api/v1/user-profiles/user123" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 更新用户档案

```bash
curl -X PUT "$DATAAGENT_URL/api/v1/user-profiles/user123" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "user_id": "user123",
    "username": "zhangsan",
    "display_name": "张三（更新）",
    "department": "AI部门",
    "role": "高级工程师"
  }' | jq
```

### 删除用户档案

```bash
curl -X DELETE "$DATAAGENT_URL/api/v1/user-profiles/user123" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

## MCP 服务器管理

### 列出 MCP 服务器

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 添加 MCP 服务器（命令行方式）

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "aws-docs",
    "command": "uvx",
    "args": ["awslabs.aws-documentation-mcp-server@latest"],
    "env": {"FASTMCP_LOG_LEVEL": "ERROR"},
    "disabled": false,
    "autoApprove": []
  }' | jq
```

### 添加 MCP 服务器（HTTP/SSE 方式）

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "remote-mcp",
    "url": "http://localhost:3000/mcp",
    "transport": "sse",
    "headers": {"Authorization": "Bearer your-token"},
    "disabled": false
  }' | jq
```

### 获取 MCP 服务器详情

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 获取 MCP 服务器状态

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/status" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 连接 MCP 服务器

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/connect" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 断开 MCP 服务器

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/disconnect" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 启用/禁用 MCP 服务器

```bash
# 禁用
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/toggle" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{"disabled": true}' | jq

# 启用
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/toggle" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{"disabled": false}' | jq
```

### 删除 MCP 服务器

```bash
curl -X DELETE "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

## 规则管理

### 列出规则

```bash
# 列出所有规则
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq

# 按范围过滤
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules?scope=user" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 创建规则

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "code-style",
    "description": "代码风格规范",
    "content": "请遵循以下代码风格：\n1. 使用 4 空格缩进\n2. 函数名使用小写下划线\n3. 类名使用大驼峰",
    "scope": "user",
    "inclusion": "always",
    "priority": 50,
    "enabled": true
  }' | jq
```

### 获取规则详情

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules/code-style" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 更新规则

```bash
curl -X PUT "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules/code-style" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "description": "更新后的代码风格规范",
    "content": "更新后的内容...",
    "enabled": true
  }' | jq
```

### 删除规则

```bash
curl -X DELETE "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules/code-style" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 验证规则内容

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules/validate" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "content": "这是规则内容..."
  }' | jq
```

### 检测规则冲突

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules/conflicts/list" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 重新加载规则

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules/reload" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

## 错误处理

所有 API 错误返回统一格式：

```json
{
  "error_code": "ERROR_CODE",
  "message": "错误描述",
  "details": {}
}
```

常见错误码：

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| `SESSION_NOT_FOUND` | 404 | 会话不存在 |
| `INVALID_REQUEST` | 400 | 请求参数错误 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

## 脚本示例

### 交互式聊天脚本

```bash
#!/bin/bash
# interactive-chat.sh

DATAAGENT_URL="${DATAAGENT_URL:-http://localhost:8000}"
SESSION_ID=""

chat() {
    local message="$1"
    local response=$(curl -s -X POST "$DATAAGENT_URL/api/v1/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"session_id\": $SESSION_ID}")
    
    SESSION_ID=$(echo "$response" | jq -r '.session_id')
    echo "$response" | jq -r '.events[] | select(.event_type == "text") | .content'
}

echo "DataAgent 交互式聊天 (输入 'quit' 退出)"
while true; do
    read -p "你: " input
    [[ "$input" == "quit" ]] && break
    echo -n "Agent: "
    chat "$input"
    echo
done
```

### 批量测试脚本

```bash
#!/bin/bash
# batch-test.sh

DATAAGENT_URL="${DATAAGENT_URL:-http://localhost:8000}"

messages=(
    "你好"
    "1+1等于几？"
    "今天天气怎么样？"
)

for msg in "${messages[@]}"; do
    echo "发送: $msg"
    curl -s -X POST "$DATAAGENT_URL/api/v1/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$msg\"}" | jq -r '.events[] | select(.event_type == "text") | .content'
    echo "---"
done
```
