# DataAgent 多租户数据库设计

## 1. 概述

本文档描述 DataAgent 多租户系统的数据库设计，支持 SQLite3 和 PostgreSQL 两种数据库后端。

### 1.1 设计目标

- **多租户隔离**: 所有数据通过 `user_id` 实现租户隔离
- **可扩展性**: 支持从单机 SQLite 平滑迁移到 PostgreSQL 集群
- **版本管理**: 内置迁移系统，支持增量升级
- **审计追踪**: 完整的操作审计日志

### 1.2 数据库选择

| 场景 | 推荐数据库 | 说明 |
|------|-----------|------|
| 开发/测试 | SQLite3 | 零配置，单文件 |
| 单机生产 | SQLite3 | 简单部署，性能足够 |
| 多机生产 | PostgreSQL 15+ | 高可用，支持集群，LangGraph 原生支持 |

## 2. 表结构设计

### 2.1 ER 图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DataAgent 数据库 ER 图                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐                                                          │
│   │    users     │──────────────────────────────────────────────────────┐   │
│   │──────────────│                                                      │   │
│   │ user_id (PK) │                                                      │   │
│   │ username     │                                                      │   │
│   │ display_name │                                                      │   │
│   │ email        │                                                      │   │
│   │ status       │                                                      │   │
│   └──────┬───────┘                                                      │   │
│          │                                                              │   │
│          │ 1:N                                                          │   │
│          │                                                              │   │
│   ┌──────┴───────┬──────────────┬──────────────┬──────────────┐        │   │
│   │              │              │              │              │        │   │
│   ▼              ▼              ▼              ▼              ▼        │   │
│ ┌────────┐  ┌─────────┐  ┌───────────┐  ┌────────┐  ┌────────┐        │   │
│ │sessions│  │api_keys │  │mcp_servers│  │  rules │  │ skills │        │   │
│ │────────│  │─────────│  │───────────│  │────────│  │────────│        │   │
│ │session │  │ key_id  │  │server_name│  │rule_nam│  │skill_na│        │   │
│ │_id(PK) │  │ (PK)    │  │ (UK)      │  │e (UK)  │  │me (UK) │        │   │
│ │user_id │  │ user_id │  │ user_id   │  │user_id │  │user_id │        │   │
│ │(FK)    │  │ (FK)    │  │ (FK)      │  │(FK)    │  │(FK)    │        │   │
│ └───┬────┘  └─────────┘  └───────────┘  └────────┘  └────────┘        │   │
│     │                                                                  │   │
│     │ 1:N                                                              │   │
│     ▼                                                                  │   │
│ ┌────────┐                                                             │   │
│ │messages│                                                             │   │
│ │────────│                                                             │   │
│ │message │                                                             │   │
│ │_id(PK) │                                                             │   │
│ │session │                                                             │   │
│ │_id(FK) │                                                             │   │
│ └────────┘                                                             │   │
│                                                                        │   │
│   ┌────────────┐                                                       │   │
│   │ workspaces │◄──────────────────────────────────────────────────────┘   │
│   │────────────│                                                           │
│   │workspace_id│                                                           │
│   │ user_id    │                                                           │
│   └────────────┘                                                           │
│                                                                             │
│   ┌────────────┐                                                           │
│   │ audit_logs │  (独立表，记录所有操作)                                     │
│   │────────────│                                                           │
│   │ timestamp  │                                                           │
│   │ user_id    │                                                           │
│   │ action     │                                                           │
│   └────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 表清单

| 表名 | 说明 | 主要字段 |
|------|------|---------|
| `schema_versions` | 迁移版本追踪 | version, applied_at |
| `users` | 用户账户 | user_id, username, status |
| `api_keys` | API 认证密钥 | key_id, user_id, key_hash |
| `sessions` | 会话管理 | session_id, user_id, assistant_id |
| `messages` | 聊天消息 | message_id, session_id, role, content |
| `mcp_servers` | MCP 服务器配置 | user_id, server_name, command/url |
| `workspaces` | 工作空间元数据 | workspace_id, user_id, path, quota |
| `rules` | 用户规则 | user_id, rule_name, content, scope |
| `skills` | 用户技能 | user_id, skill_name, content |
| `audit_logs` | 审计日志 | timestamp, user_id, action, result |

## 3. 详细表设计

### 3.1 users - 用户表

