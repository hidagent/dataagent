# Requirements Document

## Introduction

本文档定义了 DataAgent 平台的开发规范和需求，旨在为后续的通用编码 Agent 提供统一的开发标准。DataAgent 是基于 DeepAgent 构建的数据智能助手平台，支持三类用户：数据开发工程师（CLI）、普通业务人员（Web ChatUI）和数据管理人员（Web 管理界面）。

本规范涵盖三个核心组件：
- **DataAgentCore**: 核心业务逻辑库，包含 Agent 引擎、中间件、工具系统、事件系统
- **DataAgentCli**: 终端交互客户端
- **DataAgentServer**: Web API 服务端

## Glossary

- **DataAgentCore**: 核心库，封装 Agent 创建、执行、中间件、工具等通用逻辑
- **DataAgentCli**: 命令行客户端，提供终端交互界面
- **DataAgentServer**: Web 服务端，通过 FastAPI 和 WebSocket 对外提供服务
- **Agent**: 基于 LLM 的智能代理，能够执行工具调用和任务处理
- **HITL (Human-In-The-Loop)**: 人机交互协议，用于敏感操作的用户审批
- **ExecutionEvent**: 执行事件，Agent 执行过程中产生的各类事件
- **Middleware**: 中间件，用于扩展 Agent 功能的可插拔组件
- **Skills**: 技能系统，可加载的领域知识和工具集合
- **Session**: 会话，用户与 Agent 的交互上下文
- **Backend**: 后端存储，用于文件系统操作和状态管理

## Requirements

### Requirement 1: 项目结构规范

**User Story:** As a 开发者, I want 统一的项目结构规范, so that 代码组织清晰且易于维护。

#### Acceptance Criteria

1. THE DataAgentCore 项目 SHALL 遵循以下目录结构：engine/（核心引擎）、events/（事件系统）、middleware/（中间件）、tools/（工具系统）、hitl/（HITL 协议）、config/（配置管理）、session/（会话管理）
2. THE DataAgentCli 项目 SHALL 遵循以下目录结构：ui/（终端渲染）、input/（输入处理）、hitl/（终端 HITL）、commands/（命令处理）
3. WHEN 创建新模块时 THEN 开发者 SHALL 在对应目录下创建 `__init__.py` 并导出公共接口
4. THE 每个 Python 包 SHALL 包含 `pyproject.toml` 定义依赖和元数据
5. WHEN 模块间存在依赖时 THEN 依赖关系 SHALL 遵循 Core → CLI/Server 的单向依赖原则

### Requirement 2: 事件系统规范

**User Story:** As a 开发者, I want 统一的事件系统, so that Agent 执行过程可被追踪和渲染。

#### Acceptance Criteria

1. THE 事件系统 SHALL 定义以下事件类型：TextEvent、ToolCallEvent、ToolResultEvent、HITLRequestEvent、TodoUpdateEvent、FileOperationEvent、ErrorEvent、DoneEvent
2. WHEN Agent 产生文本输出时 THEN 系统 SHALL 发出 TextEvent 包含 content 和 is_final 字段
3. WHEN Agent 调用工具时 THEN 系统 SHALL 发出 ToolCallEvent 包含 tool_name、tool_args、tool_call_id 字段
4. WHEN 工具执行完成时 THEN 系统 SHALL 发出 ToolResultEvent 包含 tool_call_id、result、status 字段
5. THE 每个事件 SHALL 继承 ExecutionEvent 基类并实现 to_dict() 方法用于序列化
6. THE 每个事件 SHALL 包含 event_type 和 timestamp 字段

### Requirement 3: HITL 协议规范

**User Story:** As a 开发者, I want 统一的 HITL 协议, so that 敏感操作能够获得用户审批。

#### Acceptance Criteria

