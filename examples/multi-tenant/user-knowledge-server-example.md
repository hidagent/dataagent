# DataAgent Server 用户知识库配置示例

本示例展示如何通过 DataAgent Server REST API 为用户配置专属的知识库、规则和 MCP 工具，实现个性化的 AI 助手。

## 📋 场景描述

为用户 `alice` 配置：
1. **专属规则 (Rule)** - 指导 AI 如何检索知识、使用工具
2. **知识目录** - 存放用户常见问题、领域知识
3. **专属 MCP** - 用户特定的数据查询工具

## 📁 目录结构

```
~/.deepagents/
├── rules/                              # 全局规则
├── users/
│   └── alice/
│       ├── dataagent/
│       │   └── agent.md                # 用户记忆
│       └── rules/
│           └── knowledge-retrieval.md  # 用户专属规则

/var/dataagent/workspaces/              # 工作空间基础目录
└── alice/
    ├── knowledge/                      # 知识库目录
    │   ├── faq.md                      # 常见问题
    │   ├── best-practices.md           # 最佳实践
    │   └── domain/
    │       ├── product-guide.md        # 产品指南
    │       └── troubleshooting.md      # 故障排查
    └── context/
        └── project-overview.md         # 项目概览
```

## 🚀 配置步骤

### 步骤 1: 创建用户知识目录

```bash
# 创建知识库目录结构
curl -X POST "http://localhost:8000/api/v1/users/alice/workspace/directories" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice" \
  -d '{
    "path": "knowledge",
    "recursive": true
  }'

curl -X POST "http://localhost:8000/api/v1/users/alice/workspace/directories" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice" \
  -d '{
    "path": "knowledge/domain",
    "recursive": true
  }'
```

### 步骤 2: 上传知识文件

```bash
# 上传常见问题文档
curl -X PUT "http://localhost:8000/api/v1/users/alice/workspace/files/knowledge/faq.md" \
  -H "Content-Type: text/plain" \
  -H "X-User-ID: alice" \
  -d '# 常见问题 FAQ

## Q1: 如何查询报表数据？
使用 FineBI 报表系统，访问路径：数据中心 > 报表查询 > 选择报表类型

## Q2: 数据更新频率是多少？
- 实时数据：每5分钟更新
- 日报数据：每天凌晨2点更新
- 月报数据：每月1号凌晨更新

## Q3: 如何申请数据权限？
1. 登录 OA 系统
2. 提交数据权限申请单
3. 等待部门主管审批
'

# 上传最佳实践文档
curl -X PUT "http://localhost:8000/api/v1/users/alice/workspace/files/knowledge/best-practices.md" \
  -H "Content-Type: text/plain" \
  -H "X-User-ID: alice" \
  -d '# 最佳实践

## 数据查询优化
1. 优先使用索引字段作为查询条件
2. 避免 SELECT *，只查询需要的字段
3. 大数据量查询使用分页

## 报表设计规范
1. 标题清晰，包含数据范围和时间
2. 关键指标突出显示
3. 提供数据来源说明
'
```

### 步骤 3: 创建用户专属规则

```bash
# 创建知识检索规则
curl -X POST "http://localhost:8000/api/v1/users/alice/rules" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice" \
  -d '{
    "name": "knowledge-retrieval",
    "description": "指导AI如何检索用户知识库和使用工具",
    "scope": "user",
    "inclusion": "always",
    "priority": 90,
    "content": "## 知识检索规则\n\n当用户提问时，按以下流程获取上下文：\n\n### 1. 搜索知识库\n首先在用户知识目录搜索相关内容：\n```\nrgrep \"关键词\" /workspace/alice/knowledge/\n```\n\n### 2. 读取匹配文件\n找到相关文件后读取完整内容：\n```\nread_file \"/workspace/alice/knowledge/xxx.md\"\n```\n\n### 3. 查询业务数据\n如需查询实时数据，使用用户配置的 MCP 工具：\n- `alice-database`: 查询用户数据库\n- `alice-api`: 调用用户业务 API\n\n### 4. 综合回答\n结合知识库内容和查询结果，给出准确、有依据的回答。\n\n### 注意事项\n- 优先使用知识库中的信息\n- 引用来源时说明文件路径\n- 不确定时主动询问用户"
  }'
