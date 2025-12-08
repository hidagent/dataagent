# Design Document

## Overview

本设计文档描述 DataAgent 多租户系统的数据库架构和用户管理功能的详细设计。系统采用规范化的表命名约定，使用 `s_` 前缀标识系统表，`_rel` 后缀标识关系表，确保数据库结构清晰且易于维护。

核心设计原则：
- **多租户隔离**: 所有用户数据通过 user_id 实现严格隔离
- **关系分离**: 实体表和关系表分离，提高查询性能和可维护性
- **双数据库支持**: 同时支持 SQLite3 和 PostgreSQL，适应不同部署场景
- **版本化迁移**: 内置迁移系统，支持平滑升级

## Architecture

### 数据库架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DataAgent 数据库架构                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐                                                       │
│  │   s_user     │ (用户实体表)                                          │
│  │──────────────│                                                       │
│  │ id (PK)      │                                                       │
│  │ user_id (UK) │                                                       │
│  │ username     │                                                       │
│  │ user_account │ ← 域账号                                              │
│  │ user_source  │ ← 用户来源                                            │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         │ 1:N                                                           │
│         │                                                               │
│  ┌──────┴───────────────────────────────────────────────────┐          │
│  │                                                           │          │
│  ▼                    ▼                    ▼                 ▼          │
│ ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│ │s_session│    │s_mcp_    │    │s_user_   │    │s_rule    │          │
│ │         │    │server    │    │workspace │    │          │          │
│ │         │    │          │    │_rel      │    │          │          │
│ └────┬────┘    └──────────┘    └────┬─────┘    └──────────┘          │
│      │                               │                                 │
│      │ 1:N                           │ N:M                             │
│      │                               │                                 │
│      ▼                               ▼                                 │
│ ┌─────────────┐              ┌──────────┐                             │
│ │s_session_   │              │s_workspace│ (工作空间实体表)             │
│ │message_rel  │              │          │                             │
│ └──────┬──────┘              └──────────┘                             │
│        │ N:1                                                           │
│        ▼                                                               │
│ ┌─────────────┐                                                       │
│ │  s_message  │ (消息实体表)                                           │
│ └─────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 表分类

| 类别 | 表名 | 说明 |
|------|------|------|
| **系统核心表** | `s_user` | 用户账户实体 |
| | `s_api_key` | API 认证密钥 |
| | `s_schema_version` | 迁移版本追踪 |
| **会话相关** | `s_session` | 会话实体 |
| | `s_message` | 消息实体 |
| | `s_session_message_rel` | 会话-消息关系 |
| **配置相关** | `s_mcp_server` | MCP 服务器配置 |
| | `s_rule` | 用户规则 |
| | `s_skill` | 用户技能 |
| **工作空间** | `s_workspace` | 工作空间实体 |
| | `s_user_workspace_rel` | 用户-工作空间关系 |
| **审计日志** | `s_audit_log` | 安全审计日志 |

## Components and Interfaces

### 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    DataAgent 架构分层                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  dataagent-cli (单用户本地)                          │  │
│  │  ├── 使用 Core 层接口                                │  │
│  │  ├── MemoryStore / SQLite                           │  │
│  │  └── 无需用户认证                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  dataagent-server (多租户服务端)                     │  │
│  │  ├── 使用 Server 层实现                              │  │
│  │  ├── PostgreSQL + 完整用户管理                           │  │
│  │  ├── JWT 认证 + API Key                             │  │
│  │  └── 多租户隔离                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  dataagent-core (共享核心层)                         │  │
│  │  ├── Store 接口定义                                  │  │
│  │  ├── 基础实现 (Memory, SQLite)                      │  │
│  │  └── 业务逻辑 (Agent, Tools, etc.)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1. Core 层 (dataagent-core)

位置: `source/dataagent-core/dataagent_core/`

**职责**: 提供基础存储接口和简单实现

