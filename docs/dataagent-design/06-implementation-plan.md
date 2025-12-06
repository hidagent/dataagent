# DataAgent 架构设计方案

## 第六章：实施计划

### 6.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           实施阶段                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: Core 抽取 (2周)                                                   │
│  ├── 创建 dataagent-core 项目结构                                           │
│  ├── 迁移核心模块 (agent, middleware, tools)                                │
│  ├── 实现事件系统                                                           │
│  ├── 实现 HITL 协议                                                         │
│  └── 单元测试                                                               │
│                                                                             │
│  Phase 2: CLI 重构 (1周)                                                    │
│  ├── 创建 dataagent-cli 项目结构                                            │
│  ├── 实现终端渲染器                                                         │
│  ├── 实现终端 HITL 处理器                                                   │
│  └── 集成测试                                                               │
│                                                                             │
│  Phase 3: Server 开发 (2周)                                                 │
│  ├── 创建 dataagent-server 项目结构                                         │
│  ├── 实现 WebSocket 处理                                                    │
│  ├── 实现 REST API                                                          │
│  ├── 实现会话管理                                                           │
│  └── 集成测试                                                               │
│                                                                             │
│  Phase 4: 集成与优化 (1周)                                                  │
│  ├── ChatUI 集成测试                                                        │
│  ├── 性能优化                                                               │
│  ├── 文档完善                                                               │
│  └── 部署准备                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Phase 1: DataAgentCore 抽取

