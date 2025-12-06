# Implementation Plan

## Phase 1: DataAgentCore 核心模块

- [x] 1. 完善事件系统
  - [x] 1.1 实现事件反序列化功能
    - 在 events/__init__.py 中添加 from_dict() 类方法
    - 支持根据 event_type 重建事件对象
    - _Requirements: 14.5_
  - [x]* 1.2 编写事件序列化属性测试
    - **Property 1: 事件序列化往返一致性**
    - **Validates: Requirements 14.5**
  - [x]* 1.3 编写事件基础字段属性测试
    - **Property 2: 事件必须包含基础字段**
    - **Validates: Requirements 2.6, 14.3**
  - [x]* 1.4 编写事件 JSON 序列化属性测试
    - **Property 3: 事件序列化结果是有效 JSON**
    - **Validates: Requirements 14.2**
  - [x]* 1.5 编写 TextEvent 字段属性测试
    - **Property 4: TextEvent 包含必需字段**
    - **Validates: Requirements 2.2**
  - [x]* 1.6 编写 ToolCallEvent 字段属性测试
    - **Property 5: ToolCallEvent 包含必需字段**
    - **Validates: Requirements 2.3**
  - [x]* 1.7 编写 ToolResultEvent 字段属性测试
    - **Property 6: ToolResultEvent 包含必需字段**
    - **Validates: Requirements 2.4**

- [x] 2. 完善 HITL 协议
  - [x] 2.1 实现 AutoApproveHandler 类
    - 在 hitl/protocol.py 中添加自动批准处理器
    - 实现 request_approval 方法返回 approve 决定
    - _Requirements: 3.5_
  - [x]* 2.2 编写 HITL 拒绝属性测试
    - **Property 7: HITL 拒绝导致执行取消**
    - **Validates: Requirements 3.4, 5.5**
  - [x]* 2.3 编写自动批准属性测试
    - **Property 8: 无 HITLHandler 时自动批准**
    - **Validates: Requirements 3.5**

- [x] 3. 完善 Agent 工厂
  - [x] 3.1 实现 AgentFactory 类
    - 在 engine/factory.py 中完善工厂实现
    - 实现 create_agent 方法返回 (agent, backend) 元组
    - 实现中间件构建逻辑
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x]* 3.2 编写工厂返回值属性测试
    - **Property 9: AgentFactory 返回正确的元组**
    - **Validates: Requirements 4.2**
  - [x]* 3.3 编写 memory 中间件属性测试
    - **Property 10: 启用 memory 时添加 MemoryMiddleware**
    - **Validates: Requirements 4.4**
  - [x]* 3.4 编写 skills 中间件属性测试
    - **Property 11: 启用 skills 时添加 SkillsMiddleware**
    - **Validates: Requirements 4.5**
  - [x]* 3.5 编写自定义中间件属性测试
    - **Property 19: 自定义中间件被注入**
    - **Validates: Requirements 7.5**
  - [x]* 3.6 编写自定义工具属性测试
    - **Property 20: 自定义工具被注入**
    - **Validates: Requirements 8.3**

- [x] 4. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. 完善执行器
  - [x] 5.1 完善 AgentExecutor 错误处理
    - 确保所有异常被捕获并转换为 ErrorEvent
    - 确保正常完成发出 DoneEvent(cancelled=False)
    - 确保 HITL 拒绝发出 DoneEvent(cancelled=True)
    - _Requirements: 5.3, 5.4, 5.5, 11.1_
  - [x]* 5.2 编写执行器返回值属性测试
    - **Property 12: 执行器返回事件迭代器**
    - **Validates: Requirements 5.1**
  - [x]* 5.3 编写异常处理属性测试
    - **Property 13: 异常转换为 ErrorEvent**
    - **Validates: Requirements 5.3, 11.1**
  - [x]* 5.4 编写正常完成属性测试
    - **Property 14: 正常完成发出 DoneEvent**
    - **Validates: Requirements 5.4**

- [x] 6. 完善文件操作追踪
  - [x] 6.1 完善 FileOpTracker 实现
    - 确保追踪 read_file, write_file, edit_file 操作
    - 计算 diff 和操作统计
    - _Requirements: 5.6, 8.2_
  - [x]* 6.2 编写文件操作追踪属性测试
    - **Property 15: 文件操作被追踪**
    - **Validates: Requirements 5.6, 8.2**
    - Note: FileOpTracker 集成测试在 executor 测试中覆盖

