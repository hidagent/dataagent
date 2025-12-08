# React 集成示例

本文档提供 DataAgent 与 React 应用集成的完整示例。

## 安装依赖

```bash
npm install
# 或
yarn
```

## 项目结构

```
src/
├── hooks/
│   ├── useDataAgent.ts      # REST API Hook
│   ├── useStreamChat.ts     # SSE 流式 Hook
│   └── useWebSocketChat.ts  # WebSocket Hook
├── components/
│   ├── ChatWindow.tsx       # 聊天窗口组件
│   ├── MessageList.tsx      # 消息列表组件
│   ├── MessageInput.tsx     # 输入框组件
│   └── HITLDialog.tsx       # HITL 审批对话框
├── services/
│   └── dataagent.ts         # API 服务
└── types/
    └── chat.ts              # 类型定义
```

## 类型定义

```typescript
// src/types/chat.ts

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    toolCalls?: ToolCall[];
}

export interface ToolCall {
    id: string;
    name: string;
    args: Record<string, unknown>;
    result?: string;
}

export interface ChatEvent {
    event_type: string;
    data?: Record<string, unknown>;
    content?: string;
    timestamp?: number;
}

export interface HITLAction {
    name: string;
    args: Record<string, unknown>;
    description?: string;
}

export interface UserContext {
    user_id: string;
    username?: string;
    display_name?: string;
    department?: string;
    role?: string;
    custom_fields?: Record<string, unknown>;
}
```

## API 服务

```typescript
// src/services/dataagent.ts

const BASE_URL = process.env.REACT_APP_DATAAGENT_URL || 'http://localhost:8000';

export class DataAgentService {
    private apiKey?: string;
    private userId: string;
    
    constructor(userId: string, apiKey?: string) {
        this.userId = userId;
        this.apiKey = apiKey;
    }
    
    private getHeaders(): HeadersInit {
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            'X-User-ID': this.userId,
        };
        
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        return headers;
    }
    
    async chat(message: string, sessionId?: string): Promise<{
        sessionId: string;
        events: ChatEvent[];
    }> {
        const response = await fetch(`${BASE_URL}/api/v1/chat`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ message, session_id: sessionId }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        return {
            sessionId: data.session_id,
            events: data.events,
        };
    }
    
    async *streamChat(
        message: string,
        sessionId?: string
    ): AsyncGenerator<ChatEvent> {
        const response = await fetch(`${BASE_URL}/api/v1/chat/stream`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ message, session_id: sessionId }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            for (const line of chunk.split('\n')) {
                if (line.startsWith('data: ')) {
                    yield JSON.parse(line.slice(6));
                }
            }
        }
    }
    
    async getMessages(sessionId: string, limit = 100): Promise<Message[]> {
        const response = await fetch(
            `${BASE_URL}/api/v1/sessions/${sessionId}/messages?limit=${limit}`,
            { headers: this.getHeaders() }
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        return data.messages;
    }
}
```

## React Hooks

### useStreamChat Hook

```typescript
// src/hooks/useStreamChat.ts

import { useState, useCallback, useRef } from 'react';
import { Message, ChatEvent } from '../types/chat';

interface UseStreamChatOptions {
    baseUrl?: string;
    userId?: string;
    apiKey?: string;
    onToolCall?: (toolName: string, args: unknown) => void;
}

export function useStreamChat(options: UseStreamChatOptions = {}) {
    const {
        baseUrl = 'http://localhost:8000',
        userId = 'anonymous',
        apiKey,
        onToolCall,
    } = options;
    
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [error, setError] = useState<Error | null>(null);
    
    const abortControllerRef = useRef<AbortController | null>(null);
    
    const sendMessage = useCallback(async (content: string) => {
        setIsLoading(true);
        setError(null);
        
        // 添加用户消息
        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMessage]);
        
        // 创建助手消息占位
        const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            toolCalls: [],
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        try {
            abortControllerRef.current = new AbortController();
            
            const headers: HeadersInit = {
                'Content-Type': 'application/json',
                'X-User-ID': userId,
            };
            if (apiKey) headers['X-API-Key'] = apiKey;
            
            const response = await fetch(`${baseUrl}/api/v1/chat/stream`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    message: content,
                    session_id: sessionId,
                }),
                signal: abortControllerRef.current.signal,
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            // 获取新的 session_id
            const newSessionId = response.headers.get('X-Session-ID');
            if (newSessionId) setSessionId(newSessionId);
            
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                for (const line of chunk.split('\n')) {
                    if (line.startsWith('data: ')) {
                        const event: ChatEvent = JSON.parse(line.slice(6));
                        
                        if (event.event_type === 'text') {
                            const text = event.data?.content as string || '';
                            setMessages(prev => {
                                const updated = [...prev];
                                const last = updated[updated.length - 1];
                                if (last.role === 'assistant') {
                                    last.content += text;
                                }
                                return updated;
                            });
                        } else if (event.event_type === 'tool_call') {
                            const toolName = event.data?.tool_name as string;
                            const toolArgs = event.data?.tool_args;
                            onToolCall?.(toolName, toolArgs);
                            
                            setMessages(prev => {
                                const updated = [...prev];
                                const last = updated[updated.length - 1];
                                if (last.role === 'assistant') {
                                    last.toolCalls = [
                                        ...(last.toolCalls || []),
                                        {
                                            id: event.data?.tool_call_id as string,
                                            name: toolName,
                                            args: toolArgs as Record<string, unknown>,
                                        },
                                    ];
                                }
                                return updated;
                            });
                        }
                    }
                }
            }
        } catch (err) {
            if (err instanceof Error && err.name !== 'AbortError') {
                setError(err);
            }
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
        }
    }, [baseUrl, userId, apiKey, sessionId, onToolCall]);
    
    const cancel = useCallback(() => {
        abortControllerRef.current?.abort();
    }, []);
    
    const clearMessages = useCallback(() => {
        setMessages([]);
        setSessionId(null);
    }, []);
    
    return {
        messages,
        isLoading,
        sessionId,
        error,
        sendMessage,
        cancel,
        clearMessages,
    };
}
```