```

### 步骤 4: 配置用户专属 MCP 服务器

```bash
# 配置文件系统 MCP（限制在用户目录）
curl -X POST "http://localhost:8000/api/v1/users/alice/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice" \
  -d '{
    "name": "alice-filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/var/dataagent/workspaces/alice"],
    "autoApprove": ["read_file", "list_directory", "search_files"]
  }'

# 配置用户数据库 MCP
curl -X POST "http://localhost:8000/api/v1/users/alice/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice" \
  -d '{
    "name": "alice-database",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-postgres"],
    "env": {
      "POSTGRES_CONNECTION_STRING": "postgresql://alice:password@localhost:5432/alice_db"
    },
    "autoApprove": ["query"]
  }'

# 配置用户业务 API MCP（SSE 模式）
curl -X POST "http://localhost:8000/api/v1/users/alice/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice" \
  -d '{
    "name": "alice-api",
    "url": "http://internal-api.company.com/alice/mcp/sse",
    "transport": "sse",
    "headers": {
      "Authorization": "Bearer alice-api-token"
    }
  }'
```

### 步骤 5: 验证配置

```bash
# 查看用户规则
curl -X GET "http://localhost:8000/api/v1/users/alice/rules" \
  -H "X-User-ID: alice"

# 查看用户 MCP 服务器状态
curl -X GET "http://localhost:8000/api/v1/users/alice/mcp-servers" \
  -H "X-User-ID: alice"

# 查看用户工作空间信息
curl -X GET "http://localhost:8000/api/v1/users/alice/workspace" \
  -H "X-User-ID: alice"
```

## 📝 完整规则文件示例

### knowledge-retrieval.md

```markdown
---
name: knowledge-retrieval
description: 指导AI如何检索用户知识库和使用工具
inclusion: always
priority: 90
---

## 知识检索规则

当用户提问时，按以下流程获取上下文：

### 1. 搜索知识库

首先在用户知识目录搜索相关内容：

```bash
# 搜索关键词
rgrep "关键词" /workspace/alice/knowledge/

# 搜索特定类型文件
rgrep "关键词" /workspace/alice/knowledge/*.md
```

### 2. 读取匹配文件

找到相关文件后读取完整内容：

```bash
read_file "/workspace/alice/knowledge/faq.md"
read_file "/workspace/alice/knowledge/domain/product-guide.md"
```

### 3. 查询业务数据

如需查询实时数据，使用用户配置的 MCP 工具：

| 工具名称 | 用途 | 示例 |
|---------|------|------|
| `alice-filesystem` | 文件操作 | 读取、搜索知识文件 |
| `alice-database` | 数据库查询 | 查询业务数据 |
| `alice-api` | 业务 API | 调用内部服务 |

### 4. 综合回答

结合知识库内容和查询结果，给出准确、有依据的回答。

### 注意事项

- ✅ 优先使用知识库中的信息
- ✅ 引用来源时说明文件路径
- ✅ 不确定时主动询问用户
- ❌ 不要编造不存在的信息
- ❌ 不要访问用户目录以外的文件
```

## 🔄 使用流程

配置完成后，用户与 AI 对话时：

```
用户: 如何查询报表数据？

AI 内部流程:
1. [规则触发] knowledge-retrieval 规则生效
2. [搜索知识库] rgrep "报表" /workspace/alice/knowledge/
3. [读取文件] 发现 faq.md 包含相关内容
4. [生成回答] 基于知识库内容回答

AI: 根据知识库记录，查询报表数据的步骤如下：
使用 FineBI 报表系统，访问路径：数据中心 > 报表查询 > 选择报表类型
（来源：/workspace/alice/knowledge/faq.md）
```

## 🛡️ 安全说明

1. **路径隔离**: 每个用户只能访问自己的工作空间目录
2. **权限验证**: 所有 API 请求需要 `X-User-ID` 头部
3. **MCP 隔离**: 每个用户的 MCP 连接独立管理
4. **配额限制**: 可配置用户工作空间大小和文件数量限制

## 📚 相关 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/v1/users/{user_id}/rules` | GET/POST | 规则管理 |
| `/api/v1/users/{user_id}/rules/{name}` | GET/PUT/DELETE | 单个规则操作 |
| `/api/v1/users/{user_id}/mcp-servers` | GET/POST | MCP 服务器管理 |
| `/api/v1/users/{user_id}/workspace` | GET | 工作空间信息 |
| `/api/v1/users/{user_id}/memory` | GET/DELETE | 用户记忆管理 |
