# DataAgent 前后端集成指南

本指南详细介绍如何将 DataAgent Server 集成到第三方系统或 Web 前端中。

## 目录

1. [架构概览](#架构概览)
2. [通信方式选择](#通信方式选择)
3. [REST API 集成](#rest-api-集成)
4. [SSE 流式集成](#sse-流式集成)
5. [WebSocket 集成](#websocket-集成)
6. [认证与安全](#认证与安全)
7. [用户上下文](#用户上下文)
8. [错误处理](#错误处理)
9. [最佳实践](#最佳实践)

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        第三方系统 / Web 前端                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐  │
│   │  REST API   │   │  SSE 流式   │   │      WebSocket          │  │
│   │  (同步请求)  │   │  (单向流)   │   │    (双向实时通信)        │  │
│   └──────┬──────┘   └──────┬──────┘   └───────────┬─────────────┘  │
│          │                 │                      │                 │
└──────────┼─────────────────┼──────────────────────┼─────────────────┘
           │                 │                      │
           ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DataAgent Server                                │
│                                                                     │
│   POST /api/v1/chat      POST /api/v1/chat/stream    /ws/chat/{id} │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 通信方式选择

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| REST API | 简单集成、后端调用 | 实现简单、兼容性好 | 无法实时显示进度 |
| SSE 流式 | Web 前端、需要流式输出 | 实时显示、实现较简单 | 单向通信、无 HITL |
| WebSocket | 完整功能、需要 HITL | 双向通信、支持 HITL | 实现复杂、需维护连接 |

### 推荐选择

- **简单集成**：REST API
- **Web 聊天界面**：SSE 流式（无需 HITL）或 WebSocket（需要 HITL）
- **企业级应用**：WebSocket（完整功能支持）

## REST API 集成

### 基本流程

```
客户端                                    服务端
   │                                        │
   │  POST /api/v1/chat                     │
   │  {message, session_id}                 │
   │ ─────────────────────────────────────► │
   │                                        │
   │         等待 Agent 完成处理              │
   │                                        │
   │  {session_id, events: [...]}           │
   │ ◄───────────────────────────────────── │
   │                                        │
```

### JavaScript 示例

```javascript
class DataAgentClient {
    constructor(baseUrl = 'http://localhost:8000', apiKey = null) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.sessionId = null;
    }
    
    async chat(message) {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                message,
                session_id: this.sessionId,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        this.sessionId = data.session_id;
        
        // 提取文本内容
        const textContent = data.events
            .filter(e => e.event_type === 'text')
            .map(e => e.content)
            .join('');
        
        return {
            sessionId: data.session_id,
            content: textContent,
            events: data.events,
        };
    }
}

// 使用示例
const client = new DataAgentClient();
const result = await client.chat('你好');
console.log(result.content);
```

## SSE 流式集成

### 基本流程

```
客户端                                    服务端
   │                                        │
   │  POST /api/v1/chat/stream              │
   │  {message, session_id}                 │
   │ ─────────────────────────────────────► │
   │                                        │
   │  data: {event_type: "text", ...}       │
   │ ◄───────────────────────────────────── │
   │                                        │
   │  data: {event_type: "text", ...}       │
   │ ◄───────────────────────────────────── │
   │                                        │
   │  data: {event_type: "done", ...}       │
   │ ◄───────────────────────────────────── │
   │                                        │
```

### JavaScript 示例

```javascript
async function* streamChat(message, sessionId = null) {
    const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const event = JSON.parse(line.slice(6));
                yield event;
            }
        }
    }
}

// 使用示例
const messageDiv = document.getElementById('message');

for await (const event of streamChat('你好')) {
    if (event.event_type === 'text') {
        const content = event.data?.content || event.content || '';
        messageDiv.textContent += content;
    }
}
```

### React Hook 示例

```jsx
import { useState, useCallback } from 'react';

function useStreamChat(baseUrl = '/api/v1') {
    const [isLoading, setIsLoading] = useState(false);
    const [content, setContent] = useState('');
    const [sessionId, setSessionId] = useState(null);
    
    const sendMessage = useCallback(async (message) => {
        setIsLoading(true);
        setContent('');
        
        try {
            const response = await fetch(`${baseUrl}/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, session_id: sessionId }),
            });
            
            const newSessionId = response.headers.get('X-Session-ID');
            if (newSessionId) setSessionId(newSessionId);
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                for (const line of chunk.split('\n')) {
                    if (line.startsWith('data: ')) {
                        const event = JSON.parse(line.slice(6));
                        if (event.event_type === 'text') {
                            const text = event.data?.content || '';
                            setContent(prev => prev + text);
                        }
                    }
                }
            }
        } finally {
            setIsLoading(false);
        }
    }, [baseUrl, sessionId]);
    
    return { sendMessage, content, isLoading, sessionId };
}