#### 6.2.1 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|---------|------|
| 创建项目结构和 pyproject.toml | P0 | 2h | - |
| 迁移 config.py (Settings 部分) | P0 | 4h | 项目结构 |
| 迁移 agent.py → engine/factory.py | P0 | 8h | config |
| 迁移 agent_memory.py → middleware/memory.py | P0 | 4h | config |
| 迁移 skills/* → skills/ + middleware/skills.py | P0 | 4h | config |
| 迁移 shell.py → middleware/shell.py | P0 | 2h | - |
| 迁移 tools.py → tools/web.py | P0 | 2h | - |
| 迁移 file_ops.py → tools/file_tracker.py | P0 | 4h | - |
| 迁移 integrations/* → sandbox/ | P1 | 4h | - |
| 实现事件系统 events/* | P0 | 8h | - |
| 实现 HITL 协议 hitl/* | P0 | 4h | - |
| 实现执行器 engine/executor.py | P0 | 16h | 事件系统, HITL |
| 实现会话管理 session/* | P1 | 8h | - |
| 单元测试 | P0 | 16h | 全部 |

#### 6.2.2 关键改动点

**config.py 拆分**:
```python
# 保留到 Core
class Settings:
    # API keys
    # 路径管理
    # 模型创建

# 移除 (CLI 特有)
COLORS = {...}
DEEP_AGENTS_ASCII = ...
console = Console()
```

**execution.py 重构**:
```python
# 原始代码 (混合)
async def execute_task(...):
    # 核心执行逻辑
    # 终端渲染
    # HITL 交互

# 重构后
# Core: AgentExecutor.execute() -> AsyncIterator[ExecutionEvent]
# CLI: TerminalRenderer.render_events(events)
```

### 6.3 Phase 2: DataAgentCli 重构

#### 6.3.1 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|---------|------|
| 创建项目结构 | P0 | 2h | Core 完成 |
| 迁移 ui.py → ui/renderer.py | P0 | 8h | Core 事件系统 |
| 迁移 input.py → input/ | P0 | 4h | - |
| 实现 TerminalHITLHandler | P0 | 4h | Core HITL |
| 迁移 commands.py → commands/ | P0 | 4h | - |
| 重构 main.py | P0 | 8h | 全部 |
| 集成测试 | P0 | 8h | 全部 |

#### 6.3.2 兼容性保证

```python
# 保持命令行接口不变
dataagent                    # 交互模式
dataagent --agent mybot      # 指定 agent
dataagent --auto-approve     # 自动审批
dataagent --sandbox modal    # 沙箱模式
dataagent list               # 列出 agents
dataagent reset --agent xxx  # 重置 agent
```

### 6.4 Phase 3: DataAgentServer 开发

#### 6.4.1 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|---------|------|
| 创建项目结构 | P0 | 2h | Core 完成 |
| 实现 ConnectionManager | P0 | 4h | - |
| 实现 WebSocketHITLHandler | P0 | 4h | Core HITL |
| 实现 WebSocketChatHandler | P0 | 8h | ConnectionManager |
| 实现 ChatService | P0 | 8h | Core |
| 实现 SessionService | P0 | 4h | Core Session |
| 实现 REST API (chat) | P0 | 4h | ChatService |
| 实现 REST API (sessions) | P1 | 4h | SessionService |
| 实现认证中间件 | P1 | 8h | - |
| 数据库集成 | P1 | 8h | - |
| 集成测试 | P0 | 16h | 全部 |

#### 6.4.2 API 端点清单

```
WebSocket:
  /ws/chat                    # 聊天 WebSocket

REST API:
  POST   /api/v1/chat/message         # 发送消息 (非流式)
  POST   /api/v1/chat/message/stream  # 发送消息 (SSE)
  
  GET    /api/v1/sessions             # 列出会话
  GET    /api/v1/sessions/{id}        # 获取会话
  DELETE /api/v1/sessions/{id}        # 删除会话
  GET    /api/v1/sessions/{id}/messages  # 获取消息历史
  
  GET    /api/v1/agents               # 列出 agents
  POST   /api/v1/agents               # 创建 agent
  
  GET    /api/v1/skills               # 列出技能
  POST   /api/v1/skills               # 创建技能
```

### 6.5 Phase 4: 集成与优化

#### 6.5.1 ChatUI 集成

```typescript
// 前端 WebSocket 客户端示例
class DataAgentClient {
  private ws: WebSocket;
  
  connect(token: string) {
    this.ws = new WebSocket(`ws://server/ws/chat?token=${token}`);
    this.ws.onmessage = this.handleMessage.bind(this);
  }
  
  sendMessage(message: string) {
    this.ws.send(JSON.stringify({
      type: "chat",
      payload: { message },
    }));
  }
  
  handleMessage(event: MessageEvent) {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
      case "text":
        this.onText(msg.data);
        break;
      case "tool_call":
        this.onToolCall(msg.data);
        break;
      case "hitl_request":
        this.onHITLRequest(msg.data);
        break;
      // ...
    }
  }
  
  approveAction(interruptId: string) {
    this.ws.send(JSON.stringify({
      type: "hitl_decision",
      payload: {
        interrupt_id: interruptId,
        decisions: [{ type: "approve" }],
      },
    }));
  }
}
```

#### 6.5.2 性能优化

| 优化项 | 方案 |
|--------|------|
| 连接池 | Redis 连接池、数据库连接池 |
| 缓存 | Agent 实例缓存、会话状态缓存 |
| 并发 | asyncio 并发处理多会话 |
| 流式 | 真正的流式响应，减少延迟 |

### 6.6 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| deepagents 库 API 变更 | 高 | 锁定版本，抽象适配层 |
| HITL 超时处理 | 中 | 设置合理超时，支持重连 |
| 会话状态丢失 | 中 | Redis 持久化，定期快照 |
| 并发性能 | 中 | 压测，优化热点 |

### 6.7 里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| M1: Core Alpha | Week 2 | dataagent-core 可用 |
| M2: CLI Beta | Week 3 | dataagent-cli 功能完整 |
| M3: Server Beta | Week 5 | dataagent-server API 可用 |
| M4: Release | Week 6 | 全部组件集成完成 |

---

下一章：[07-appendix.md](./07-appendix.md) - 附录
