# 用户工作目录多租户隔离设计文档

## Overview

本设计实现了 dataagent-server 的多租户用户工作目录隔离功能，确保每个用户拥有独立的文件系统工作空间，Agent 执行时使用用户的私有目录而非服务器运行目录。

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      dataagent-server                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  User A     │  │  User B     │  │  User C     │              │
│  │  Session    │  │  Session    │  │  Session    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐              │
│  │  Agent A    │  │  Agent B    │  │  Agent C    │              │
│  │  workspace: │  │  workspace: │  │  workspace: │              │
│  │  /ws/userA  │  │  /ws/userB  │  │  /ws/userC  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
├─────────┼────────────────┼────────────────┼─────────────────────┤
│         ▼                ▼                ▼                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Workspace Manager                           │    │
│  │  - Path validation                                       │    │
│  │  - Quota management                                      │    │
│  │  - Directory creation                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      File System                                 │
├─────────────────────────────────────────────────────────────────┤
│  /var/dataagent/workspaces/                                      │
│  ├── userA/                                                      │
│  │   ├── project1/                                               │
│  │   └── project2/                                               │
│  ├── userB/                                                      │
│  │   └── data/                                                   │
│  └── userC/                                                      │
│      └── scripts/                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Workspace API (`/api/v1/workspaces`)

新增 REST API 端点用于工作目录管理：

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /workspaces | 列出用户所有工作目录 |
| GET | /workspaces/default | 获取默认工作目录 |
| POST | /workspaces | 创建新工作目录 |
| GET | /workspaces/{id} | 获取工作目录详情 |
| PATCH | /workspaces/{id} | 更新工作目录 |
| DELETE | /workspaces/{id} | 删除工作目录 |
| POST | /workspaces/{id}/set-default | 设置默认工作目录 |

### 2. AgentConfig 扩展

在 `AgentConfig` 数据类中新增字段：

```python
@dataclass
class AgentConfig:
    # ... existing fields ...
    user_id: str | None = None  # 用户 ID
    workspace_path: str | None = None  # 用户工作目录路径
```

### 3. AgentFactory 修改

修改 `create_agent` 方法：
- 使用 `workspace_path` 配置 `ShellMiddleware`
- 将 `workspace_path` 传递给 `get_system_prompt`

### 4. WebSocket Handler 修改

在 `_get_or_create_executor` 方法中：
- 调用 `_get_user_workspace_path` 获取用户工作目录
- 如果不存在则自动创建默认工作目录
- 将 `workspace_path` 设置到 `AgentConfig`

### 5. 配置项

新增服务器配置项：

```python
class ServerSettings(BaseSettings):
    # Workspace configuration
    workspace_base_path: str = "/var/dataagent/workspaces"
    workspace_default_max_size_bytes: int = 1073741824  # 1GB
    workspace_default_max_files: int = 10000
```

## Data Models

### s_workspace 表

```sql
CREATE TABLE s_workspace (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL,
    description TEXT,
    max_size_bytes BIGINT DEFAULT 1073741824,
    max_files INTEGER DEFAULT 10000,
    current_size_bytes BIGINT DEFAULT 0,
    current_file_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    settings TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at DATETIME
);
```

### s_user_workspace_rel 表

```sql
CREATE TABLE s_user_workspace_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    permission VARCHAR(32) DEFAULT 'read_write',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES s_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES s_workspace(workspace_id) ON DELETE CASCADE,
    UNIQUE (user_id, workspace_id)
);
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Workspace Isolation

*For any* two different users A and B, user A's file operations SHALL NOT affect user B's workspace, and user A SHALL NOT be able to read or write files in user B's workspace.

**Validates: Requirements 1.4, 1.5**

### Property 2: Default Workspace Creation

*For any* user who logs in for the first time, the system SHALL create a default workspace before the first agent execution completes.

**Validates: Requirements 1.1, 1.2**

### Property 3: Agent Workspace Binding

*For any* agent created for a user, the agent's working directory SHALL be set to the user's default workspace path.

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 4: API CRUD Consistency

*For any* workspace created via POST /workspaces, a subsequent GET /workspaces SHALL include that workspace in the response.

**Validates: Requirements 2.1, 2.3**

### Property 5: Configuration Persistence

*For any* workspace configuration stored in the database, the configuration SHALL survive server restarts.

**Validates: Requirements 5.1, 5.2, 5.3**

## Error Handling

| Error Scenario | HTTP Status | Error Code | Description |
|----------------|-------------|------------|-------------|
| Workspace not found | 404 | WORKSPACE_NOT_FOUND | 请求的工作目录不存在 |
| Permission denied | 403 | PERMISSION_DENIED | 用户无权访问该工作目录 |
| Path escape attempt | 400 | PATH_ESCAPE_ERROR | 尝试访问工作目录外的路径 |
| Quota exceeded | 400 | QUOTA_EXCEEDED | 超出工作目录配额限制 |
| Directory creation failed | 500 | DIRECTORY_ERROR | 无法创建工作目录 |

## Testing Strategy

### Unit Tests

1. 测试 `get_user_default_workspace_path` 函数
2. 测试 `ensure_user_default_workspace` 函数
3. 测试 Workspace API 各端点
4. 测试 AgentConfig 新字段

### Integration Tests

1. 测试用户登录后自动创建工作目录
2. 测试 Agent 执行时使用正确的工作目录
3. 测试多用户并发访问时的隔离性

### Property-Based Tests

使用 Hypothesis 库进行属性测试：
- 测试路径验证逻辑
- 测试配额检查逻辑
- 测试用户隔离性
