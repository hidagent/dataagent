# 多租户隔离测试框架设计文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Test Framework                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Test Users  │  │  Test Data   │  │  Isolation Verifier  │  │
│  │  - test_alice│  │  - SQLite DB │  │  - MCP Tests         │  │
│  │  - test_bob  │  │  - Files     │  │  - Rules Tests       │  │
│  └──────────────┘  │  - Rules     │  │  - FS Tests          │  │
│                    │  - Skills    │  │  - Skills Tests      │  │
│                    └──────────────┘  │  - Memory Tests      │  │
│                                      └──────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Security Audit Logger                  │  │
│  │  - Cross-tenant access attempts                          │  │
│  │  - Violation detection                                    │  │
│  │  - Report generation                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 测试用户设计

### 2.1 用户配置

| 属性 | test_alice | test_bob |
|------|------------|----------|
| user_id | `test_alice` | `test_bob` |
| display_name | Alice Test | Bob Test |
| department | Engineering | Sales |
| role | Developer | Analyst |
| workspace | `/tmp/dataagent-test/workspaces/test_alice` | `/tmp/dataagent-test/workspaces/test_bob` |
| rules_dir | `~/.dataagent-test/users/test_alice/rules` | `~/.dataagent-test/users/test_bob/rules` |
| memory_dir | `~/.dataagent-test/users/test_alice/agent` | `~/.dataagent-test/users/test_bob/agent` |

### 2.2 用户资源清单

#### test_alice 资源

```
test_alice/
├── workspace/
│   └── knowledge/
│       ├── alice-faq.md           # 包含 "ALICE_SECRET_001"
│       ├── alice-guide.md         # 包含 "ALICE_SECRET_002"
│       └── alice-notes.md         # 包含 "ALICE_SECRET_003"
├── rules/
│   ├── alice-coding-rule.md       # 包含 "ALICE_RULE_MARKER"
│   ├── alice-review-rule.md
│   └── alice-security-rule.md
├── mcp/
│   ├── alice-database (SQLite)    # 表: alice_data, 包含 alice 专属数据
│   └── alice-api (Mock)           # 返回 alice 专属响应
├── skills/
│   ├── alice-report-skill/
│   └── alice-analysis-skill/
└── memory/
    └── agent.md                   # 包含 "ALICE_MEMORY_MARKER"
```

#### test_bob 资源

```
test_bob/
├── workspace/
│   └── knowledge/
│       ├── bob-faq.md             # 包含 "BOB_SECRET_001"
│       ├── bob-guide.md           # 包含 "BOB_SECRET_002"
│       └── bob-notes.md           # 包含 "BOB_SECRET_003"
├── rules/
│   ├── bob-sales-rule.md          # 包含 "BOB_RULE_MARKER"
│   ├── bob-crm-rule.md
│   └── bob-report-rule.md
├── mcp/
│   ├── bob-database (SQLite)      # 表: bob_data, 包含 bob 专属数据
│   └── bob-api (Mock)             # 返回 bob 专属响应
├── skills/
│   ├── bob-sales-skill/
│   └── bob-forecast-skill/
└── memory/
    └── agent.md                   # 包含 "BOB_MEMORY_MARKER"
```

## 3. 测试数据设计

### 3.1 SQLite 数据库结构

```sql
-- 测试数据库: test_isolation.db

-- 用户表
CREATE TABLE test_users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    department TEXT,
    role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alice 的数据表
CREATE TABLE alice_data (
    id INTEGER PRIMARY KEY,
    content TEXT,
    secret_marker TEXT,  -- 用于验证隔离
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bob 的数据表
CREATE TABLE bob_data (
    id INTEGER PRIMARY KEY,
    content TEXT,
    secret_marker TEXT,  -- 用于验证隔离
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MCP 配置表
CREATE TABLE mcp_configs (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    server_name TEXT,
    config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, server_name)
);

-- 规则表
CREATE TABLE rules (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    rule_name TEXT,
    rule_content TEXT,
    scope TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, rule_name)
);

-- 安全审计日志表
CREATE TABLE security_audit_log (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    requesting_user TEXT,
    target_user TEXT,
    resource_type TEXT,  -- mcp, rule, file, skill, memory
    resource_id TEXT,
    action TEXT,         -- read, write, delete, execute
    result TEXT,         -- allowed, denied
    details TEXT
);
```

### 3.2 初始测试数据

