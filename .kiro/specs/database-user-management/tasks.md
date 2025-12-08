# Implementation Plan

## 1. 数据库模型和迁移系统 (Server 层)

- [x] 1.1 创建 Server 层数据库模块结构
  - 在 `source/dataagent-server/dataagent_server/` 下创建 `database/` 目录
  - 创建 `__init__.py`, `models.py`, `migration.py`, `factory.py`
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 1.2 实现系统表 ORM 模型 (s_ 前缀)
  - 实现 `s_user` 表模型，包含 user_account, user_source 字段
  - 实现 `s_api_key` 表模型
  - 实现 `s_session` 表模型
  - 实现 `s_message` 表模型
  - 实现 `s_session_message_rel` 关系表模型
  - 实现 `s_mcp_server` 表模型
  - 实现 `s_workspace` 表模型
  - 实现 `s_user_workspace_rel` 关系表模型
  - 实现 `s_rule` 表模型
  - 实现 `s_skill` 表模型
  - 实现 `s_audit_log` 表模型
  - 实现 `s_schema_version` 表模型
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3, 5.1, 6.1, 6.2, 7.1, 7.2, 8.1_

- [ ] 1.3 编写属性测试：表命名规范
  - **Property 2: 表命名一致性**
  - **Property 3: 关系表命名一致性**
  - **Validates: Requirements 1.1, 1.2**

- [x] 1.4 实现数据库迁移管理器
  - 创建 MigrationManager 类
  - 支持 SQLite 和 MySQL 双数据库
  - 实现版本追踪和回滚功能
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 1.5 创建 SQL 迁移脚本
  - 创建 `scripts/sqlite_schema.sql`
  - 创建 `scripts/mysql_schema.sql`
  - 包含所有系统表的创建语句
  - _Requirements: 11.1, 11.2_

- [ ] 1.6 编写属性测试：迁移完整性
  - **Property 4: 级联删除完整性**
  - **Validates: Requirements 2.6**

- [ ] 1.7 Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 2. 用户认证系统

- [x] 2.1 创建认证模块结构
  - 在 `source/dataagent-server/dataagent_server/` 下创建 `auth/` 目录
  - 创建 `__init__.py`, `jwt.py`, `password.py`, `middleware.py`
  - _Requirements: 2.4, 2.5, 3.1_

- [x] 2.2 实现密码哈希功能
  - 使用 bcrypt 或 argon2 实现密码哈希
  - 实现密码验证函数
  - _Requirements: 2.5_

- [x] 2.3 实现 JWT Token 管理
  - 实现 Token 生成函数
  - 实现 Token 验证函数
  - 设置合理的过期时间（1小时）
  - _Requirements: 9.1, 9.4_

- [x] 2.4 实现 API Key 认证
  - 实现 API Key 生成和哈希存储
  - 实现 API Key 验证
  - 支持多个 API Key 和作用域
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 2.5 编写属性测试：API 密钥过期验证
  - **Property 7: API 密钥过期验证**
  - **Validates: Requirements 3.3**

- [x] 2.6 实现认证中间件
  - 创建 FastAPI 依赖注入
  - 支持 JWT 和 API Key 两种认证方式
  - 实现速率限制（5次/分钟）
  - _Requirements: 9.3, 9.5_

- [ ] 2.7 Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 3. 用户管理 API

- [x] 3.1 实现登录 API
  - POST /api/v1/auth/login - 用户名密码登录
  - 返回 JWT Token 和用户信息
  - 更新 last_login_at 时间戳
  - _Requirements: 9.1, 9.2, 9.4_

- [x] 3.2 实现登出 API
  - POST /api/v1/auth/logout - 用户登出
  - 可选：实现 Token 黑名单
  - _Requirements: 9.1_

- [ ] 3.3 实现用户配置 API
  - GET /api/v1/users/{user_id}/profile - 获取用户配置
  - PUT /api/v1/users/{user_id}/profile - 更新用户配置
  - 验证用户只能访问自己的数据
  - _Requirements: 10.1, 10.2, 10.5_

- [ ] 3.4 编写属性测试：用户隔离完整性
  - **Property 1: 用户隔离完整性**
  - **Validates: Requirements 2.6, 10.5**

- [ ] 3.5 实现 MCP 服务器配置 API
  - GET /api/v1/users/{user_id}/mcp-servers - 获取 MCP 配置列表
  - POST /api/v1/users/{user_id}/mcp-servers - 添加 MCP 服务器
  - DELETE /api/v1/users/{user_id}/mcp-servers/{name} - 删除 MCP 服务器
  - _Requirements: 10.3, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 3.6 实现工作空间 API
  - GET /api/v1/users/{user_id}/workspaces - 获取工作空间列表
  - POST /api/v1/users/{user_id}/workspaces - 创建工作空间
  - PUT /api/v1/users/{user_id}/workspaces/{id} - 更新工作空间
  - _Requirements: 10.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 3.7 编写属性测试：工作空间配额强制
  - **Property 6: 工作空间配额强制**
  - **Validates: Requirements 6.5**