**目录结构**:
```
dataagent_core/
├── session/
│   ├── store.py              # SessionStore 接口
│   ├── state.py              # Session 数据类
│   └── stores/
│       ├── memory.py         # 内存实现（CLI 使用）
│       └── postgres.py          # PostgreSQL 实现（Server 使用）
├── user/
│   ├── store.py              # UserProfileStore 接口
│   ├── profile.py            # UserProfile 数据类
│   └── sqlite_store.py       # SQLite 实现
└── mcp/
    ├── store.py              # MCPConfigStore 接口
    └── sqlite_store.py       # SQLite 实现
```

**特点**:
- ✅ 接口驱动设计
- ✅ 不包含认证逻辑
- ✅ 不包含多租户逻辑
- ✅ CLI 和 Server 都可使用

### 2. Server 层 (dataagent-server)

位置: `source/dataagent-server/dataagent_server/`

**职责**: 提供完整的多租户数据库实现

**目录结构**:
```
dataagent_server/
├── database/
│   ├── __init__.py
│   ├── models.py             # 所有系统表 ORM（s_ 前缀）
│   ├── migration.py          # 数据库迁移管理
│   ├── factory.py            # 数据库工厂
│   └── scripts/
│       ├── sqlite_schema.sql
│       └── postgres_schema.sql
├── auth/
│   ├── __init__.py
│   ├── jwt.py                # JWT Token 管理
│   ├── password.py           # 密码哈希
│   └── middleware.py         # 认证中间件
├── api/
│   └── v1/
│       ├── auth.py           # 认证 API
│       ├── users.py          # 用户管理 API
│       ├── sessions.py       # 会话管理 API
│       └── mcp.py            # MCP 配置 API
└── stores/
    ├── user_store.py         # 多租户用户存储
    ├── session_store.py      # 多租户会话存储
    └── mcp_store.py          # 多租户 MCP 存储
```

**特点**:
- ✅ 完整的用户管理
- ✅ JWT + API Key 认证
- ✅ 多租户隔离
- ✅ **双数据库支持**: SQLite (开发/测试) + PostgreSQL (生产)

**数据库选择**:
```python
# 开发环境 - SQLite
DATABASE_URL = "sqlite+aiosqlite:///dataagent_server.db"

# 生产环境 - PostgreSQL
DATABASE_URL = "postgres+aiopostgres://user:pass@localhost/dataagent"
```

**优势**:
- 开发人员无需安装 PostgreSQL 即可开发和测试
- 使用相同的 ORM 模型和迁移脚本
- 生产环境可无缝切换到 PostgreSQL

### 3. API 层 (REST API)

位置: `source/dataagent-server/dataagent_server/api/v1/`

提供 RESTful API 接口：
- `/api/v1/auth/*`: 认证相关
- `/api/v1/users/*`: 用户管理
- `/api/v1/sessions/*`: 会话管理
- `/api/v1/mcp/*`: MCP 配置管理

### 4. 前端层 (Frontend Demo)

位置: `source/dataagent-server-demo/`

使用 **Streamlit** 实现演示页面，提供：
- 登录页面
- 用户仪表板
- MCP 配置管理
- 工作空间管理
- 会话历史查看

**项目结构**:
```
source/dataagent-server-demo/
├── dataagent_server_demo/
│   ├── __init__.py
│   ├── app.py                  # 主应用入口
│   ├── pages/
│   │   ├── 1_🔐_Login.py       # 登录页面
│   │   ├── 2_📊_Dashboard.py   # 用户仪表板
│   │   ├── 3_🔌_MCP.py         # MCP 配置管理
│   │   ├── 4_📁_Workspaces.py  # 工作空间管理
│   │   └── 5_💬_Sessions.py    # 会话历史
│   └── utils/
│       ├── auth.py             # 认证工具
│       ├── api_client.py       # API 客户端
│       └── ui_components.py    # UI 组件
├── pyproject.toml
└── README.md
```

**技术栈**:
- 框架: Streamlit
- HTTP 客户端: httpx (异步)
- WebSocket: websocket-client
- 状态管理: st.session_state

## Data Models

### 核心表设计

#### 1. s_user - 用户表

```sql
CREATE TABLE s_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    user_account VARCHAR(128),              -- 域账号 (LDAP/AD)
    user_source VARCHAR(32) NOT NULL,       -- 用户来源: local, ldap, oauth, sso
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(256),
    password_hash VARCHAR(256),
    department VARCHAR(128),
    role VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active',    -- active, inactive, suspended
    custom_fields TEXT,                     -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
```