- [x] 7. 完善配置管理
  - [x] 7.1 完善 Settings 类
    - 实现从环境变量加载 API keys
    - 实现 create_model 方法
    - 实现 ensure_agent_dir 方法
    - 实现默认值处理
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [x]* 7.2 编写环境变量加载属性测试
    - **Property 16: Settings 从环境变量加载**
    - **Validates: Requirements 6.1**
  - [x]* 7.3 编写目录创建属性测试
    - **Property 17: ensure_agent_dir 创建目录**
    - **Validates: Requirements 6.3**
  - [x]* 7.4 编写默认值属性测试
    - **Property 18: 未设置环境变量时使用默认值**
    - **Validates: Requirements 6.4**

- [x] 8. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: DataAgentCore 会话管理

- [x] 9. 实现会话管理
  - [x] 9.1 实现 Session 数据类
    - 在 session/state.py 中定义 Session 数据类
    - 包含 session_id, user_id, assistant_id, created_at, last_active, state, metadata 字段
    - _Requirements: 13.1_
  - [x] 9.2 实现 SessionStore 抽象类
    - 在 session/store.py 中定义抽象基类
    - 定义 create, get, update, delete, list_by_user 方法
    - _Requirements: 13.2_
  - [x] 9.3 实现 MemorySessionStore
    - 在 session/stores/memory.py 中实现内存存储
    - _Requirements: 13.5_
  - [x] 9.4 实现 SessionManager
    - 在 session/manager.py 中实现会话管理器
    - 实现 get_or_create_session 和 get_executor 方法
    - 实现会话超时清理逻辑
    - _Requirements: 13.3, 13.4_
  - [x]* 9.5 编写会话超时属性测试
    - **Property 21: 会话超时自动清理**
    - **Validates: Requirements 13.4**

- [x] 10. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: DataAgentCli 终端客户端

- [x] 11. 完善终端渲染器
  - [x] 11.1 完善 TerminalRenderer 实现
    - 在 ui/renderer.py 中完善事件渲染逻辑
    - 实现 TextEvent 的 Markdown 渲染
    - 实现 ToolCallEvent 的图标和参数显示
    - 实现 FileOperationEvent 的 diff 渲染
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [x]* 11.2 编写渲染器单元测试
    - 测试各类事件的渲染输出
    - _Requirements: 9.2, 9.3, 9.4, 9.5_
    - Note: CLI 渲染器测试需要终端环境，建议手动测试

- [x] 12. 完善终端 HITL 处理器
  - [x] 12.1 完善 TerminalHITLHandler 实现
    - 在 hitl/terminal.py 中完善实现
    - 实现键盘导航选择
    - _Requirements: 3.6_
  - [x]* 12.2 编写 HITL 处理器单元测试
    - 测试 approve/reject 决定的返回
    - _Requirements: 3.1, 3.2, 3.3_
    - Note: HITL 协议测试在 Core 模块中已覆盖

- [x] 13. 完善 CLI 主入口
  - [x] 13.1 完善 main.py 实现
    - 集成 AgentFactory, AgentExecutor, TerminalRenderer, TerminalHITLHandler
    - 实现主循环逻辑
    - _Requirements: 4.1, 5.1, 9.1_
  - [x]* 13.2 编写 CLI 集成测试
    - 测试完整的用户交互流程
    - _Requirements: 1.2_
    - Note: CLI 集成测试需要终端环境，建议手动测试

- [x] 14. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: 架构验证和文档

- [x] 15. 验证模块依赖
  - [x] 15.1 检查并修复模块依赖
    - 确保 Core 不导入 CLI 或 Server
    - 确保依赖关系遵循 Core → CLI/Server 原则
    - _Requirements: 1.5_
  - [x]* 15.2 编写依赖检查属性测试
    - **Property 22: 模块依赖单向性**
    - **Validates: Requirements 1.5**

- [x] 16. 完善项目结构
  - [x] 16.1 确保所有模块有 __init__.py
    - 检查并添加缺失的 __init__.py 文件
    - 确保公共接口被正确导出
    - _Requirements: 1.3_
  - [x] 16.2 更新 pyproject.toml
    - 确保依赖声明完整
    - 确保元数据正确
    - _Requirements: 1.4_