- [ ] 3.8 Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 4. 会话和消息管理

- [x] 4.1 实现会话存储 (多租户)
  - 使用 LangGraph SQLite Checkpointer 持久化 agent 执行状态
  - 在 WebSocket handler 中创建新会话时写入 s_session 表
  - 修改 sessions API 从 s_session 表读取数据
  - 确保 user_id 隔离
  - _Requirements: 4.1, 4.4_

- [ ] 4.2 实现消息存储 (独立实体)
  - 创建 ServerMessageStore 类
  - 实现消息的 CRUD 操作
  - 支持 tool_calls 和 tool_call_id
  - _Requirements: 4.3, 4.5, 4.6_

- [ ] 4.3 实现会话-消息关系管理
  - 创建 SessionMessageRelStore 类
  - 实现消息关联和顺序管理
  - 支持级联删除
  - _Requirements: 4.2, 4.4_

- [ ] 4.4 编写属性测试：会话消息关联完整性
  - **Property 5: 会话消息关联完整性**
  - **Property 9: 消息顺序保证**
  - **Validates: Requirements 4.4, 4.6**

- [ ] 4.5 实现会话管理 API
  - GET /api/v1/sessions - 获取会话列表
  - GET /api/v1/sessions/{id} - 获取会话详情
  - GET /api/v1/sessions/{id}/messages - 获取会话消息
  - DELETE /api/v1/sessions/{id} - 删除会话
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 4.6 Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 5. 审计日志系统

- [ ] 5.1 实现审计日志存储
  - 创建 AuditLogStore 类
  - 实现日志记录功能
  - 支持按时间和用户查询
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 5.2 实现审计日志中间件
  - 自动记录所有 CRUD 操作
  - 记录 IP 地址和 User Agent
  - 记录安全违规事件
  - _Requirements: 8.2, 8.3, 8.5_

- [ ] 5.3 编写属性测试：审计日志完整性
  - **Property 8: 审计日志完整性**
  - **Validates: Requirements 8.2**

- [ ] 5.4 实现日志清理功能
  - 支持配置保留天数
  - 实现自动清理任务
  - _Requirements: 8.4_

- [ ] 5.5 Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 6. 前端演示页面 (Streamlit)

- [x] 6.1 创建登录页面
  - 在 `source/dataagent-server-demo/dataagent_server_demo/pages/` 下创建 `1_🔐_Login.py`
  - 实现用户名/密码登录表单
  - 实现 Token 存储到 session_state
  - 实现错误提示
  - _Requirements: 12.1_

- [x] 6.2 创建用户仪表板页面
  - 创建 `2_📊_Dashboard.py`
  - 显示用户信息卡片
  - 显示统计数据（会话数、消息数、工作空间使用率）
  - 提供快速操作入口
  - _Requirements: 12.2_

- [x] 6.3 扩展 MCP 配置管理页面
  - 更新现有 MCP 管理功能
  - 添加认证支持
  - 优化 UI 显示
  - _Requirements: 12.3_

- [x] 6.4 创建工作空间管理页面
  - 创建 `4_📁_Workspaces.py`
  - 显示工作空间列表
  - 显示配额使用进度条
  - 支持设置默认工作空间
  - _Requirements: 12.4_

- [x] 6.5 创建会话历史页面
  - 创建 `5_💬_Sessions.py`
  - 显示会话列表
  - 支持查看会话消息
  - 支持会话搜索
  - _Requirements: 12.2_

- [x] 6.6 实现响应式设计
  - 使用 Streamlit 的 columns 和 container
  - 确保移动端可用
  - _Requirements: 12.5_

- [ ] 6.7 Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 7. 数据库初始化脚本

- [ ] 7.1 更新数据库初始化脚本
  - 更新 `scripts/init_database.py`
  - 支持 Server 层的新表结构
  - 支持创建测试用户
  - _Requirements: 11.1, 11.2_

- [ ] 7.2 创建测试数据脚本
  - 创建示例用户数据
  - 创建示例会话和消息
  - 创建示例 MCP 配置
  - _Requirements: 2.1_

- [ ] 7.3 更新文档
  - 更新 `docs/database-design.md`
  - 添加 API 文档
  - 添加部署指南
  - _Requirements: 11.1_

- [ ] 7.4 Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.
