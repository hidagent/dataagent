# DataAgent Web 前后端对接示例

本目录包含 DataAgent Server 与前端系统对接的完整示例，帮助第三方系统快速集成。

## 目录结构

```
web-integration/
├── README.md                    # 本文档
├── frontend/                    # 前端示例
│   ├── vanilla-js/             # 原生 JavaScript 示例
│   │   └── index.html          # 完整的聊天界面
│   └── react-example.md        # React 集成指南
├── backend/                     # 后端客户端示例
│   ├── python-client.py        # Python SDK 示例
│   └── curl-examples.md        # cURL 命令示例
└── integration-guide.md        # 完整集成指南
```

## 快速开始

### 1. 启动 DataAgent Server

```bash
cd source/dataagent-server
pip install -e .
dataagent-server
```

服务默认运行在 `http://localhost:8000`

### 2. 测试 API

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 发送消息（同步）
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

### 3. 打开前端示例

直接在浏览器中打开 `frontend/vanilla-js/index.html`，或使用本地服务器：

```bash
cd examples/web-integration/frontend/vanilla-js
python -m http.server 3000
# 访问 http://localhost:3000
```

## API 概览

### REST API

#### 核心 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/chat` | POST | 发送消息（同步响应） |
| `/api/v1/chat/stream` | POST | 发送消息（SSE 流式响应） |
| `/api/v1/sessions` | GET | 列出会话 |
| `/api/v1/sessions/{id}` | GET | 获取会话详情 |
| `/api/v1/sessions/{id}/messages` | GET | 获取历史消息 |
| `/api/v1/assistants` | GET/POST/PUT/DELETE | 助手管理 |

#### 用户管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/user-profiles` | GET/POST | 用户档案列表/创建 |
| `/api/v1/user-profiles/{user_id}` | GET/PUT/DELETE | 用户档案详情/更新/删除 |
| `/api/v1/users/{user_id}/memory/status` | GET | 获取用户记忆状态 |
| `/api/v1/users/{user_id}/memory` | DELETE | 清除用户记忆 |

#### MCP 服务器管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/users/{user_id}/mcp-servers` | GET/POST | MCP 服务器列表/添加 |
| `/api/v1/users/{user_id}/mcp-servers/{name}` | GET/PUT/DELETE | MCP 服务器详情/更新/删除 |
| `/api/v1/users/{user_id}/mcp-servers/{name}/status` | GET | 获取连接状态 |
| `/api/v1/users/{user_id}/mcp-servers/{name}/connect` | POST | 连接服务器 |
| `/api/v1/users/{user_id}/mcp-servers/{name}/disconnect` | POST | 断开连接 |
| `/api/v1/users/{user_id}/mcp-servers/{name}/toggle` | POST | 启用/禁用 |

#### 规则管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/users/{user_id}/rules` | GET/POST | 规则列表/创建 |
| `/api/v1/users/{user_id}/rules/{name}` | GET/PUT/DELETE | 规则详情/更新/删除 |
| `/api/v1/users/{user_id}/rules/validate` | POST | 验证规则内容 |
| `/api/v1/users/{user_id}/rules/conflicts/list` | GET | 检测规则冲突 |
| `/api/v1/users/{user_id}/rules/reload` | POST | 重新加载规则 |

### WebSocket

```
ws://localhost:8000/ws/chat/{session_id}
```

支持实时双向通信，包括 HITL（人机交互）审批。

## 认证

通过 `X-API-Key` Header 进行认证：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/chat
```

用户标识通过 `X-User-ID` Header 传递：

```bash
curl -H "X-User-ID: user123" http://localhost:8000/api/v1/sessions
```

## 详细文档

- [完整集成指南](./integration-guide.md)
- [API 参考文档](../../docs/api-reference.md)
- [架构设计](../../docs/architecture.md)