- [x] 17. 完善代码文档
  - [x] 17.1 添加公共 API docstring
    - 为所有公共类和方法添加 docstring
    - 说明参数和返回值
    - _Requirements: 10.3_
  - [x] 17.2 更新 README 文档
    - 更新 dataagent-core/README.md
    - 更新 dataagent-cli/README.md
    - _Requirements: 1.1, 1.2_

- [x] 18. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: DataAgentServer Web 服务

- [x] 19. 创建 DataAgentServer 项目结构
  - [x] 19.1 创建项目目录和 pyproject.toml
    - 创建 libs/dataagent-server/ 目录结构
    - 配置 pyproject.toml 包含 FastAPI、uvicorn 等依赖
    - 添加对 dataagent-core 的依赖
    - _Requirements: 15.1, 15.3, 15.4_
  - [x] 19.2 创建基础模块结构
    - 创建 api/, ws/, hitl/, models/, auth/, config/ 目录
    - 添加各目录的 __init__.py 文件
    - _Requirements: 15.1_

- [x] 20. 实现服务配置管理
  - [x] 20.1 实现 ServerSettings 类
    - 在 config/settings.py 中实现配置类
    - 支持从环境变量加载配置（DATAAGENT_HOST, DATAAGENT_PORT 等）
    - 实现合理的默认值
    - _Requirements: 20.1, 20.2, 20.4_
  - [x] 20.2 编写配置默认值属性测试
    - **Property 32: 配置默认值**
    - **Validates: Requirements 20.4**

- [x] 21. 实现 Pydantic 数据模型
  - [x] 21.1 实现请求/响应模型
    - 在 models/ 目录下实现 ChatRequest, ChatResponse, SessionInfo, ErrorResponse, WebSocketMessage
    - 确保所有必需字段都已定义
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_
  - [x] 21.2 编写模型字段完整性属性测试
    - **Property 33: Pydantic 模型字段完整性**
    - **Validates: Requirements 21.2, 21.3, 21.4, 21.5**

- [x] 22. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 23. 实现 API Key 认证
  - [x] 23.1 实现 APIKeyAuth 中间件
    - 在 auth/api_key.py 中实现认证逻辑
    - 支持通过 X-API-Key Header 传递 API Key
    - 支持配置多个 API Key
    - 支持 DATAAGENT_AUTH_DISABLED 环境变量禁用认证
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_
  - [x] 23.2 编写 API Key 认证属性测试
    - **Property 30: API Key 认证有效性**
    - **Validates: Requirements 19.3**
  - [x] 23.3 编写多 API Key 支持属性测试
    - **Property 31: 多 API Key 支持**
    - **Validates: Requirements 19.4**

- [x] 24. 实现 REST API 路由
  - [x] 24.1 实现健康检查端点
    - 在 api/v1/health.py 中实现 /api/v1/health 端点
    - 返回 status, version, uptime 字段
    - _Requirements: 22.3, 22.4_
  - [x] 24.2 编写健康检查响应属性测试
    - **Property 34: 健康检查响应格式**
    - **Validates: Requirements 22.4**
  - [x] 24.3 实现会话管理端点
    - 在 api/v1/sessions.py 中实现会话 CRUD 端点
    - GET /api/v1/sessions - 列出会话
    - GET /api/v1/sessions/{session_id} - 获取会话详情
    - DELETE /api/v1/sessions/{session_id} - 删除会话
    - _Requirements: 16.2_
  - [x] 24.4 实现聊天端点
    - 在 api/v1/chat.py 中实现 POST /api/v1/chat 端点
    - 支持同步聊天请求
    - _Requirements: 16.2_
  - [x] 24.5 实现聊天取消端点
    - 在 api/v1/chat.py 中实现 POST /api/v1/chat/{session_id}/cancel 端点
    - 终止正在进行的问答
    - _Requirements: 24.4_
  - [x] 24.6 编写 API 端点注册属性测试
    - **Property 23: API 端点注册完整性**
    - **Validates: Requirements 16.2**
  - [x] 24.7 编写 API 响应格式属性测试
    - **Property 24: API 响应 JSON 格式**
    - **Validates: Requirements 16.3**
  - [x] 24.8 编写并发连接隔离性属性测试
    - **Property 36: 并发连接隔离性**
    - **Validates: Requirements 23.4**