### useWebSocketChat Hook

```typescript
// src/hooks/useWebSocketChat.ts

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message, HITLAction } from '../types/chat';

interface UseWebSocketChatOptions {
    baseUrl?: string;
    userId?: string;
    onHITL?: (action: HITLAction) => Promise<'approve' | 'reject'>;
}

export function useWebSocketChat(options: UseWebSocketChatOptions = {}) {
    const {
        baseUrl = 'ws://localhost:8000',
        userId = 'anonymous',
        onHITL,
    } = options;
    
    const [messages, setMessages] = useState<Message[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    
    const wsRef = useRef<WebSocket | null>(null);
    const pendingHITLRef = useRef<((decision: string) => void) | null>(null);
    
    const connect = useCallback((newSessionId?: string) => {
        const sid = newSessionId || `session-${Math.random().toString(36).substr(2, 9)}`;
        setSessionId(sid);
        
        const ws = new WebSocket(`${baseUrl}/ws/chat/${sid}`);
        
        ws.onopen = () => {
            setIsConnected(true);
        };
        
        ws.onclose = () => {
            setIsConnected(false);
        };
        
        ws.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.event_type) {
                case 'connected':
                    console.log('Connected to session:', data.data.session_id);
                    break;
                    
                case 'text':
                    setMessages(prev => {
                        const updated = [...prev];
                        const last = updated[updated.length - 1];
                        if (last?.role === 'assistant') {
                            last.content += data.data.content || '';
                        } else {
                            updated.push({
                                id: Date.now().toString(),
                                role: 'assistant',
                                content: data.data.content || '',
                                timestamp: new Date(),
                            });
                        }
                        return updated;
                    });
                    break;
                    
                case 'hitl':
                    if (onHITL) {
                        const decision = await onHITL(data.data.action);
                        ws.send(JSON.stringify({
                            type: 'hitl_decision',
                            payload: { decisions: [{ type: decision }] },
                        }));
                    }
                    break;
                    
                case 'done':
                    setIsLoading(false);
                    break;
                    
                case 'error':
                    console.error('WebSocket error:', data.data.message);
                    setIsLoading(false);
                    break;
            }
        };
        
        wsRef.current = ws;
    }, [baseUrl, onHITL]);
    
    const disconnect = useCallback(() => {
        wsRef.current?.close();
        wsRef.current = null;
        setIsConnected(false);
    }, []);
    
    const sendMessage = useCallback((content: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }
        
        setIsLoading(true);
        
        // 添加用户消息
        setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'user',
            content,
            timestamp: new Date(),
        }]);
        
        wsRef.current.send(JSON.stringify({
            type: 'chat',
            payload: { message: content, user_id: userId },
        }));
    }, [userId]);
    
    const cancel = useCallback(() => {
        wsRef.current?.send(JSON.stringify({
            type: 'cancel',
            payload: {},
        }));
    }, []);
    
    useEffect(() => {
        return () => {
            disconnect();
        };
    }, [disconnect]);
    
    return {
        messages,
        isConnected,
        isLoading,
        sessionId,
        connect,
        disconnect,
        sendMessage,
        cancel,
    };
}
```