```sql
-- 插入测试用户
INSERT INTO test_users VALUES ('test_alice', 'Alice Test', 'Engineering', 'Developer', CURRENT_TIMESTAMP);
INSERT INTO test_users VALUES ('test_bob', 'Bob Test', 'Sales', 'Analyst', CURRENT_TIMESTAMP);

-- Alice 的数据
INSERT INTO alice_data (content, secret_marker) VALUES 
    ('Alice project report Q4', 'ALICE_DB_SECRET_001'),
    ('Alice code review notes', 'ALICE_DB_SECRET_002'),
    ('Alice architecture design', 'ALICE_DB_SECRET_003');

-- Bob 的数据
INSERT INTO bob_data (content, secret_marker) VALUES 
    ('Bob sales forecast 2024', 'BOB_DB_SECRET_001'),
    ('Bob customer analysis', 'BOB_DB_SECRET_002'),
    ('Bob revenue report', 'BOB_DB_SECRET_003');

-- MCP 配置
INSERT INTO mcp_configs (user_id, server_name, config_json) VALUES 
    ('test_alice', 'alice-database', '{"type": "sqlite", "path": "alice.db"}'),
    ('test_alice', 'alice-api', '{"type": "http", "url": "http://localhost:9001/alice"}'),
    ('test_bob', 'bob-database', '{"type": "sqlite", "path": "bob.db"}'),
    ('test_bob', 'bob-api', '{"type": "http", "url": "http://localhost:9002/bob"}');
```

## 4. 隔离测试设计

### 4.1 测试矩阵

| 测试类别 | 正向测试 (应成功) | 负向测试 (应失败) |
|---------|------------------|------------------|
| **MCP** | Alice 访问 alice-database | Alice 访问 bob-database |
| **Rules** | Alice 读取 alice-coding-rule | Alice 读取 bob-sales-rule |
| **Files** | Alice 读取 alice-faq.md | Alice 读取 bob-faq.md |
| **Skills** | Alice 执行 alice-report-skill | Alice 执行 bob-sales-skill |
| **Memory** | Alice 读取自己的 agent.md | Alice 读取 Bob 的 agent.md |

### 4.2 测试用例设计

#### MCP 隔离测试

```python
class TestMCPIsolation:
    """MCP 服务器隔离测试"""
    
    def test_alice_can_list_own_mcp_servers(self):
        """Alice 可以列出自己的 MCP 服务器"""
        # 预期: 返回 alice-database, alice-api
        
    def test_alice_cannot_list_bob_mcp_servers(self):
        """Alice 不能看到 Bob 的 MCP 服务器"""
        # 预期: 列表中不包含 bob-database, bob-api
        
    def test_alice_can_call_own_mcp_tool(self):
        """Alice 可以调用自己的 MCP 工具"""
        # 预期: 成功执行，返回 alice 数据
        
    def test_alice_cannot_call_bob_mcp_tool(self):
        """Alice 不能调用 Bob 的 MCP 工具"""
        # 预期: 403 Forbidden 或 404 Not Found
        
    def test_mcp_tool_result_contains_only_user_data(self):
        """MCP 工具结果只包含用户自己的数据"""
        # 预期: 结果包含 ALICE_DB_SECRET，不包含 BOB_DB_SECRET
```

#### Rules 隔离测试

```python
class TestRulesIsolation:
    """规则隔离测试"""
    
    def test_alice_can_list_own_rules(self):
        """Alice 可以列出自己的规则"""
        # 预期: 返回 alice-coding-rule 等
        
    def test_alice_cannot_see_bob_rules(self):
        """Alice 不能看到 Bob 的规则"""
        # 预期: 列表中不包含 bob-sales-rule
        
    def test_alice_can_read_own_rule_content(self):
        """Alice 可以读取自己规则的内容"""
        # 预期: 内容包含 ALICE_RULE_MARKER
        
    def test_alice_cannot_read_bob_rule(self):
        """Alice 不能读取 Bob 的规则"""
        # 预期: 404 Not Found
        
    def test_alice_cannot_modify_bob_rule(self):
        """Alice 不能修改 Bob 的规则"""
        # 预期: 403 Forbidden
        
    def test_rule_trigger_is_user_scoped(self):
        """规则触发只影响当前用户"""
        # 预期: Alice 的规则不会在 Bob 的会话中触发
```

#### 文件系统隔离测试

```python
class TestFilesystemIsolation:
    """文件系统隔离测试"""
    
    def test_alice_can_read_own_files(self):
        """Alice 可以读取自己的文件"""
        # 预期: 成功读取，内容包含 ALICE_SECRET
        
    def test_alice_cannot_read_bob_files(self):
        """Alice 不能读取 Bob 的文件"""
        # 预期: 403 Forbidden 或路径不存在
        
    def test_path_traversal_blocked(self):
        """路径遍历攻击被阻止"""
        # 尝试: ../test_bob/knowledge/bob-faq.md
        # 预期: 拒绝访问
        
    def test_alice_search_only_returns_own_files(self):
        """Alice 搜索只返回自己的文件"""
        # 搜索: "SECRET"
        # 预期: 只返回 ALICE_SECRET，不返回 BOB_SECRET
        
    def test_alice_cannot_write_to_bob_workspace(self):
        """Alice 不能写入 Bob 的工作空间"""
        # 预期: 403 Forbidden
```