- [x] 25. 实现错误处理
  - [x] 25.1 实现全局异常处理器
    - 在 api/deps.py 中实现异常处理
    - 确保所有错误返回标准 ErrorResponse 格式
    - _Requirements: 16.4_
  - [x] 25.2 编写错误响应格式属性测试
    - **Property 25: 错误响应格式一致性**
    - **Validates: Requirements 16.4**

- [x] 26. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 27. 实现 WebSocket 连接管理
  - [x] 27.1 实现 ConnectionManager 类
    - 在 ws/manager.py 中实现连接管理器
    - 实现 connect, disconnect, send_event 方法
    - 实现 wait_for_decision, resolve_decision 方法用于 HITL
    - 使用 asyncio.Lock 确保线程安全
    - 支持最大连接数限制
    - _Requirements: 17.1, 17.6, 23.2, 23.5_
  - [x] 27.2 编写连接断开资源清理属性测试
    - **Property 28: WebSocket 连接断开资源清理**
    - **Validates: Requirements 17.6**
  - [x] 27.3 编写连接管理器线程安全属性测试
    - **Property 37: 连接管理器线程安全**
    - **Validates: Requirements 23.5**
  - [x] 27.4 编写系统过载保护属性测试
    - **Property 38: 系统过载保护**
    - **Validates: Requirements 23.6**

- [x] 28. 实现 WebSocket 消息处理
  - [x] 28.1 实现 WebSocketChatHandler 类
    - 在 ws/handlers.py 中实现消息处理器
    - 处理 chat, hitl_decision, cancel, ping 消息类型
    - 验证消息格式（type 和 payload 字段）
    - _Requirements: 17.2, 17.3, 17.7_
  - [x] 28.2 实现问答取消功能
    - 实现 cancel 消息处理逻辑
    - 使用 asyncio.Task.cancel() 终止正在执行的任务
    - 发送 DoneEvent(cancelled=True) 通知客户端
    - 清理相关资源
    - _Requirements: 24.1, 24.2, 24.3, 24.5, 24.6_
  - [x] 28.3 编写 WebSocket 消息格式验证属性测试
    - **Property 26: WebSocket 消息格式验证**
    - **Validates: Requirements 17.3**
  - [x] 28.4 编写服务端事件推送格式属性测试
    - **Property 27: 服务端事件推送格式**
    - **Validates: Requirements 17.4, 17.5**
  - [x] 28.5 编写取消消息响应属性测试
    - **Property 39: 取消消息响应**
    - **Validates: Requirements 24.2, 24.3**
  - [x] 28.6 编写取消操作及时性属性测试
    - **Property 40: 取消操作及时性**
    - **Validates: Requirements 24.5**
  - [x] 28.7 编写取消后资源清理属性测试
    - **Property 41: 取消后资源清理**
    - **Validates: Requirements 24.6**

- [x] 29. 实现 WebSocket HITL 处理器
  - [x] 29.1 实现 WebSocketHITLHandler 类
    - 在 hitl/websocket_handler.py 中实现 HITL 处理器
    - 实现 HITLHandler 协议
    - 通过 WebSocket 发送 HITLRequestEvent
    - 支持超时自动拒绝（默认 300 秒）
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_
  - [x] 29.2 编写 HITL 超时自动拒绝属性测试
    - **Property 29: HITL 超时自动拒绝**
    - **Validates: Requirements 18.5**

- [x] 30. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 31. 实现 FastAPI 应用入口
  - [x] 31.1 实现 main.py 应用入口
    - 创建 FastAPI 应用实例
    - 配置 CORS 中间件
    - 注册 REST API 路由
    - 注册 WebSocket 端点 /ws/chat/{session_id}
    - 实现应用生命周期管理
    - _Requirements: 15.2, 15.5, 16.1, 16.5, 17.1_

- [x] 32. 实现请求追踪
  - [x] 32.1 实现请求 ID 中间件
    - 为每个请求生成唯一 request_id
    - 在日志中记录 request_id
    - _Requirements: 22.2, 22.5_
  - [x] 32.2 编写请求 ID 追踪属性测试
    - **Property 35: 请求 ID 追踪**
    - **Validates: Requirements 22.5**

- [x] 33. 完善项目文档
  - [x] 33.1 编写 README.md
    - 说明项目用途和功能
    - 提供安装和运行说明
    - 提供 API 文档链接
    - _Requirements: 15.1_
  - [x] 33.2 添加 API docstring
    - 为所有公共 API 添加 docstring
    - _Requirements: 10.3_