**新增字段说明**:
- `user_account`: 存储域账号，用于企业 LDAP/AD 集成
- `user_source`: 标识用户来源，支持多种认证方式

#### 2. s_session - 会话表

```sql
CREATE TABLE s_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    assistant_id VARCHAR(64) NOT NULL,
    title VARCHAR(256),
    state TEXT,                             -- JSON
    metadata TEXT,                          -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived INTEGER DEFAULT 0
);
```

#### 3. s_message - 消息实体表

```sql
CREATE TABLE s_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(32) NOT NULL,              -- user, assistant, system, tool
    content TEXT NOT NULL,
    tool_calls TEXT,                        -- JSON
    tool_call_id VARCHAR(64),
    metadata TEXT,                          -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**设计说明**: 消息是独立实体，通过关系表与会话关联，支持消息复用和灵活查询。

#### 4. s_session_message_rel - 会话消息关系表

```sql
CREATE TABLE s_session_message_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) NOT NULL REFERENCES s_session(session_id) ON DELETE CASCADE,
    message_id VARCHAR(64) NOT NULL REFERENCES s_message(message_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,       -- 消息在会话中的顺序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, message_id),
    UNIQUE(session_id, sequence_number)
);
```

**设计说明**: 
- 使用关系表分离会话和消息，提高查询性能
- `sequence_number` 保证消息顺序
- 支持同一消息在不同会话中复用（如系统消息）

#### 5. s_workspace - 工作空间实体表

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
    is_active INTEGER DEFAULT 1,
    settings TEXT,                          -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP
);
```

**设计说明**: 工作空间是独立实体，可以被多个用户共享（通过关系表）。

#### 6. s_user_workspace_rel - 用户工作空间关系表

```sql
CREATE TABLE s_user_workspace_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL REFERENCES s_user(user_id) ON DELETE CASCADE,
    workspace_id VARCHAR(64) NOT NULL REFERENCES s_workspace(workspace_id) ON DELETE CASCADE,
    is_default INTEGER DEFAULT 0,
    permission VARCHAR(32) DEFAULT 'read_write',  -- read_only, read_write, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, workspace_id)
);
```

**设计说明**:
- 支持用户拥有多个工作空间
- 支持工作空间共享（多个用户访问同一工作空间）
- 每个用户可以设置一个默认工作空间

### 完整表清单

| 表名 | 类型 | 说明 |
|------|------|------|
| `s_schema_version` | 系统表 | 迁移版本追踪 |
| `s_user` | 实体表 | 用户账户 |
| `s_api_key` | 实体表 | API 密钥 |
| `s_session` | 实体表 | 会话 |
| `s_message` | 实体表 | 消息 |
| `s_session_message_rel` | 关系表 | 会话-消息关联 |
| `s_mcp_server` | 实体表 | MCP 服务器配置 |
| `s_workspace` | 实体表 | 工作空间 |
| `s_user_workspace_rel` | 关系表 | 用户-工作空间关联 |
| `s_rule` | 实体表 | 用户规则 |
| `s_skill` | 实体表 | 用户技能 |
| `s_audit_log` | 日志表 | 安全审计日志 |


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 用户隔离完整性
*For any* two different users, querying one user's data should never return another user's data
**Validates: Requirements 2.6**

### Property 2: 表命名一致性
*For all* system tables, the table name must start with `s_` prefix
**Validates: Requirements 1.1**

### Property 3: 关系表命名一致性
*For all* relationship tables, the table name must end with `_rel` suffix
**Validates: Requirements 1.2**

### Property 4: 级联删除完整性
*For any* user deletion, all associated data (sessions, messages, workspaces) must be automatically deleted
**Validates: Requirements 2.6**

### Property 5: 会话消息关联完整性
*For any* session, all messages must be accessible through s_session_message_rel table
**Validates: Requirements 4.4**

### Property 6: 工作空间配额强制
*For any* workspace, when current_size_bytes exceeds max_size_bytes, file operations must be rejected
**Validates: Requirements 6.5**