存储用户账户和基本信息。

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,    -- 用户唯一标识
    username VARCHAR(64) UNIQUE NOT NULL,   -- 登录用户名
    display_name VARCHAR(128) NOT NULL,     -- 显示名称
    email VARCHAR(256),                     -- 邮箱
    password_hash VARCHAR(256),             -- 密码哈希（本地认证）
    department VARCHAR(128),                -- 部门
    role VARCHAR(64),                       -- 角色
    status ENUM('active','inactive','suspended'), -- 状态
    custom_fields JSON,                     -- 自定义字段
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_login_at TIMESTAMP
);
```

**索引**:
- `idx_users_user_id` - 主查询索引
- `idx_users_username` - 登录查询
- `idx_users_email` - 邮箱查询
- `idx_users_status` - 状态过滤
- `idx_users_department` - 部门过滤

### 3.2 api_keys - API 密钥表

存储用户的 API 认证密钥。

```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY,
    key_id VARCHAR(64) UNIQUE NOT NULL,     -- 密钥 ID（公开）
    user_id VARCHAR(64) NOT NULL,           -- 所属用户
    key_hash VARCHAR(256) NOT NULL,         -- 密钥哈希
    name VARCHAR(128) NOT NULL,             -- 密钥名称/描述
    scopes JSON,                            -- 权限范围
    expires_at TIMESTAMP,                   -- 过期时间
    last_used_at TIMESTAMP,                 -- 最后使用时间
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3.3 sessions - 会话表

存储用户与 Agent 的会话。

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,           -- 所属用户
    assistant_id VARCHAR(64) NOT NULL,      -- Agent ID
    title VARCHAR(256),                     -- 会话标题
    state JSON,                             -- 会话状态
    metadata JSON,                          -- 元数据
    created_at TIMESTAMP,
    last_active TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3.4 messages - 消息表

存储会话中的消息。

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL,        -- 所属会话
    role ENUM('user','assistant','system','tool'),
    content TEXT NOT NULL,
    tool_calls JSON,                        -- 工具调用
    tool_call_id VARCHAR(64),               -- 工具响应 ID
    metadata JSON,
    created_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
```

### 3.5 mcp_servers - MCP 服务器配置表

存储用户的 MCP 服务器配置。

```sql
CREATE TABLE mcp_servers (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    server_name VARCHAR(128) NOT NULL,
    command VARCHAR(512),                   -- stdio 命令
    args JSON,                              -- 命令参数
    env JSON,                               -- 环境变量
    url VARCHAR(512),                       -- SSE/HTTP URL
    transport VARCHAR(32) DEFAULT 'stdio',  -- 传输类型
    headers JSON,                           -- HTTP 头
    disabled BOOLEAN DEFAULT FALSE,
    auto_approve JSON,                      -- 自动批准的工具
    timeout_seconds INTEGER DEFAULT 30,
    max_retries INTEGER DEFAULT 3,
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, server_name),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3.6 workspaces - 工作空间表

存储用户工作空间的元数据。

```sql
CREATE TABLE workspaces (
    id INTEGER PRIMARY KEY,
    workspace_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL,             -- 文件系统路径
    max_size_bytes BIGINT DEFAULT 1073741824,  -- 1GB
    max_files INTEGER DEFAULT 10000,
    current_size_bytes BIGINT DEFAULT 0,
    current_file_count INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    settings JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3.7 rules - 规则表

存储用户的 Agent 规则。

```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope ENUM('global','user','project','session') DEFAULT 'user',
    inclusion ENUM('always','fileMatch','manual') DEFAULT 'always',
    file_match_pattern VARCHAR(256),
    priority INTEGER DEFAULT 50,            -- 1-100
    override BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, rule_name),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3.8 skills - 技能表

存储用户的可复用技能。

```sql
CREATE TABLE skills (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    skill_name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category VARCHAR(64),
    tags JSON,
    parameters JSON,                        -- 输入参数 schema
    enabled BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, skill_name),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3.9 audit_logs - 审计日志表

记录所有安全相关操作。

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requesting_user_id VARCHAR(64) NOT NULL,
    target_user_id VARCHAR(64),
    resource_type ENUM('user','session','message','mcp','workspace','rule','skill','api_key'),
    resource_id VARCHAR(128),
    action ENUM('create','read','update','delete','execute','login','logout'),
    result ENUM('success','failure','denied'),
    ip_address VARCHAR(45),                 -- IPv6 兼容
    user_agent VARCHAR(512),
    session_id VARCHAR(64),
    request_id VARCHAR(64),
    details JSON,
    error_message TEXT
);
```

**PostgreSQL 分区**: 按时间分区以优化查询和清理