// 使用示例
function ChatComponent() {
    const { sendMessage, content, isLoading } = useStreamChat();
    const [input, setInput] = useState('');
    
    const handleSubmit = () => {
        sendMessage(input);
        setInput('');
    };
    
    return (
        <div>
            <div>{content}</div>
            <input value={input} onChange={e => setInput(e.target.value)} />
            <button onClick={handleSubmit} disabled={isLoading}>
                发送
            </button>
        </div>
    );
}
```

## WebSocket 集成

### 消息协议

#### 客户端 → 服务端

```typescript
interface ClientMessage {
    type: 'chat' | 'hitl_decision' | 'cancel' | 'ping' | 'set_user_context';
    payload: object;
}
```

#### 服务端 → 客户端

```typescript
interface ServerEvent {
    event_type: string;  // connected, text, tool_call, hitl, done, error, pong
    data: object;
    timestamp: number;
}
```

### JavaScript 示例

```javascript
class DataAgentWebSocket {
    constructor(baseUrl = 'ws://localhost:8000') {
        this.baseUrl = baseUrl;
        this.ws = null;
        this.sessionId = null;
        this.messageHandlers = new Map();
    }
    
    connect(sessionId = null) {
        this.sessionId = sessionId || this.generateSessionId();
        const url = `${this.baseUrl}/ws/chat/${this.sessionId}`;
        
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(url);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
                
                if (data.event_type === 'connected') {
                    resolve(data.data.session_id);
                }
            };
            
            this.ws.onerror = (error) => {
                reject(error);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
            };
        });
    }
    
    handleEvent(event) {
        const handler = this.messageHandlers.get(event.event_type);
        if (handler) {
            handler(event.data, event);
        }
    }
    
    on(eventType, handler) {
        this.messageHandlers.set(eventType, handler);
        return this;
    }
    
    sendChat(message, userId = null) {
        this.ws.send(JSON.stringify({
            type: 'chat',
            payload: { message, user_id: userId },
        }));
    }
    
    sendHITLDecision(decision) {
        this.ws.send(JSON.stringify({
            type: 'hitl_decision',
            payload: { decisions: [{ type: decision }] },
        }));
    }
    
    cancel() {
        this.ws.send(JSON.stringify({
            type: 'cancel',
            payload: {},
        }));
    }
    
    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
    
    generateSessionId() {
        return 'session-' + Math.random().toString(36).substr(2, 9);
    }
}

// 使用示例
const client = new DataAgentWebSocket();

client
    .on('text', (data) => {
        console.log('收到文本:', data.content);
    })
    .on('tool_call', (data) => {
        console.log('工具调用:', data.tool_name);
    })
    .on('hitl', (data) => {
        // 显示审批对话框
        if (confirm(`是否批准操作: ${data.action.name}?`)) {
            client.sendHITLDecision('approve');
        } else {
            client.sendHITLDecision('reject');
        }
    })
    .on('done', (data) => {
        console.log('完成:', data.cancelled ? '已取消' : '成功');
    })
    .on('error', (data) => {
        console.error('错误:', data.message);
    });

await client.connect();
client.sendChat('你好');
```

## 认证与安全

### API Key 认证

```javascript
// 在请求头中添加 API Key
const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key',
};
```

### 用户标识

```javascript
// 通过 X-User-ID 头传递用户标识
const headers = {
    'X-User-ID': 'user-123',
};
```

### CORS 配置

服务端默认允许所有来源，生产环境建议配置：

```bash
export DATAAGENT_CORS_ORIGINS="https://your-domain.com,https://app.your-domain.com"
```

## 用户上下文

可以在请求中传递用户上下文，用于个性化响应：

```javascript
const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: '你好',
        user_context: {
            user_id: 'user-123',
            username: 'zhangsan',
            display_name: '张三',
            department: '技术部',
            role: '开发工程师',
            custom_fields: {
                team: 'AI 团队',
            },
        },
    }),
});
```

## 错误处理

### 错误响应格式

```json
{
    "error_code": "SESSION_NOT_FOUND",
    "message": "Session abc123 not found",
    "details": {
        "session_id": "abc123"
    }
}
```

### 错误处理示例

```javascript
async function safeChat(message) {
    try {
        const response = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            
            switch (error.error_code) {
                case 'SESSION_NOT_FOUND':
                    // 重新创建会话
                    return safeChat(message);
                case 'SERVICE_UNAVAILABLE':
                    // 显示服务不可用提示
                    throw new Error('服务暂时不可用，请稍后重试');
                default:
                    throw new Error(error.message);
            }
        }
        
        return await response.json();
    } catch (error) {
        console.error('Chat error:', error);
        throw error;
    }
}
```

## 最佳实践

### 1. 会话管理

- 保存 `session_id` 以支持多轮对话
- 定期清理过期会话
- 考虑使用 localStorage 持久化会话 ID

### 2. 连接管理

- WebSocket 断线自动重连
- 实现心跳机制保持连接
- 处理网络切换场景

### 3. 用户体验

- 显示加载状态和进度
- 流式显示响应内容
- 提供取消操作的能力

### 4. 安全考虑

- 不在前端暴露 API Key
- 使用 HTTPS
- 验证用户身份

### 5. 性能优化

- 使用连接池
- 实现请求去重
- 考虑响应缓存

## 管理 API 集成

除了聊天功能，DataAgent 还提供完整的管理 API，用于用户管理、MCP 服务器配置和规则管理。

### 用户档案管理

```javascript
// 创建用户档案
async function createUserProfile(profile) {
    const response = await fetch('/api/v1/user-profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-ID': 'admin' },
        body: JSON.stringify(profile),
    });
    return response.json();
}