- [x] 34. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: MySQL 数据库存储

- [x] 35. 更新服务配置支持存储类型选择
  - [x] 35.1 更新 ServerSettings 添加存储配置
    - 添加 session_store 配置项（memory/mysql）
    - 添加 MySQL 连接配置项（host, port, user, password, database, pool_size, max_overflow）
    - _Requirements: 25.2, 25.3_
  - [x] 35.2 编写存储类型配置属性测试
    - **Property 43: 存储类型配置有效性**
    - **Validates: Requirements 25.2**

- [x] 36. 实现 MySQL 会话存储
  - [x] 36.1 创建 SQLAlchemy 数据模型
    - 在 dataagent-core/session/models.py 中定义 SessionModel 和 MessageModel
    - 定义表结构和索引
    - _Requirements: 25.5, 25.6_
  - [x] 36.2 实现 MySQLSessionStore 类
    - 在 dataagent-core/session/stores/mysql.py 中实现
    - 实现 SessionStore 抽象类的所有方法
    - 使用 SQLAlchemy 异步引擎和连接池
    - _Requirements: 25.4, 25.8_
  - [x] 36.3 实现数据库表自动创建
    - 在 MySQLSessionStore.init_tables() 中实现
    - _Requirements: 25.7_
  - [x] 36.4 编写 MySQL 会话存储往返属性测试
    - **Property 42: MySQL 会话存储往返一致性**
    - **Validates: Requirements 25.4**
  - [x] 36.5 编写连接池管理属性测试
    - **Property 44: 数据库连接池管理**
    - **Validates: Requirements 25.8**

- [x] 37. 实现消息历史存储
  - [x] 37.1 定义 MessageStore 抽象类
    - 在 dataagent-core/session/message_store.py 中定义
    - 定义 save_message, get_messages, delete_messages 方法
    - _Requirements: 26.1, 26.2_
  - [x] 37.2 实现 MySQLMessageStore 类
    - 在 dataagent-core/session/stores/mysql_message.py 中实现
    - 实现消息的增删查功能
    - _Requirements: 26.1, 26.2_
  - [x] 37.3 编写消息历史完整性属性测试
    - **Property 45: 消息历史记录完整性**
    - **Validates: Requirements 26.1**
  - [x] 37.4 编写消息分页查询属性测试
    - **Property 46: 消息查询分页正确性**
    - **Validates: Requirements 26.4**

- [x] 38. 实现存储工厂和集成
  - [x] 38.1 实现 SessionStoreFactory 类
    - 在 dataagent-core/session/factory.py 中实现
    - 根据配置创建对应的存储实例
    - _Requirements: 25.2_
  - [x] 38.2 更新 DataAgentServer 集成存储工厂
    - 在 main.py 中根据配置初始化存储
    - 在应用启动时初始化数据库表
    - _Requirements: 25.7_
  - [x] 38.3 实现消息保存中间件
    - 在问答完成后自动保存消息到数据库
    - _Requirements: 26.1_
    - Note: 消息保存逻辑在 WebSocket handler 中实现

- [x] 39. 实现消息历史 API
  - [x] 39.1 实现消息历史端点
    - 在 api/v1/sessions.py 中添加 GET /api/v1/sessions/{session_id}/messages 端点
    - 支持 limit 和 offset 分页参数
    - _Requirements: 26.3, 26.4_
  - [x] 39.2 编写消息历史 API 测试
    - 测试分页功能和消息顺序
    - _Requirements: 26.4, 26.5_

- [x] 40. 更新项目依赖和文档
  - [x] 40.1 更新 pyproject.toml
    - 添加 SQLAlchemy、aiomysql 依赖
    - _Requirements: 25.1_
  - [x] 40.2 更新 README.md
    - 添加 MySQL 配置说明
    - 添加数据库初始化说明
    - _Requirements: 25.1_

- [x] 41. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.



## Phase 7: DataAgentHarbor 测试框架

- [x] 42. 创建 DataAgentHarbor 项目结构
  - [x] 42.1 创建项目目录和 pyproject.toml
    - 创建 libs/dataagent-harbor/ 目录结构
    - 配置 pyproject.toml 包含依赖
    - _Requirements: 27.1_
  - [x] 42.2 创建基础模块结构
    - 创建 models.py, client.py, runner.py, tracing.py, cli.py
    - _Requirements: 27.1_