## 组件示例

### ChatWindow 组件

```tsx
// src/components/ChatWindow.tsx

import React, { useState } from 'react';
import { useStreamChat } from '../hooks/useStreamChat';

export function ChatWindow() {
    const [input, setInput] = useState('');
    const { messages, isLoading, sendMessage, clearMessages } = useStreamChat({
        baseUrl: 'http://localhost:8000',
        userId: 'demo-user',
    });
    
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !isLoading) {
            sendMessage(input.trim());
            setInput('');
        }
    };
    
    return (
        <div className="chat-window">
            <div className="chat-header">
                <h2>DataAgent Chat</h2>
                <button onClick={clearMessages}>清空</button>
            </div>
            
            <div className="messages">
                {messages.map(msg => (
                    <div key={msg.id} className={`message ${msg.role}`}>
                        <div className="content">{msg.content}</div>
                        {msg.toolCalls?.map(tool => (
                            <div key={tool.id} className="tool-call">
                                🔧 {tool.name}
                            </div>
                        ))}
                    </div>
                ))}
                {isLoading && (
                    <div className="message assistant loading">
                        思考中...
                    </div>
                )}
            </div>
            
            <form onSubmit={handleSubmit} className="input-form">
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="输入消息..."
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading || !input.trim()}>
                    发送
                </button>
            </form>
        </div>
    );
}
```

### HITLDialog 组件

```tsx
// src/components/HITLDialog.tsx

import React from 'react';
import { HITLAction } from '../types/chat';

interface HITLDialogProps {
    action: HITLAction;
    onDecision: (decision: 'approve' | 'reject') => void;
}

export function HITLDialog({ action, onDecision }: HITLDialogProps) {
    return (
        <div className="hitl-overlay">
            <div className="hitl-dialog">
                <h3>操作审批请求</h3>
                <p>Agent 请求执行以下操作：</p>
                
                <div className="action-details">
                    <div className="action-name">{action.name}</div>
                    {action.description && (
                        <div className="action-desc">{action.description}</div>
                    )}
                    <pre className="action-args">
                        {JSON.stringify(action.args, null, 2)}
                    </pre>
                </div>
                
                <div className="dialog-buttons">
                    <button
                        className="reject"
                        onClick={() => onDecision('reject')}
                    >
                        拒绝
                    </button>
                    <button
                        className="approve"
                        onClick={() => onDecision('approve')}
                    >
                        批准
                    </button>
                </div>
            </div>
        </div>
    );
}
```

## 样式示例

```css
/* src/styles/chat.css */

.chat-window {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 800px;
    margin: 0 auto;
}

.chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: #1a73e8;
    color: white;
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.message {
    margin-bottom: 12px;
    padding: 12px 16px;
    border-radius: 12px;
    max-width: 70%;
}

.message.user {
    background: #1a73e8;
    color: white;
    margin-left: auto;
}

.message.assistant {
    background: #f0f0f0;
    color: #333;
}

.message.loading {
    color: #999;
    font-style: italic;
}

.tool-call {
    margin-top: 8px;
    padding: 8px;
    background: #fff3e0;
    border-radius: 4px;
    font-size: 12px;
}

.input-form {
    display: flex;
    padding: 16px;
    gap: 12px;
    border-top: 1px solid #eee;
}

.input-form input {
    flex: 1;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 24px;
    font-size: 14px;
}

.input-form button {
    padding: 12px 24px;
    background: #1a73e8;
    color: white;
    border: none;
    border-radius: 24px;
    cursor: pointer;
}

.input-form button:disabled {
    background: #ccc;
}

.hitl-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
}

.hitl-dialog {
    background: white;
    padding: 24px;
    border-radius: 12px;
    max-width: 500px;
    width: 90%;
}

.action-details {
    background: #f5f5f5;
    padding: 12px;
    border-radius: 8px;
    margin: 16px 0;
}

.action-args {
    font-size: 12px;
    overflow-x: auto;
}

.dialog-buttons {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}

.dialog-buttons button {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.dialog-buttons .approve {
    background: #4caf50;
    color: white;
}

.dialog-buttons .reject {
    background: #f44336;
    color: white;
}
```

## 使用示例

```tsx
// src/App.tsx

import React from 'react';
import { ChatWindow } from './components/ChatWindow';
import './styles/chat.css';

function App() {
    return (
        <div className="app">
            <ChatWindow />
        </div>
    );
}

export default App;
```

## 环境配置

```env
# .env
REACT_APP_DATAAGENT_URL=http://localhost:8000
REACT_APP_DATAAGENT_API_KEY=your-api-key
```