1. THE HITLHandler 协议 SHALL 定义 request_approval(action_request, session_id) 异步方法
2. THE ActionRequest 类型 SHALL 包含 name、args、description 字段
3. THE Decision 类型 SHALL 包含 type（approve/reject）和 message 字段
4. WHEN 用户拒绝操作时 THEN 系统 SHALL 返回 Decision(type="reject") 并终止当前执行
5. WHEN 未配置 HITLHandler 时 THEN 系统 SHALL 自动批准所有操作
6. THE 终端 HITL 实现 SHALL 支持键盘导航选择 approve/reject/auto-approve-all

### Requirement 4: Agent 工厂规范

**User Story:** As a 开发者, I want 统一的 Agent 创建接口, so that 不同客户端能够一致地创建和配置 Agent。

#### Acceptance Criteria

1. THE AgentConfig 数据类 SHALL 包含以下配置项：assistant_id、model、enable_memory、enable_skills、enable_shell、auto_approve、sandbox_type、system_prompt、extra_tools、extra_middleware
2. THE AgentFactory.create_agent() 方法 SHALL 返回 (agent, backend) 元组
3. WHEN 未指定 model 时 THEN 工厂 SHALL 使用 Settings 中的默认模型
4. WHEN enable_memory 为 True 时 THEN 工厂 SHALL 添加 AgentMemoryMiddleware
5. WHEN enable_skills 为 True 时 THEN 工厂 SHALL 添加 SkillsMiddleware
6. WHEN sandbox_type 不为 None 时 THEN 工厂 SHALL 创建对应的沙箱后端

### Requirement 5: 执行器规范

**User Story:** As a 开发者, I want 统一的执行器接口, so that Agent 执行逻辑与 UI 渲染解耦。

#### Acceptance Criteria

1. THE AgentExecutor.execute() 方法 SHALL 返回 AsyncIterator[ExecutionEvent]
2. THE execute() 方法 SHALL 接受 user_input、session_id、context 参数
3. WHEN 执行过程中发生异常时 THEN 执行器 SHALL 发出 ErrorEvent 而非抛出异常
4. WHEN 执行正常完成时 THEN 执行器 SHALL 发出 DoneEvent(cancelled=False)
5. WHEN 用户拒绝 HITL 请求时 THEN 执行器 SHALL 发出 DoneEvent(cancelled=True)
6. THE 执行器 SHALL 使用 FileOpTracker 追踪文件操作并发出 FileOperationEvent

### Requirement 6: 配置管理规范

**User Story:** As a 开发者, I want 统一的配置管理, so that 环境变量和设置能够集中管理。

#### Acceptance Criteria

1. THE Settings 类 SHALL 从环境变量加载 API keys（OPENAI_API_KEY、ANTHROPIC_API_KEY、TAVILY_API_KEY）
2. THE Settings 类 SHALL 提供 create_model(model_name) 方法创建 LLM 实例
3. THE Settings 类 SHALL 提供 ensure_agent_dir(assistant_id) 方法管理 Agent 目录
4. WHEN 环境变量未设置时 THEN Settings SHALL 使用合理的默认值
5. THE SessionState 类 SHALL 管理会话级别的状态（thread_id、auto_approve 等）

### Requirement 7: 中间件规范

**User Story:** As a 开发者, I want 可扩展的中间件系统, so that Agent 功能能够灵活扩展。

#### Acceptance Criteria

1. THE 中间件 SHALL 实现 LangChain AgentMiddleware 协议
2. THE AgentMemoryMiddleware SHALL 提供长期记忆功能，存储和检索历史上下文
3. THE SkillsMiddleware SHALL 加载和注入领域技能到 Agent 上下文
4. THE ShellMiddleware SHALL 提供 Shell 命令执行能力
5. WHEN 添加自定义中间件时 THEN 开发者 SHALL 通过 AgentConfig.extra_middleware 注入

### Requirement 8: 工具系统规范

**User Story:** As a 开发者, I want 统一的工具注册和管理, so that Agent 能够使用各类工具。

#### Acceptance Criteria