// 使用示例
await createUserProfile({
    user_id: 'user123',
    username: 'zhangsan',
    display_name: '张三',
    department: '技术部',
    role: '开发工程师',
});
```

### MCP 服务器管理

```javascript
// 添加 MCP 服务器
async function addMCPServer(userId, serverConfig) {
    const response = await fetch(`/api/v1/users/${userId}/mcp-servers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
        body: JSON.stringify(serverConfig),
    });
    return response.json();
}

// 连接 MCP 服务器
async function connectMCPServer(userId, serverName) {
    const response = await fetch(
        `/api/v1/users/${userId}/mcp-servers/${serverName}/connect`,
        {
            method: 'POST',
            headers: { 'X-User-ID': userId },
        }
    );
    return response.json();
}

// 使用示例
await addMCPServer('user123', {
    name: 'aws-docs',
    command: 'uvx',
    args: ['awslabs.aws-documentation-mcp-server@latest'],
});

const result = await connectMCPServer('user123', 'aws-docs');
console.log(`连接成功，可用工具: ${result.tools.join(', ')}`);
```

### 规则管理

```javascript
// 创建规则
async function createRule(userId, rule) {
    const response = await fetch(`/api/v1/users/${userId}/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
        body: JSON.stringify(rule),
    });
    return response.json();
}

// 使用示例
await createRule('user123', {
    name: 'code-style',
    description: '代码风格规范',
    content: '请遵循 PEP8 代码风格...',
    scope: 'user',
    inclusion: 'always',
    priority: 50,
    enabled: true,
});
```

### 管理界面集成示例

```html
<!-- 简单的管理界面 -->
<div id="admin-panel">
    <h3>MCP 服务器管理</h3>
    <div id="mcp-servers"></div>
    <button onclick="refreshMCPServers()">刷新</button>
    
    <h3>规则管理</h3>
    <div id="rules-list"></div>
    <button onclick="refreshRules()">刷新</button>
</div>

<script>
async function refreshMCPServers() {
    const userId = 'current-user';
    const response = await fetch(`/api/v1/users/${userId}/mcp-servers`, {
        headers: { 'X-User-ID': userId }
    });
    const data = await response.json();
    
    const container = document.getElementById('mcp-servers');
    container.innerHTML = data.servers.map(s => `
        <div class="server-item">
            <span class="status ${s.connected ? 'connected' : 'disconnected'}">●</span>
            <span class="name">${s.name}</span>
            <span class="tools">${s.tools_count} 工具</span>
            <button onclick="toggleServer('${s.name}', ${!s.disabled})">
                ${s.disabled ? '启用' : '禁用'}
            </button>
        </div>
    `).join('');
}

async function refreshRules() {
    const userId = 'current-user';
    const response = await fetch(`/api/v1/users/${userId}/rules`, {
        headers: { 'X-User-ID': userId }
    });
    const data = await response.json();
    
    const container = document.getElementById('rules-list');
    container.innerHTML = data.rules.map(r => `
        <div class="rule-item">
            <span class="status ${r.enabled ? 'enabled' : 'disabled'}">●</span>
            <span class="name">${r.name}</span>
            <span class="scope">${r.scope}</span>
        </div>
    `).join('');
}
</script>
```

## 完整示例项目

- `frontend/vanilla-js/index.html` - 完整的聊天界面示例
- `frontend/react-example.md` - React 集成指南
- `backend/python-client.py` - Python SDK 示例
- `backend/curl-examples.md` - cURL 命令示例
- `backend/admin-api-examples.md` - 管理 API 详细示例
