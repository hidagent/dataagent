# Requirements Document

## Introduction

本文档定义 DataAgent 多租户系统的数据库设计规范和用户管理功能需求。系统需要支持完整的后端管理数据库表结构，包括用户认证、会话管理、MCP 配置、工作空间管理等核心功能，并提供相应的 REST API 接口和前端演示页面。

## Glossary

- **System**: DataAgent 多租户后端管理系统
- **User**: 系统中的租户用户
- **Session**: 用户与 Agent 的对话会话
- **Message**: 会话中的单条消息
- **MCP Server**: Model Context Protocol 服务器配置
- **Workspace**: 用户的隔离工作空间
- **Rule**: 指导 Agent 行为的规则
- **Skill**: 可复用的技能定义
- **Audit Log**: 安全审计日志
- **s_ prefix**: 系统表前缀，标识核心系统表
- **_rel suffix**: 关系表后缀，标识存储实体关系的表

## Requirements

### Requirement 1: 数据库表命名规范

**User Story:** As a 数据库管理员, I want 统一的表命名规范, so that 数据库结构清晰易维护。

#### Acceptance Criteria

1. THE System SHALL use `s_` prefix for all system tables to distinguish from business tables
2. THE System SHALL use `_rel` suffix for relationship tables that store entity associations
3. THE System SHALL use snake_case naming convention for all table and column names
4. THE System SHALL use singular nouns for entity tables (e.g., `s_user` not `s_users`)
5. THE System SHALL use consistent column naming: `id` for primary key, `{entity}_id` for foreign keys

### Requirement 2: 用户账户管理

**User Story:** As a 系统管理员, I want 完整的用户账户管理功能, so that 可以管理多租户用户。

#### Acceptance Criteria

1. WHEN a user registers THEN the System SHALL create a record in `s_user` table with unique `user_id`
2. THE System SHALL store `user_account` field for domain account (e.g., LDAP/AD account)
3. THE System SHALL store `user_source` field to identify user origin (local, ldap, oauth, sso)
4. WHEN authenticating a user THEN the System SHALL validate credentials and return JWT token
5. THE System SHALL support password hashing using bcrypt or argon2 algorithm
6. WHEN a user is deleted THEN the System SHALL cascade delete all associated data

### Requirement 3: API 密钥认证

**User Story:** As a 开发者, I want API 密钥认证, so that 可以通过 API 访问系统。

#### Acceptance Criteria

1. WHEN creating an API key THEN the System SHALL generate a unique key and store its hash in `s_api_key` table
2. THE System SHALL support multiple API keys per user with different scopes
3. WHEN an API key expires THEN the System SHALL reject authentication attempts
4. THE System SHALL record `last_used_at` timestamp for each API key usage
5. WHEN validating an API key THEN the System SHALL check expiration and active status

### Requirement 4: 会话和消息管理

**User Story:** As a 用户, I want 持久化的会话和消息存储, so that 可以查看历史对话。

#### Acceptance Criteria

1. THE System SHALL store sessions in `s_session` table with user isolation via `user_id`
2. THE System SHALL store session-message relationships in `s_session_message_rel` table
3. THE System SHALL store actual message content in `s_message` table
4. WHEN a session is deleted THEN the System SHALL cascade delete related messages
5. THE System SHALL support message roles: user, assistant, system, tool
6. THE System SHALL store tool_calls and tool_call_id for function calling messages

### Requirement 5: MCP 服务器配置

**User Story:** As a 用户, I want 管理我的 MCP 服务器配置, so that 可以连接不同的工具服务。

#### Acceptance Criteria

1. THE System SHALL store MCP configurations in `s_mcp_server` table with user isolation
2. THE System SHALL support both stdio and SSE/HTTP transport types
3. WHEN adding a server THEN the System SHALL validate unique (user_id, server_name) combination
4. THE System SHALL store auto_approve list for automatic tool approval
5. THE System SHALL support server enable/disable without deletion