1. THE 工具系统 SHALL 提供以下内置工具：http_request、fetch_url、web_search（需要 TAVILY_API_KEY）
2. THE FileOpTracker SHALL 追踪文件操作（read_file、write_file、edit_file）并计算 diff
3. WHEN 添加自定义工具时 THEN 开发者 SHALL 通过 AgentConfig.extra_tools 注入
4. THE 工具 SHALL 继承 LangChain BaseTool 并实现 _run() 或 _arun() 方法
5. THE 工具结果 SHALL 通过 ToolResultEvent 返回，包含 status 字段指示成功或失败

### Requirement 9: 终端渲染规范

**User Story:** As a 开发者, I want 统一的终端渲染器, so that CLI 能够美观地展示 Agent 输出。

#### Acceptance Criteria

1. THE TerminalRenderer SHALL 使用 Rich 库进行终端渲染
2. THE 渲染器 SHALL 为不同事件类型提供对应的渲染方法
3. WHEN 渲染 TextEvent 时 THEN 渲染器 SHALL 使用 Markdown 格式化输出
4. WHEN 渲染 ToolCallEvent 时 THEN 渲染器 SHALL 显示工具图标和简化的参数信息
5. WHEN 渲染 FileOperationEvent 时 THEN 渲染器 SHALL 显示 diff 块和操作统计
6. THE 渲染器 SHALL 在 Agent 思考时显示 spinner 动画

### Requirement 10: 代码风格规范

**User Story:** As a 开发者, I want 统一的代码风格, so that 代码库保持一致性和可读性。

#### Acceptance Criteria

1. THE 代码 SHALL 使用 Python 3.11+ 语法特性（类型注解、dataclass、match 语句等）
2. THE 代码 SHALL 遵循 PEP 8 风格指南，行宽限制为 100 字符
3. THE 公共 API SHALL 包含 docstring 说明参数和返回值
4. THE 类型注解 SHALL 使用 Python 3.10+ 语法（`list[str]` 而非 `List[str]`）
5. WHEN 定义数据类时 THEN 开发者 SHALL 优先使用 dataclass 或 Pydantic BaseModel
6. THE 异步函数 SHALL 使用 async/await 语法，避免回调风格

### Requirement 11: 错误处理规范

**User Story:** As a 开发者, I want 统一的错误处理策略, so that 系统能够优雅地处理异常。

#### Acceptance Criteria

1. THE 执行器 SHALL 捕获所有异常并转换为 ErrorEvent
2. THE ErrorEvent SHALL 包含 error（错误信息）和 recoverable（是否可恢复）字段
3. WHEN 发生可恢复错误时 THEN 系统 SHALL 允许用户重试操作
4. WHEN 发生不可恢复错误时 THEN 系统 SHALL 终止当前执行并通知用户
5. THE 日志 SHALL 使用 Python logging 模块，支持不同级别（DEBUG、INFO、WARNING、ERROR）

### Requirement 12: 测试规范

**User Story:** As a 开发者, I want 完善的测试覆盖, so that 代码质量得到保证。

#### Acceptance Criteria

1. THE 单元测试 SHALL 使用 pytest 框架
2. THE 测试文件 SHALL 放置在 tests/ 目录下，镜像源代码结构
3. WHEN 测试异步代码时 THEN 开发者 SHALL 使用 pytest-asyncio 插件
4. THE 测试 SHALL 使用 mock 隔离外部依赖（LLM API、文件系统等）
5. THE 核心模块 SHALL 达到 80% 以上的测试覆盖率

### Requirement 13: 会话管理规范

**User Story:** As a 开发者, I want 统一的会话管理, so that 用户交互状态能够被正确维护。

#### Acceptance Criteria

1. THE Session 数据类 SHALL 包含 session_id、user_id、assistant_id、created_at、last_active、state、metadata 字段
2. THE SessionStore 抽象类 SHALL 定义 create、get、update、delete、list_by_user 方法
3. THE SessionManager SHALL 提供 get_or_create_session() 和 get_executor() 方法
4. WHEN 会话超时时 THEN 系统 SHALL 自动清理会话资源
5. THE 会话状态 SHALL 支持持久化到内存、Redis 或数据库