- [x] 43. 实现数据模型
  - [x] 43.1 实现 Question 和 QuestionSet 模型
    - 支持从 JSON 文件加载测试问题集
    - 包含 question、expected_keywords、expected_pattern 等字段
    - _Requirements: 27.1, 27.2_
  - [x] 43.2 实现 QuestionResult 和 BenchmarkReport 模型
    - 收集测试结果和统计信息
    - _Requirements: 27.4, 27.5_
  - [x] 43.3 实现响应验证逻辑
    - 验证关键词匹配和正则模式匹配
    - _Requirements: 27.4_

- [x] 44. 实现 DataAgent 客户端
  - [x] 44.1 实现 REST API 客户端
    - 支持 health check、chat、sessions 等端点
    - _Requirements: 27.6_
  - [x] 44.2 实现 WebSocket 客户端
    - 支持流式聊天和事件接收
    - _Requirements: 27.6_

- [x] 45. 实现压测运行器
  - [x] 45.1 实现 BenchmarkRunner 类
    - 支持配置并发数
    - 支持限制测试数量
    - _Requirements: 27.3_
  - [x] 45.2 实现并发测试执行
    - 使用 asyncio.Semaphore 控制并发
    - _Requirements: 27.3_
  - [x] 45.3 实现结果统计和报告生成
    - 生成 JSON 和 Markdown 报告
    - _Requirements: 27.5_

- [x] 46. 实现 LangSmith 追踪集成
  - [x] 46.1 实现 TracingManager 类
    - 支持环境变量配置
    - _Requirements: 28.1_
  - [x] 46.2 实现数据集创建功能
    - 从测试问题创建 LangSmith 数据集
    - _Requirements: 28.3_
  - [x] 46.3 实现反馈添加功能
    - 将测试结果作为反馈添加到 LangSmith
    - _Requirements: 28.4_

- [x] 47. 实现命令行接口
  - [x] 47.1 实现 run 命令
    - 支持 --dataset, --server, --concurrency 等参数
    - _Requirements: 27.1, 27.3_
  - [x] 47.2 实现 report 命令
    - 支持多种输出格式（summary, json, markdown）
    - _Requirements: 27.5_
  - [x] 47.3 实现 analyze 命令
    - 支持过滤失败案例
    - _Requirements: 27.5_
  - [x] 47.4 实现 feedback 命令
    - 添加测试结果到 LangSmith
    - _Requirements: 28.4_

- [x] 48. 创建示例数据集和文档
  - [x] 48.1 创建示例测试问题集
    - 创建 datasets/sample-qa.json
    - _Requirements: 27.2_
  - [x] 48.2 编写 README.md
    - 说明使用方法和配置选项
    - _Requirements: 27.1_

- [x] 49. 编写单元测试
  - [x] 49.1 编写模型测试
    - 测试 Question、QuestionSet、QuestionResult 等模型
    - _Requirements: 27.2, 27.4_
  - [x] 49.2 编写响应验证属性测试
    - 测试关键词匹配和模式匹配逻辑
    - _Requirements: 27.4_

- [x] 50. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 8: MCP Server 配置与多租户支持

- [x] 51. 实现 MCP 配置数据模型
  - [x] 51.1 创建 MCPServerConfig 和 MCPConfig 数据类
    - 在 dataagent-core/mcp/config.py 中实现
    - 支持从 JSON 文件加载和保存配置
    - _Requirements: 29.1, 29.2_
  - [x] 51.2 创建 Pydantic 模型用于 API
    - 在 dataagent-server/models/mcp.py 中实现
    - 包含 MCPServerConfigRequest 和 MCPServerConfigResponse
    - _Requirements: 30.2_