### Property 7: API 密钥过期验证
*For any* expired API key, authentication attempts must fail
**Validates: Requirements 3.3**

### Property 8: 审计日志完整性
*For all* CRUD operations, an audit log entry must be created
**Validates: Requirements 8.2**

### Property 9: 消息顺序保证
*For any* session, messages must be retrievable in the correct sequence order
**Validates: Requirements 4.6**

### Property 10: 用户来源验证
*For any* user, user_source must be one of: local, ldap, oauth, sso
**Validates: Requirements 2.3**

## Error Handling

### 数据库错误处理

1. **连接失败**: 自动重试 3 次，间隔 1 秒
2. **唯一约束冲突**: 返回 409 Conflict 错误
3. **外键约束失败**: 返回 400 Bad Request 错误
4. **事务失败**: 自动回滚，记录错误日志

### API 错误响应

```python
{
    "error": {
        "code": "USER_NOT_FOUND",
        "message": "User with id 'xxx' not found",
        "details": {},
        "timestamp": "2024-12-08T10:30:00Z"
    }
}
```

### 常见错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| `INVALID_CREDENTIALS` | 401 | 认证失败 |
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `DUPLICATE_USERNAME` | 409 | 用户名已存在 |
| `QUOTA_EXCEEDED` | 429 | 配额超限 |
| `INVALID_TOKEN` | 401 | Token 无效或过期 |

## Testing Strategy

### 单元测试

测试各个 Store 层的 CRUD 操作：
- 用户创建、查询、更新、删除
- 会话和消息的关联操作
- 工作空间配额检查
- API 密钥验证

### 集成测试

测试完整的 API 流程：
- 用户注册 → 登录 → 获取配置
- 创建会话 → 发送消息 → 查询历史
- 配置 MCP 服务器 → 连接测试

### 属性测试

使用 Hypothesis (Python) 进行属性测试：
- 测试用户隔离属性
- 测试级联删除属性
- 测试配额强制属性

### 性能测试

- 并发用户登录测试 (100 用户/秒)
- 大量消息查询测试 (10000 条消息)
- 数据库连接池压力测试

## API Design

### 认证 API

#### POST /api/v1/auth/login
用户登录

**Request:**
```json
{
    "username": "alice",
    "password": "password123"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
        "user_id": "alice",
        "username": "alice",
        "display_name": "Alice",
        "email": "alice@example.com"
    }
}
```

#### POST /api/v1/auth/logout
用户登出

**Request:**
```json
{
    "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
    "message": "Logged out successfully"
}
```

### 用户管理 API

#### GET /api/v1/users/{user_id}/profile
获取用户配置

**Response:**
```json
{
    "user_id": "alice",
    "username": "alice",
    "user_account": "alice@company.com",
    "user_source": "ldap",
    "display_name": "Alice",
    "email": "alice@example.com",
    "department": "Engineering",
    "role": "Developer",
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-12-08T10:00:00Z"
}
```

#### PUT /api/v1/users/{user_id}/profile
更新用户配置

**Request:**
```json
{
    "display_name": "Alice Smith",
    "department": "Engineering",
    "custom_fields": {
        "timezone": "Asia/Shanghai",
        "language": "zh-CN"
    }
}
```

#### GET /api/v1/users/{user_id}/mcp-servers
获取 MCP 服务器列表

**Response:**
```json
{
    "servers": [
        {
            "server_name": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": "***"},
            "transport": "stdio",
            "disabled": false
        }
    ]
}
```

#### GET /api/v1/users/{user_id}/workspaces
获取工作空间列表

**Response:**
```json
{
    "workspaces": [
        {
            "workspace_id": "ws_123",
            "name": "Default Workspace",
            "path": "/workspaces/alice/default",
            "is_default": true,
            "permission": "admin",
            "quota": {
                "max_size_bytes": 1073741824,
                "max_files": 10000,
                "current_size_bytes": 52428800,
                "current_file_count": 150
            }
        }
    ]
}
```

### 会话管理 API

#### GET /api/v1/sessions
获取会话列表

**Query Parameters:**
- `user_id`: 用户 ID (必需)
- `limit`: 返回数量 (默认 20)
- `offset`: 偏移量 (默认 0)