### Requirement 14: 序列化规范

**User Story:** As a 开发者, I want 统一的序列化格式, so that 事件和数据能够在不同组件间传输。

#### Acceptance Criteria

1. THE 事件 SHALL 通过 to_dict() 方法序列化为字典
2. THE 序列化结果 SHALL 可直接转换为 JSON 格式
3. WHEN 序列化事件时 THEN 系统 SHALL 包含 event_type 和 timestamp 字段
4. THE WebSocket 消息 SHALL 使用 JSON 格式传输
5. WHEN 反序列化事件时 THEN 系统 SHALL 能够根据 event_type 重建事件对象



### Requirement 15: DataAgentServer 项目结构规范

**User Story:** As a 开发者, I want DataAgentServer 有清晰的项目结构, so that Web 服务代码组织清晰且易于维护。

#### Acceptance Criteria

1. THE DataAgentServer 项目 SHALL 遵循以下目录结构：api/（REST API 路由）、ws/（WebSocket 处理）、hitl/（Web HITL 实现）、models/（Pydantic 模型）、deps/（依赖注入）
2. THE 项目 SHALL 使用 FastAPI 作为 Web 框架
3. THE 项目 SHALL 包含 `pyproject.toml` 定义依赖和元数据
4. THE 项目 SHALL 依赖 dataagent-core 包
5. WHEN 启动服务时 THEN 系统 SHALL 通过 uvicorn 运行 ASGI 应用

### Requirement 16: REST API 规范

**User Story:** As a Web 客户端开发者, I want 标准的 REST API, so that 我可以通过 HTTP 与 Agent 交互。

#### Acceptance Criteria

1. THE API 版本前缀 SHALL 为 `/api/v1`
2. THE API SHALL 提供以下端点：
   - `POST /api/v1/chat` - 发送消息并获取响应（同步）
   - `GET /api/v1/sessions` - 列出用户会话
   - `GET /api/v1/sessions/{session_id}` - 获取会话详情
   - `DELETE /api/v1/sessions/{session_id}` - 删除会话
   - `GET /api/v1/agents` - 列出可用 Agent
   - `GET /api/v1/health` - 健康检查
3. THE API 响应 SHALL 使用 JSON 格式
4. WHEN 请求失败时 THEN API SHALL 返回标准错误响应包含 error_code 和 message 字段
5. THE API SHALL 支持 CORS 配置

### Requirement 17: WebSocket 规范

**User Story:** As a Web 客户端开发者, I want WebSocket 实时通信, so that 我可以接收 Agent 的流式响应。

#### Acceptance Criteria

1. THE WebSocket 端点 SHALL 为 `/ws/chat/{session_id}`
2. WHEN 客户端连接时 THEN 服务器 SHALL 验证 session_id 有效性
3. THE 客户端消息格式 SHALL 为 JSON 包含 type 和 payload 字段
4. THE 服务器消息格式 SHALL 为 JSON 包含 event_type 和事件数据
5. WHEN Agent 产生事件时 THEN 服务器 SHALL 实时推送事件到客户端
6. WHEN 连接断开时 THEN 服务器 SHALL 清理相关资源
7. THE WebSocket SHALL 支持心跳机制保持连接活跃

### Requirement 18: Web HITL 规范

**User Story:** As a Web 用户, I want 在浏览器中审批敏感操作, so that 我可以控制 Agent 的行为。

#### Acceptance Criteria

1. THE WebHITLHandler SHALL 实现 HITLHandler 协议
2. WHEN 需要用户审批时 THEN 服务器 SHALL 通过 WebSocket 发送 HITLRequestEvent
3. THE 客户端 SHALL 通过 WebSocket 发送审批决定（approve/reject）
4. WHEN 等待用户审批时 THEN 服务器 SHALL 设置超时时间（默认 300 秒）
5. WHEN 审批超时时 THEN 系统 SHALL 自动拒绝操作

### Requirement 19: 认证和授权规范