#### Skills 隔离测试

```python
class TestSkillsIsolation:
    """Skills 隔离测试"""
    
    def test_alice_can_list_own_skills(self):
        """Alice 可以列出自己的 Skills"""
        # 预期: 返回 alice-report-skill 等
        
    def test_alice_cannot_see_bob_skills(self):
        """Alice 不能看到 Bob 的 Skills"""
        # 预期: 列表中不包含 bob-sales-skill
        
    def test_alice_can_execute_own_skill(self):
        """Alice 可以执行自己的 Skill"""
        # 预期: 成功执行
        
    def test_alice_cannot_execute_bob_skill(self):
        """Alice 不能执行 Bob 的 Skill"""
        # 预期: 404 Not Found
        
    def test_skill_execution_uses_user_context(self):
        """Skill 执行使用用户自己的上下文"""
        # 预期: Skill 只能访问 Alice 的资源
```

#### Memory 隔离测试

```python
class TestMemoryIsolation:
    """Memory/Knowledge 隔离测试"""
    
    def test_alice_can_read_own_memory(self):
        """Alice 可以读取自己的记忆"""
        # 预期: 内容包含 ALICE_MEMORY_MARKER
        
    def test_alice_cannot_read_bob_memory(self):
        """Alice 不能读取 Bob 的记忆"""
        # 预期: 403 Forbidden
        
    def test_alice_can_update_own_memory(self):
        """Alice 可以更新自己的记忆"""
        # 预期: 成功更新
        
    def test_alice_cannot_update_bob_memory(self):
        """Alice 不能更新 Bob 的记忆"""
        # 预期: 403 Forbidden
        
    def test_memory_clear_only_affects_own(self):
        """清除记忆只影响自己"""
        # Alice 清除记忆后，Bob 的记忆不受影响
```

## 5. 安全审计设计

### 5.1 审计事件

```python
@dataclass
class SecurityAuditEvent:
    timestamp: datetime
    requesting_user: str
    target_user: str
    resource_type: str  # mcp, rule, file, skill, memory
    resource_id: str
    action: str         # read, write, delete, execute, list
    result: str         # allowed, denied
    details: dict
```

### 5.2 审计日志格式

```json
{
  "timestamp": "2024-12-07T10:30:00Z",
  "requesting_user": "test_alice",
  "target_user": "test_bob",
  "resource_type": "file",
  "resource_id": "/workspace/test_bob/knowledge/bob-faq.md",
  "action": "read",
  "result": "denied",
  "details": {
    "error": "PathEscapeError",
    "message": "Access denied: path outside user workspace"
  }
}
```

## 6. 测试报告设计

### 6.1 报告结构

```
Multi-Tenant Isolation Test Report
==================================
Date: 2024-12-07 10:30:00
Duration: 45 seconds

Summary
-------
Total Tests: 50
Passed: 50
Failed: 0
Security Violations: 0

Results by Category
-------------------
✅ MCP Isolation: 10/10 passed
✅ Rules Isolation: 10/10 passed
✅ Filesystem Isolation: 10/10 passed
✅ Skills Isolation: 10/10 passed
✅ Memory Isolation: 10/10 passed

Security Audit Summary
----------------------
Cross-tenant access attempts: 25
All attempts correctly denied: ✅

Detailed Results
----------------
[详细测试结果...]
```

## 7. 文件结构

```
source/dataagent-server/
├── tests/
│   └── test_multi_tenant/
│       ├── __init__.py
│       ├── conftest.py              # 测试 fixtures
│       ├── test_data/
│       │   ├── init_test_db.sql     # 数据库初始化脚本
│       │   ├── alice/               # Alice 测试文件
│       │   └── bob/                 # Bob 测试文件
│       ├── test_mcp_isolation.py
│       ├── test_rules_isolation.py
│       ├── test_filesystem_isolation.py
│       ├── test_skills_isolation.py
│       ├── test_memory_isolation.py
│       └── test_security_audit.py

scripts/
├── init_test_users.py               # 初始化测试用户脚本
├── run_isolation_tests.sh           # 运行隔离测试脚本
└── generate_test_report.py          # 生成测试报告脚本
```

## 8. 实现优先级

| 优先级 | 组件 | 说明 |
|--------|------|------|
| P0 | 测试用户初始化 | 基础设施 |
| P0 | 文件系统隔离测试 | 最基本的安全要求 |
| P0 | MCP 隔离测试 | 核心功能隔离 |
| P1 | Rules 隔离测试 | 配置隔离 |
| P1 | Memory 隔离测试 | 数据隔离 |
| P2 | Skills 隔离测试 | 扩展功能隔离 |
| P2 | 安全审计日志 | 合规要求 |
| P3 | 测试报告生成 | 可视化 |