**Response:**
```json
{
    "sessions": [
        {
            "session_id": "sess_123",
            "title": "代码审查讨论",
            "created_at": "2024-12-08T09:00:00Z",
            "last_active": "2024-12-08T10:30:00Z",
            "message_count": 15
        }
    ],
    "total": 50,
    "limit": 20,
    "offset": 0
}
```

#### GET /api/v1/sessions/{session_id}/messages
获取会话消息

**Response:**
```json
{
    "messages": [
        {
            "message_id": "msg_001",
            "role": "user",
            "content": "帮我审查这段代码",
            "created_at": "2024-12-08T09:00:00Z"
        },
        {
            "message_id": "msg_002",
            "role": "assistant",
            "content": "我来帮你审查...",
            "created_at": "2024-12-08T09:00:15Z"
        }
    ]
}
```

## Frontend Design

### 页面结构

Streamlit 多页面应用结构：

```
主页 (app.py)
├── 🔐 Login          - 登录页面
├── 📊 Dashboard      - 用户仪表板
│   ├── 用户信息卡片
│   ├── 统计数据展示
│   └── 快速操作入口
├── 🔌 MCP            - MCP 配置管理
│   ├── 服务器列表
│   ├── JSON 配置编辑
│   └── 连接测试
├── 📁 Workspaces     - 工作空间管理
│   ├── 工作空间列表
│   ├── 配额使用情况
│   └── 文件管理
└── 💬 Sessions       - 会话历史
    ├── 会话列表
    ├── 消息查看
    └── 会话搜索
```

**Streamlit 特性**:
- 自动刷新和状态管理
- 内置组件（表单、图表、文件上传）
- 响应式布局
- 实时数据更新

### 登录页面 (Login Page)

使用 Streamlit 实现：

```python
# pages/1_🔐_Login.py
import streamlit as st
import httpx

st.title("🔐 用户登录")

with st.form("login_form"):
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    remember = st.checkbox("记住我")
    submitted = st.form_submit_button("登录")
    
    if submitted:
        # 调用登录 API
        response = httpx.post(
            f"{API_URL}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.user = data["user"]
            st.success("登录成功！")
            st.switch_page("pages/2_📊_Dashboard.py")
        else:
            st.error("登录失败：用户名或密码错误")
```

### 用户仪表板 (Dashboard)

使用 Streamlit 实现：

```python
# pages/2_📊_Dashboard.py
import streamlit as st

st.title("📊 用户仪表板")

# 用户信息卡片
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("会话数", "25", "+3")
with col2:
    st.metric("消息数", "1,234", "+156")
with col3:
    st.metric("工作空间使用", "45%", "+5%")

# 用户信息
with st.expander("👤 个人信息", expanded=True):
    user = st.session_state.user
    st.write(f"**用户名**: {user['username']}")
    st.write(f"**显示名称**: {user['display_name']}")
    st.write(f"**邮箱**: {user['email']}")
    st.write(f"**部门**: {user['department']}")
    st.write(f"**角色**: {user['role']}")

# 快速操作
st.subheader("快速操作")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔌 配置 MCP", use_container_width=True):
        st.switch_page("pages/3_🔌_MCP.py")
with col2:
    if st.button("📁 管理工作空间", use_container_width=True):
        st.switch_page("pages/4_📁_Workspaces.py")
with col3:
    if st.button("💬 查看会话", use_container_width=True):
        st.switch_page("pages/5_💬_Sessions.py")
```

### MCP 配置管理页面

使用 Streamlit 实现（已有实现，需扩展）：

```python
# pages/3_🔌_MCP.py
import streamlit as st

st.title("🔌 MCP 服务器管理")

# 标签页：列表视图 / JSON 配置
tab1, tab2 = st.tabs(["📋 服务器列表", "📝 JSON 配置"])

with tab1:
    # 刷新和连接全部按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 刷新状态"):
            load_mcp_servers()
    with col2:
        if st.button("🔗 连接全部"):
            connect_all_servers()
    
    # 服务器列表
    for server in servers:
        render_server_row(server)

with tab2:
    # JSON 编辑器
    json_config = st.text_area("mcp.json", height=300)
    if st.button("💾 保存配置"):
        save_mcp_config(json_config)
```