**User Story:** As a 系统管理员, I want API 认证机制, so that 只有授权用户可以访问服务。

#### Acceptance Criteria

1. THE API SHALL 支持 API Key 认证方式
2. THE API Key SHALL 通过 HTTP Header `X-API-Key` 传递
3. WHEN 请求未携带有效 API Key 时 THEN API SHALL 返回 401 Unauthorized
4. THE 系统 SHALL 支持配置多个 API Key
5. WHEN 配置 `DATAAGENT_AUTH_DISABLED=true` 时 THEN 系统 SHALL 跳过认证检查

### Requirement 20: 服务配置规范

**User Story:** As a 运维人员, I want 灵活的服务配置, so that 我可以根据环境调整服务行为。

#### Acceptance Criteria

1. THE 服务 SHALL 从环境变量加载配置
2. THE 配置项 SHALL 包含：
   - `DATAAGENT_HOST` - 监听地址（默认 0.0.0.0）
   - `DATAAGENT_PORT` - 监听端口（默认 8000）
   - `DATAAGENT_WORKERS` - 工作进程数（默认 1）
   - `DATAAGENT_API_KEYS` - API Key 列表（逗号分隔）
   - `DATAAGENT_CORS_ORIGINS` - CORS 允许的源（逗号分隔）
   - `DATAAGENT_SESSION_TIMEOUT` - 会话超时秒数（默认 3600）
3. THE 服务 SHALL 支持通过命令行参数覆盖配置
4. WHEN 必需配置缺失时 THEN 服务 SHALL 使用合理的默认值

### Requirement 21: API 数据模型规范

**User Story:** As a 开发者, I want 清晰的 API 数据模型, so that 请求和响应格式明确。

#### Acceptance Criteria

1. THE 请求/响应模型 SHALL 使用 Pydantic BaseModel 定义
2. THE ChatRequest 模型 SHALL 包含 message、session_id（可选）、assistant_id（可选）字段
3. THE ChatResponse 模型 SHALL 包含 session_id、events 字段
4. THE SessionInfo 模型 SHALL 包含 session_id、user_id、assistant_id、created_at、last_active 字段
5. THE ErrorResponse 模型 SHALL 包含 error_code、message、details（可选）字段
6. THE WebSocketMessage 模型 SHALL 包含 type、payload 字段

### Requirement 22: 日志和监控规范

**User Story:** As a 运维人员, I want 完善的日志和监控, so that 我可以追踪服务状态和问题。

#### Acceptance Criteria

1. THE 服务 SHALL 使用结构化日志格式（JSON）
2. THE 日志 SHALL 包含 timestamp、level、message、request_id 字段
3. THE 服务 SHALL 在 `/api/v1/health` 端点提供健康检查
4. THE 健康检查响应 SHALL 包含 status、version、uptime 字段
5. WHEN 请求处理时 THEN 系统 SHALL 记录请求 ID 用于追踪

### Requirement 23: 高并发性能规范

**User Story:** As a 系统管理员, I want 服务支持高并发访问, so that 多个用户可以同时使用系统。

#### Acceptance Criteria

1. THE 服务 SHALL 支持至少 100 个用户同时进行问答交互
2. THE WebSocket 连接管理器 SHALL 使用异步非阻塞设计处理并发连接
3. THE 服务 SHALL 支持配置工作进程数（workers）以利用多核 CPU
4. WHEN 单个用户请求处理时 THEN 系统 SHALL 不阻塞其他用户的请求
5. THE 会话管理 SHALL 使用线程安全的数据结构存储连接状态
6. WHEN 系统负载过高时 THEN 服务 SHALL 返回 503 Service Unavailable 并提示稍后重试

### Requirement 24: 问答终止规范

**User Story:** As a 用户, I want 能够随时终止正在进行的问答, so that 我可以取消不需要的请求。

#### Acceptance Criteria