### Requirement 6: 工作空间管理

**User Story:** As a 用户, I want 隔离的工作空间, so that 文件操作不会影响其他用户。

#### Acceptance Criteria

1. THE System SHALL store workspace metadata in `s_workspace` table
2. THE System SHALL store user-workspace relationships in `s_user_workspace_rel` table
3. THE System SHALL enforce quota limits: max_size_bytes, max_files
4. THE System SHALL track current usage: current_size_bytes, current_file_count
5. WHEN workspace quota is exceeded THEN the System SHALL reject file operations
6. THE System SHALL support multiple workspaces per user with one default workspace

### Requirement 7: 规则和技能管理

**User Story:** As a 用户, I want 自定义规则和技能, so that 可以定制 Agent 行为。

#### Acceptance Criteria

1. THE System SHALL store rules in `s_rule` table with scope levels: global, user, project, session
2. THE System SHALL store skills in `s_skill` table with category and tags
3. THE System SHALL support rule priority (1-100) for conflict resolution
4. THE System SHALL track skill usage_count and last_used_at for analytics
5. WHEN rules conflict THEN the System SHALL apply higher priority rule

### Requirement 8: 安全审计日志

**User Story:** As a 安全管理员, I want 完整的操作审计日志, so that 可以追踪安全事件。

#### Acceptance Criteria

1. THE System SHALL log all CRUD operations to `s_audit_log` table
2. THE System SHALL record requesting_user_id, target_user_id, resource_type, action, result
3. THE System SHALL store IP address and user agent for each request
4. THE System SHALL support log retention policy with automatic cleanup
5. WHEN a security violation occurs THEN the System SHALL log with result='denied'

### Requirement 9: 用户登录 API

**User Story:** As a 前端开发者, I want 用户登录 API, so that 可以实现用户认证。

#### Acceptance Criteria

1. WHEN POST /api/v1/auth/login is called with valid credentials THEN the System SHALL return JWT token
2. WHEN POST /api/v1/auth/login is called with invalid credentials THEN the System SHALL return 401 error
3. THE System SHALL support login via username/password and API key
4. WHEN login succeeds THEN the System SHALL update user's last_login_at timestamp
5. THE System SHALL implement rate limiting for login attempts (max 5 per minute)

### Requirement 10: 用户配置 API

**User Story:** As a 前端开发者, I want 用户配置 API, so that 可以获取和更新用户设置。

#### Acceptance Criteria

1. WHEN GET /api/v1/users/{user_id}/profile is called THEN the System SHALL return user profile
2. WHEN PUT /api/v1/users/{user_id}/profile is called THEN the System SHALL update user profile
3. WHEN GET /api/v1/users/{user_id}/mcp-servers is called THEN the System SHALL return MCP configurations
4. WHEN GET /api/v1/users/{user_id}/workspaces is called THEN the System SHALL return workspace list
5. THE System SHALL validate that requesting user can only access their own data

### Requirement 11: 数据库迁移管理

**User Story:** As a 运维工程师, I want 数据库迁移管理, so that 可以安全升级数据库 schema。

#### Acceptance Criteria

1. THE System SHALL track schema versions in `s_schema_version` table
2. THE System SHALL support forward migrations with version numbers
3. THE System SHALL support rollback to previous versions where possible
4. THE System SHALL generate checksum for migration integrity verification
5. WHEN migration fails THEN the System SHALL rollback and report error

### Requirement 12: 前端演示页面

**User Story:** As a 产品经理, I want 前端演示页面, so that 可以展示系统功能。

#### Acceptance Criteria

1. THE System SHALL provide a login page with username/password form
2. THE System SHALL provide a dashboard showing user profile and statistics
3. THE System SHALL provide MCP server configuration management UI
4. THE System SHALL provide workspace management UI with quota display
5. THE System SHALL use responsive design for mobile compatibility