```sql
PARTITION BY RANGE (UNIX_TIMESTAMP(timestamp)) (
    PARTITION p_2024_q1 VALUES LESS THAN (UNIX_TIMESTAMP('2024-04-01')),
    PARTITION p_2024_q2 VALUES LESS THAN (UNIX_TIMESTAMP('2024-07-01')),
    ...
);
```

## 4. 迁移管理

### 4.1 版本追踪

使用 `schema_versions` 表追踪已应用的迁移：

```sql
CREATE TABLE schema_versions (
    id INTEGER PRIMARY KEY,
    version VARCHAR(32) UNIQUE NOT NULL,
    description TEXT,
    applied_at TIMESTAMP,
    checksum VARCHAR(64)
);
```

### 4.2 迁移版本

| 版本 | 描述 |
|------|------|
| 001 | 初始 schema - users, sessions, messages |
| 002 | MCP 服务器配置 |
| 003 | 用户工作空间 |
| 004 | 规则和技能 |
| 005 | API 密钥和审计日志 |

### 4.3 使用迁移管理器

```python
from sqlalchemy.ext.asyncio import create_async_engine
from dataagent_core.database import MigrationManager

# SQLite
engine = create_async_engine("sqlite+aiosqlite:///dataagent.db")

# PostgreSQL
engine = create_async_engine(
    "postgres+aiopostgres://user:pass@localhost/dataagent"
)

# 初始化并执行迁移
manager = MigrationManager(engine)
await manager.init()
await manager.migrate()

# 回滚到指定版本
await manager.rollback("003")
```

### 4.4 手动执行 SQL

**SQLite**:
```bash
sqlite3 dataagent.db < sqlite_schema.sql
```

**PostgreSQL**:
```bash
postgres -u root -p dataagent < postgres_schema.sql
```

## 5. 多租户隔离

### 5.1 隔离策略

所有用户数据表都包含 `user_id` 字段，通过外键关联到 `users` 表：

```sql
-- 所有查询都必须包含 user_id 过滤
SELECT * FROM sessions WHERE user_id = 'alice';
SELECT * FROM mcp_servers WHERE user_id = 'alice';
```

### 5.2 级联删除

删除用户时，所有关联数据自动删除：

```sql
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
```

### 5.3 索引优化

所有表都在 `user_id` 上建立索引，确保多租户查询性能：

```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_mcp_servers_user_id ON mcp_servers(user_id);
```

## 6. 性能优化

### 6.1 SQLite 优化

```sql
-- 启用 WAL 模式
PRAGMA journal_mode = WAL;

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 优化缓存
PRAGMA cache_size = -64000;  -- 64MB
```

### 6.2 PostgreSQL 优化

```sql
-- 使用 InnoDB 引擎
ENGINE=InnoDB

-- UTF8MB4 字符集
DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

-- 审计日志分区
PARTITION BY RANGE (UNIX_TIMESTAMP(timestamp))
```

### 6.3 连接池配置

```python
# SQLite (单连接)
engine = create_async_engine(
    "sqlite+aiosqlite:///dataagent.db",
    pool_size=1,
    max_overflow=0,
)

# PostgreSQL (连接池)
engine = create_async_engine(
    "postgres+aiopostgres://user:pass@localhost/dataagent",
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)
```

## 7. 备份与恢复

### 7.1 SQLite 备份

```bash
# 在线备份
sqlite3 dataagent.db ".backup backup.db"

# 导出 SQL
sqlite3 dataagent.db .dump > backup.sql
```

### 7.2 PostgreSQL 备份

```bash
# 逻辑备份
postgresdump -u root -p dataagent > backup.sql

# 物理备份 (使用 pg_basebackup)
pg_basebackup --backup --target-dir=/backup/
```

## 8. 文件位置

| 文件 | 路径 |
|------|------|
| SQLAlchemy 模型 | `source/dataagent-core/dataagent_core/database/models.py` |
| 迁移管理器 | `source/dataagent-core/dataagent_core/database/migration.py` |
| SQLite Schema | `source/dataagent-core/dataagent_core/database/scripts/sqlite_schema.sql` |
| PostgreSQL Schema | `source/dataagent-core/dataagent_core/database/scripts/postgres_schema.sql` |

## 9. 总结

本数据库设计实现了：

✅ **完整的多租户支持** - 所有表通过 user_id 隔离  
✅ **双数据库支持** - SQLite3 和 PostgreSQL  
✅ **版本化迁移** - 支持增量升级和回滚  
✅ **安全审计** - 完整的操作日志  
✅ **性能优化** - 合理的索引和分区策略  
✅ **级联删除** - 用户删除时自动清理关联数据