1. THE WebSocket 协议 SHALL 支持 cancel 消息类型用于终止当前问答
2. WHEN 用户发送 cancel 消息时 THEN 服务器 SHALL 立即停止当前 Agent 执行
3. WHEN 问答被终止时 THEN 服务器 SHALL 发送 DoneEvent(cancelled=True) 通知客户端
4. THE REST API SHALL 提供 POST /api/v1/chat/{session_id}/cancel 端点用于终止问答
5. WHEN 终止请求到达时 THEN 系统 SHALL 在 1 秒内响应终止操作
6. WHEN 问答被终止时 THEN 系统 SHALL 清理相关资源并释放内存

### Requirement 25: 数据库会话存储规范

**User Story:** As a 系统管理员, I want 会话数据持久化存储到数据库, so that 服务重启后会话和历史记录不会丢失。

#### Acceptance Criteria

1. THE DataAgentServer SHALL 支持 MySQL 数据库作为会话存储后端
2. THE 系统 SHALL 支持通过环境变量 DATAAGENT_SESSION_STORE 配置存储类型（memory/mysql）
3. WHEN 配置为 mysql 时 THEN 系统 SHALL 从环境变量加载数据库连接配置（DATAAGENT_MYSQL_HOST, DATAAGENT_MYSQL_PORT, DATAAGENT_MYSQL_USER, DATAAGENT_MYSQL_PASSWORD, DATAAGENT_MYSQL_DATABASE）
4. THE MySQLSessionStore SHALL 实现 SessionStore 抽象类的所有方法（create, get, update, delete, list_by_user, list_by_assistant, cleanup_expired）
5. THE 数据库表 SHALL 包含 sessions 表存储会话元数据
6. THE 数据库表 SHALL 包含 messages 表存储用户问答历史记录
7. WHEN 服务启动时 THEN 系统 SHALL 自动创建所需的数据库表（如果不存在）
8. THE 数据库操作 SHALL 使用连接池管理连接，支持高并发访问

### Requirement 26: 问答历史记录规范

**User Story:** As a 用户, I want 查看历史问答记录, so that 我可以回顾之前的对话内容。

#### Acceptance Criteria

1. THE 系统 SHALL 在每次问答完成后保存用户消息和 Agent 响应到数据库
2. THE messages 表 SHALL 包含 message_id, session_id, role（user/assistant）, content, created_at 字段
3. THE REST API SHALL 提供 GET /api/v1/sessions/{session_id}/messages 端点获取会话历史消息
4. WHEN 查询历史消息时 THEN 系统 SHALL 支持分页参数（limit, offset）
5. THE 历史消息 SHALL 按时间顺序排列（最早的在前）


### Requirement 27: DataAgentHarbor 测试框架规范

**User Story:** As a 测试工程师, I want 一个批量压测框架, so that 我可以评估 DataAgent Server 的性能和正确性。

#### Acceptance Criteria

1. THE DataAgentHarbor 项目 SHALL 支持从 JSON 文件加载测试问题集
2. THE 测试问题集 SHALL 包含 question、expected_keywords、expected_pattern、category、difficulty 字段
3. WHEN 执行压测时 THEN 系统 SHALL 支持配置并发数进行并行测试
4. THE 系统 SHALL 收集每个测试的结果包括：状态（passed/failed/error/timeout）、响应时间、匹配的关键词
5. WHEN 测试完成时 THEN 系统 SHALL 生成统计报告包含成功率、平均响应时间、失败案例列表
6. THE 系统 SHALL 支持通过 REST API 和 WebSocket 两种方式与 DataAgent Server 交互

### Requirement 28: LangSmith 追踪集成规范

**User Story:** As a 开发者, I want 集成 LangSmith 追踪, so that 我可以分析和调试 Agent 执行过程。

#### Acceptance Criteria

1. THE 系统 SHALL 支持通过环境变量启用 LangSmith 追踪（LANGSMITH_API_KEY, LANGSMITH_TRACING_V2）
2. WHEN 追踪启用时 THEN 系统 SHALL 为每个测试请求创建追踪记录
3. THE 系统 SHALL 支持创建 LangSmith 数据集用于存储测试问题
4. WHEN 测试完成时 THEN 系统 SHALL 支持将测试结果作为反馈添加到 LangSmith
5. THE 追踪记录 SHALL 包含 question_id、category、response_time 等元数据