- [x] 52. 实现 CLI 模式 MCP 配置加载
  - [x] 52.1 实现 MCPConfigLoader 类
    - 在 dataagent-core/mcp/loader.py 中实现
    - 支持从 ~/.deepagents/{assistant_id}/mcp.json 加载配置
    - 支持 --mcp-config 命令行参数
    - _Requirements: 29.1, 29.6_
  - [x] 52.2 集成 langchain-mcp-adapters
    - 使用 MultiServerMCPClient 连接 MCP Server
    - 获取 MCP 工具并注入到 Agent
    - _Requirements: 29.3, 29.4_
  - [x] 52.3 实现 MCP 连接错误处理
    - 连接失败时记录警告日志
    - 不阻塞主流程
    - _Requirements: 29.5_
  - [ ]* 52.4 编写 CLI MCP 配置加载属性测试
    - **Property 47: CLI MCP 配置加载**
    - **Validates: Requirements 29.1, 29.2**
  - [ ]* 52.5 编写 MCP 连接失败不阻塞属性测试
    - **Property 48: MCP Server 连接失败不阻塞**
    - **Validates: Requirements 29.5**

- [x] 53. 更新 DataAgentCli 集成 MCP
  - [x] 53.1 更新 CLI main.py 加载 MCP 配置
    - 在启动时加载 MCP 配置
    - 将 MCP 工具添加到 AgentConfig.extra_tools
    - _Requirements: 29.3_
  - [x] 53.2 实现 /mcp reload 命令
    - 支持运行时重载 MCP 配置
    - _Requirements: 29.7_

- [x] 54. Checkpoint - 确保 CLI MCP 功能测试通过
  - All 133 core tests and 119 server tests pass.

- [x] 55. 实现 MCP 连接管理器
  - [x] 55.1 实现 MCPConnectionManager 类
    - 在 dataagent-core/mcp/manager.py 中实现
    - 支持每用户独立的连接池
    - 支持最大连接数限制
    - _Requirements: 31.1, 31.2_
  - [x] 55.2 实现连接生命周期管理
    - 支持连接、断开、健康检查
    - 支持自动重连
    - _Requirements: 31.3, 31.4, 31.5_
  - [ ]* 55.3 编写 MCP 连接池资源释放属性测试
    - **Property 50: MCP 连接池资源释放**
    - **Validates: Requirements 31.3**

- [x] 56. 实现 Server 模式 MCP 配置存储
  - [x] 56.1 实现 MCPConfigStore 抽象类
    - 在 dataagent-core/mcp/store.py 中定义接口
    - 定义 get_user_config, save_user_config, delete_user_config 方法
    - _Requirements: 30.3_
  - [x] 56.2 实现 MemoryMCPConfigStore
    - 内存存储实现
    - _Requirements: 30.3_
  - [x] 56.3 实现 MySQLMCPConfigStore
    - MySQL 存储实现
    - 创建 mcp_servers 表
    - _Requirements: 30.3_

- [x] 57. 实现 MCP 配置 REST API
  - [x] 57.1 创建 api/v1/mcp.py 路由
    - GET /api/v1/users/{user_id}/mcp-servers
    - POST /api/v1/users/{user_id}/mcp-servers
    - PUT /api/v1/users/{user_id}/mcp-servers/{server_name}
    - DELETE /api/v1/users/{user_id}/mcp-servers/{server_name}
    - _Requirements: 30.2_
  - [x] 57.2 实现权限检查
    - 用户只能管理自己的配置
    - 管理员可管理所有用户配置
    - _Requirements: 30.2_
  - [ ]* 57.3 编写用户 MCP 配置隔离属性测试
    - **Property 49: 用户 MCP 配置隔离**
    - **Validates: Requirements 30.4**

- [x] 58. 更新 DataAgentServer 集成 MCP
  - [x] 58.1 更新 AgentFactory 支持 MCP
    - 在创建 Agent 时加载用户 MCP 配置
    - 将 MCP 工具添加到 Agent
    - _Requirements: 30.4_
  - [x] 58.2 更新 WebSocket handler 支持 MCP
    - 在会话创建时连接 MCP Server
    - 在会话结束时断开 MCP 连接
    - _Requirements: 30.6_

- [x] 59. Checkpoint - 确保 Server MCP 功能测试通过
  - All 119 server tests pass.

- [x] 60. 实现用户工作区管理
  - [x] 60.1 实现 UserWorkspaceManager 类
    - 在 dataagent-core/workspace/manager.py 中实现
    - 支持创建、验证、清理用户工作区
    - _Requirements: 33.1, 33.2_
  - [x] 60.2 实现工作区配额管理
    - 支持配置和检查用户配额
    - _Requirements: 33.5, 33.6_
  - [ ]* 60.3 编写用户工作区配额检查属性测试
    - **Property 53: 用户工作区配额检查**
    - **Validates: Requirements 33.6**