### 工作空间管理页面

使用 Streamlit 实现：

```python
# pages/4_📁_Workspaces.py
import streamlit as st

st.title("📁 工作空间管理")

# 获取工作空间列表
workspaces = get_user_workspaces()

for ws in workspaces:
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.subheader(ws['name'])
            if ws['is_default']:
                st.badge("默认", type="success")
            
            # 配额使用进度条
            usage_pct = ws['current_size_bytes'] / ws['max_size_bytes'] * 100
            st.progress(usage_pct / 100)
            st.caption(f"{format_bytes(ws['current_size_bytes'])} / {format_bytes(ws['max_size_bytes'])}")
            st.caption(f"文件数: {ws['current_file_count']} / {ws['max_files']}")
        
        with col2:
            if not ws['is_default']:
                if st.button("设为默认", key=f"default_{ws['workspace_id']}"):
                    set_default_workspace(ws['workspace_id'])
        
        with col3:
            if st.button("🗑️ 清理", key=f"clean_{ws['workspace_id']}"):
                clean_workspace(ws['workspace_id'])
        
        st.divider()
```

## Implementation Notes

### 数据库迁移流程

1. 创建新的迁移版本（如 V006）
2. 编写 SQLite 和 PostgreSQL 的 SQL 脚本
3. 更新 `migration.py` 注册新迁移
4. 运行 `python scripts/init_database.py` 应用迁移
5. 验证迁移成功

### 表命名规范执行

所有新表必须遵循：
- 系统表：`s_` 前缀
- 关系表：`_rel` 后缀
- 使用 snake_case
- 单数名词

### 安全考虑

1. **密码存储**: 使用 bcrypt 或 argon2 哈希
2. **JWT Token**: 设置合理的过期时间（1小时）
3. **API 限流**: 使用 slowapi 实现速率限制
4. **SQL 注入防护**: 使用 SQLAlchemy ORM 参数化查询
5. **XSS 防护**: 前端输出转义

### 性能优化

1. **索引优化**: 在 user_id, session_id 等常用查询字段建立索引
2. **连接池**: PostgreSQL 使用连接池（pool_size=10）
3. **查询优化**: 使用 JOIN 减少查询次数
4. **缓存策略**: 用户配置缓存 5 分钟
5. **分页查询**: 大数据量使用 LIMIT/OFFSET

## Deployment Considerations

### SQLite 部署

适用场景：
- **开发环境** ✅ 推荐
- **测试环境** ✅ 推荐
- 单机小规模部署
- 演示环境

配置：
```python
# dataagent-server 配置
DATABASE_URL = "sqlite+aiosqlite:///dataagent_server.db"

# 启动命令
python -m dataagent_server --db-url sqlite+aiosqlite:///dataagent_server.db
```

**优势**:
- 零配置，开箱即用
- 快速开发和测试
- 单文件，易于备份

### PostgreSQL 部署

适用场景：
- **生产环境** ✅ 推荐
- 多机集群部署
- 大规模用户（1000+ 用户）
- 需要高可用

配置：
```python
# dataagent-server 配置
DATABASE_URL = "postgres+aiopostgres://user:pass@localhost/dataagent"
POOL_SIZE = 10
MAX_OVERFLOW = 20

# 启动命令
python -m dataagent_server \
  --db-url postgres+aiopostgres://user:pass@localhost/dataagent \
  --pool-size 10
```

**优势**:
- 高性能和高可用
- 支持集群和主从复制
- 更好的并发处理

### 数据备份策略

- SQLite: 每日备份数据库文件
- PostgreSQL: 使用 postgresdump 或 xtrabackup
- 保留最近 30 天的备份

## Summary

本设计文档定义了 DataAgent 多租户系统的完整数据库架构，包括：

✅ 规范化的表命名约定（s_ 前缀，_rel 后缀）  
✅ 实体表和关系表分离设计  
✅ 完整的用户管理和认证系统  
✅ 会话和消息的灵活存储方案  
✅ 工作空间的多用户共享支持  
✅ RESTful API 接口设计  
✅ 前端演示页面设计  
✅ 安全和性能优化策略