---

## Phase 8: MCP Server 配置与多租户支持

### Requirement 29: CLI 模式 MCP Server 配置规范

**User Story:** As a 数据开发工程师, I want 在 CLI 模式下配置 MCP Server, so that 我可以扩展 Agent 的工具能力。

#### Acceptance Criteria

1. THE DataAgentCli SHALL 支持通过配置文件 `~/.deepagents/{assistant_id}/mcp.json` 配置 MCP Server
2. THE MCP 配置文件 SHALL 支持以下字段：servers（服务器列表）、每个服务器包含 name、command、args、env、disabled
3. WHEN CLI 启动时 THEN 系统 SHALL 自动加载并连接配置的 MCP Server
4. THE 系统 SHALL 使用 langchain-mcp-adapters 库连接 MCP Server
5. WHEN MCP Server 连接失败时 THEN 系统 SHALL 记录警告日志并继续运行（不阻塞主流程）
6. THE CLI SHALL 提供 `--mcp-config` 参数允许指定自定义配置文件路径
7. THE 系统 SHALL 支持在运行时动态重载 MCP 配置（通过特殊命令 `/mcp reload`）

### Requirement 30: Server 模式动态 MCP Server 配置规范

**User Story:** As a 系统管理员, I want 在 Server 模式下为每个用户动态配置 MCP Server, so that 不同用户可以使用不同的工具集。

#### Acceptance Criteria

1. THE DataAgentServer SHALL 支持通过 REST API 管理用户的 MCP Server 配置
2. THE API SHALL 提供以下端点：
   - `GET /api/v1/users/{user_id}/mcp-servers` - 列出用户的 MCP Server 配置
   - `POST /api/v1/users/{user_id}/mcp-servers` - 添加 MCP Server 配置
   - `PUT /api/v1/users/{user_id}/mcp-servers/{server_name}` - 更新 MCP Server 配置
   - `DELETE /api/v1/users/{user_id}/mcp-servers/{server_name}` - 删除 MCP Server 配置
3. THE MCP Server 配置 SHALL 支持持久化存储（MySQL 或配置文件）
4. WHEN 用户发起聊天请求时 THEN 系统 SHALL 加载该用户的 MCP Server 配置并创建对应的工具
5. THE 系统 SHALL 支持全局默认 MCP Server 配置，用户配置可覆盖或扩展全局配置
6. WHEN MCP Server 配置变更时 THEN 系统 SHALL 在下次会话创建时生效（不影响进行中的会话）
7. THE 系统 SHALL 支持 MCP Server 配置的热更新（通过 WebSocket 消息通知客户端）

### Requirement 31: MCP Server 连接池管理规范

**User Story:** As a 系统管理员, I want MCP Server 连接被高效管理, so that 系统资源得到合理利用。

#### Acceptance Criteria

1. THE 系统 SHALL 为每个用户维护独立的 MCP Server 连接池
2. THE 连接池 SHALL 支持配置最大连接数（默认每用户 5 个 MCP Server）
3. WHEN 用户会话结束时 THEN 系统 SHALL 释放该用户的 MCP Server 连接
4. THE 系统 SHALL 支持 MCP Server 连接的健康检查和自动重连
5. WHEN MCP Server 连接超时时 THEN 系统 SHALL 自动断开并记录日志
6. THE 系统 SHALL 支持配置 MCP Server 连接超时时间（默认 30 秒）

### Requirement 32: 多租户用户隔离规范

**User Story:** As a 企业管理员, I want 不同用户的数据完全隔离, so that 用户隐私和数据安全得到保障。

#### Acceptance Criteria