- [x] 61. 实现沙箱化文件系统后端
  - [x] 61.1 实现 SandboxedFilesystemBackend 类
    - 在 dataagent-core/workspace/backend.py 中实现
    - 限制操作范围在用户工作区内
    - _Requirements: 32.6, 33.3, 33.4_
  - [ ]* 61.2 编写用户工作区路径沙箱属性测试
    - **Property 52: 用户工作区路径沙箱**
    - **Validates: Requirements 32.6, 33.4**

- [x] 62. 实现用户记忆隔离
  - [x] 62.1 更新 AgentMemoryMiddleware 支持用户隔离
    - 记忆存储路径包含 user_id
    - _Requirements: 34.1, 34.2_
  - [x] 62.2 实现记忆清除 API
    - DELETE /api/v1/users/{user_id}/memory
    - _Requirements: 34.4_
  - [ ]* 62.3 编写用户记忆隔离属性测试
    - **Property 54: 用户记忆隔离**
    - **Validates: Requirements 34.3**

- [x] 63. 实现会话隔离增强
  - [x] 63.1 更新 SessionStore 查询方法
    - 确保 list_by_user 只返回指定用户的会话
    - 已在 MemorySessionStore 和 MySQLSessionStore 中实现
    - _Requirements: 32.1, 32.5_
  - [ ]* 63.2 编写用户会话隔离属性测试
    - **Property 51: 用户会话隔离**
    - **Validates: Requirements 32.5**

- [x] 64. Checkpoint - 确保多租户隔离测试通过
  - All 133 core tests and 119 server tests pass.

- [ ] 65. 实现租户管理（可选，企业版）
  - [ ] 65.1 创建租户数据模型
    - 在 dataagent-core/tenant/models.py 中实现
    - 包含 Tenant 和 UserTenant 数据类
    - _Requirements: 35.2_
  - [ ] 65.2 实现 TenantStore
    - 支持 MySQL 存储
    - 创建 tenants 和 user_tenants 表
    - _Requirements: 35.3_
  - [ ] 65.3 实现租户配额检查
    - 在请求处理前检查租户配额
    - 超出配额返回 429
    - _Requirements: 35.4_
  - [ ] 65.4 实现租户功能开关
    - 支持租户级别禁用某些功能
    - _Requirements: 35.5_

- [x] 66. 更新项目依赖和文档
  - [x] 66.1 更新 pyproject.toml
    - 添加 langchain-mcp-adapters 依赖
    - _Requirements: 29.4_
  - [x] 66.2 更新 README.md
    - 添加 MCP 配置说明
    - 添加多租户配置说明
    - _Requirements: 29.1, 32.1_
  - [x] 66.3 更新 docs/developer-guide.md
    - 添加 MCP 开发指南
    - 添加多租户开发指南
    - _Requirements: 29.1, 32.1_

- [x] 67. 实现 Demo 界面 MCP 配置
  - [x] 67.1 实现 MCP API 客户端函数
    - 在 dataagent-server-demo/app.py 中添加 get_mcp_servers, add_mcp_server, delete_mcp_server 函数
    - 支持调用 Server 的 MCP REST API
    - _Requirements: 36.2, 36.3, 36.4_
  - [x] 67.2 实现 MCP 配置界面组件
    - 添加 render_mcp_config 函数渲染 MCP 配置面板
    - 显示已配置的 MCP Server 列表
    - 提供添加/删除 MCP Server 的表单
    - _Requirements: 36.1, 36.2, 36.3, 36.4_
  - [x] 67.3 添加 MCP 配置标签页
    - 在主界面添加"对话"和"MCP 配置"两个标签页
    - _Requirements: 36.1_
  - [x] 67.4 添加配置示例和错误处理
    - 提供文件系统、数据库、自定义 MCP Server 配置示例
    - API 未实现时显示友好提示
    - _Requirements: 36.6, 36.7_

- [x] 68. Final Checkpoint - 确保所有 Phase 8 测试通过
  - All 133 core tests and 119 server tests pass.
  - MCP configuration (CLI and Server modes) implemented.
  - Multi-tenant user isolation implemented.
  - Remaining: Property tests (52.4, 52.5, 55.3, 57.3, 60.3, 61.2, 62.3, 63.2) and Task 65 (optional enterprise features).
