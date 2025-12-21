# 用户工作目录多租户隔离需求文档

## 问题描述

当前 dataagent-server 在多租户场景下存在工作目录隔离问题：

1. **所有用户共享服务器运行目录** - 不同用户登录后查询"当前目录"都返回 dataagent-server 运行的目录
2. **缺少用户私有工作目录** - 没有为每个用户分配独立的工作目录
3. **文件操作无隔离** - 用户的文件操作可能影响其他用户或系统文件

## 术语定义

- **Workspace（工作目录）**: 用户在服务器上的私有文件存储目录
- **Default Workspace（默认工作目录）**: 用户登录时自动使用的工作目录
- **Workspace Base Path（工作目录基础路径）**: 所有用户工作目录的父目录

## Requirements

### Requirement 1: 用户工作目录管理

**User Story:** As a system administrator, I want each user to have their own isolated workspace, so that users cannot access each other's files.

#### Acceptance Criteria

1. WHEN a user first logs in THEN the system SHALL automatically create a default workspace for that user
2. WHEN a workspace is created THEN the system SHALL create the corresponding filesystem directory
3. WHEN a user queries the current directory THEN the system SHALL return the user's workspace path, not the server's running directory
4. WHEN a user performs file operations THEN the system SHALL restrict operations to the user's workspace
5. WHEN a user attempts to access paths outside their workspace THEN the system SHALL reject the request

### Requirement 2: Workspace API

**User Story:** As a developer, I want to manage user workspaces through REST API, so that I can integrate workspace management into my application.

#### Acceptance Criteria

1. WHEN a GET request is made to /api/v1/workspaces THEN the system SHALL return all workspaces for the current user
2. WHEN a GET request is made to /api/v1/workspaces/default THEN the system SHALL return the user's default workspace
3. WHEN a POST request is made to /api/v1/workspaces THEN the system SHALL create a new workspace
4. WHEN a PATCH request is made to /api/v1/workspaces/{id} THEN the system SHALL update the workspace
5. WHEN a DELETE request is made to /api/v1/workspaces/{id} THEN the system SHALL delete the workspace
6. WHEN a POST request is made to /api/v1/workspaces/{id}/set-default THEN the system SHALL set the workspace as default

### Requirement 3: Agent 工作目录集成

**User Story:** As a user, I want the AI agent to operate in my workspace, so that file operations are performed in my private directory.

#### Acceptance Criteria

1. WHEN an agent is created for a user THEN the system SHALL configure the agent with the user's workspace path
2. WHEN the agent executes shell commands THEN the system SHALL use the user's workspace as the working directory
3. WHEN the agent generates system prompts THEN the system SHALL include the user's workspace path
4. WHEN the agent performs file operations THEN the system SHALL restrict operations to the user's workspace

### Requirement 4: 配置管理

**User Story:** As a system administrator, I want to configure workspace settings, so that I can control resource usage.

#### Acceptance Criteria

1. WHEN the server starts THEN the system SHALL read workspace configuration from environment variables
2. WHEN DATAAGENT_WORKSPACE_BASE_PATH is set THEN the system SHALL use it as the base path for all workspaces
3. WHEN DATAAGENT_WORKSPACE_DEFAULT_MAX_SIZE_BYTES is set THEN the system SHALL use it as the default quota
4. WHEN DATAAGENT_WORKSPACE_DEFAULT_MAX_FILES is set THEN the system SHALL use it as the default file limit

### Requirement 5: 数据库存储

**User Story:** As a developer, I want workspace metadata to be persisted in the database, so that workspace configurations survive server restarts.

#### Acceptance Criteria

1. WHEN a workspace is created THEN the system SHALL store metadata in s_workspace table
2. WHEN a user-workspace relationship is created THEN the system SHALL store it in s_user_workspace_rel table
3. WHEN workspace metadata is queried THEN the system SHALL retrieve it from the database
4. WHEN a workspace is deleted THEN the system SHALL remove the database records