1. THE 系统 SHALL 为每个用户维护独立的会话空间（session isolation）
2. THE 系统 SHALL 为每个用户维护独立的记忆存储（memory isolation）
3. THE 系统 SHALL 为每个用户维护独立的历史记录（history isolation）
4. THE 系统 SHALL 为每个用户维护独立的文件工作区（workspace isolation）
5. WHEN 用户 A 查询会话时 THEN 系统 SHALL 只返回用户 A 的会话，不返回其他用户的会话
6. WHEN 用户 A 使用文件操作工具时 THEN 系统 SHALL 限制操作范围在用户 A 的工作区内
7. THE 系统 SHALL 支持配置用户工作区根目录（默认 `/data/workspaces/{user_id}`）

### Requirement 33: 用户工作区管理规范

**User Story:** As a 用户, I want 拥有独立的文件工作区, so that 我的文件不会与其他用户混淆。

#### Acceptance Criteria

1. THE 系统 SHALL 在用户首次登录时自动创建用户工作区目录
2. THE 用户工作区 SHALL 包含以下子目录：files/（用户文件）、uploads/（上传文件）、outputs/（输出文件）
3. THE Agent 文件操作工具 SHALL 被限制在用户工作区范围内（路径沙箱）
4. WHEN 用户尝试访问工作区外的文件时 THEN 系统 SHALL 拒绝操作并返回权限错误
5. THE 系统 SHALL 支持配置用户工作区配额（默认 1GB）
6. WHEN 用户工作区超出配额时 THEN 系统 SHALL 拒绝新的写入操作并通知用户
7. THE 系统 SHALL 支持用户工作区的清理策略（如 30 天未访问自动归档）

### Requirement 34: 用户记忆隔离规范

**User Story:** As a 用户, I want Agent 只记住我的对话历史, so that 我的隐私得到保护。

#### Acceptance Criteria

1. THE AgentMemoryMiddleware SHALL 支持按用户隔离记忆存储
2. THE 记忆存储路径 SHALL 为 `{storage_root}/memories/{user_id}/{assistant_id}/`
3. WHEN 加载记忆时 THEN 系统 SHALL 只加载当前用户的记忆数据
4. THE 系统 SHALL 支持用户主动清除自己的记忆数据（通过 API 或命令）
5. THE 系统 SHALL 支持配置记忆数据的保留期限（默认 90 天）

### Requirement 35: 租户配置管理规范

**User Story:** As a 企业管理员, I want 为不同租户配置不同的系统参数, so that 满足不同客户的需求。

#### Acceptance Criteria

1. THE 系统 SHALL 支持多租户模式（通过环境变量 DATAAGENT_MULTI_TENANT=true 启用）
2. THE 租户配置 SHALL 包含：tenant_id、name、max_users、max_sessions_per_user、max_mcp_servers、workspace_quota、features_enabled
3. THE 系统 SHALL 支持通过 REST API 管理租户配置（仅管理员）
4. WHEN 用户请求超出租户配额时 THEN 系统 SHALL 返回 429 Too Many Requests
5. THE 系统 SHALL 支持租户级别的功能开关（如禁用某些工具或 MCP Server）

### Requirement 36: Demo 界面 MCP 配置规范

**User Story:** As a 演示用户, I want 在 Demo 界面配置 MCP Server, so that 我可以测试和体验 MCP 工具扩展功能。

#### Acceptance Criteria

1. THE DataAgentServerDemo SHALL 提供 MCP 配置标签页，与对话标签页并列显示
2. THE MCP 配置界面 SHALL 显示当前用户已配置的 MCP Server 列表
3. THE MCP 配置界面 SHALL 提供添加新 MCP Server 的表单，包含名称、命令、参数、环境变量字段
4. THE MCP 配置界面 SHALL 支持删除已配置的 MCP Server
5. THE MCP 配置界面 SHALL 显示每个 MCP Server 的连接状态（connected/disconnected/error）
6. THE MCP 配置界面 SHALL 提供配置示例帮助用户理解配置格式
7. WHEN MCP API 未实现时 THEN 界面 SHALL 显示友好的提示信息而非错误
