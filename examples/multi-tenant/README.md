# DataAgent 多租户用户知识库示例

本目录展示如何为不同用户配置专属的知识库、规则和 MCP 工具，实现个性化的 AI 助手。

## 📁 目录结构

```
examples/multi-tenant/
├── README.md                           # 本文档
├── user-knowledge-server-example.md    # Server 版本（REST API）
├── user-knowledge-cli-example.md       # CLI 版本（命令行）
└── filesystem-memory-example.md        # 文件系统记忆示例
```

## 🎯 核心概念

### 用户隔离机制

DataAgent 提供多层次的用户隔离：

| 层次 | Server 版本 | CLI 版本 |
|------|------------|----------|
| **工作空间** | `/workspace/{user_id}/` | `~/.deepagents/{agent}/` |
| **规则** | `~/.deepagents/users/{user_id}/rules/` | `~/.deepagents/{agent}/rules/` |
| **记忆** | `~/.deepagents/users/{user_id}/{agent}/` | `~/.deepagents/{agent}/agent.md` |
| **MCP** | 数据库隔离 (user_id) | `~/.deepagents/{agent}/mcp.json` |

### 知识检索流程

```
用户提问
    │
    ▼
┌─────────────────┐
│  规则触发       │  ← knowledge-retrieval 规则
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  搜索知识库     │  ← rgrep 搜索关键词
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  读取相关文件   │  ← read_file 获取内容
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  查询业务数据   │  ← MCP 工具调用（可选）
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  综合生成回答   │  ← 引用来源
└─────────────────┘
```

## 🚀 快速开始

### Server 版本

适用于多用户 SaaS 场景，通过 REST API 管理：

```bash
# 1. 创建用户规则
curl -X POST "http://localhost:8000/api/v1/users/alice/rules" \
  -H "X-User-ID: alice" \
  -d '{"name": "knowledge-retrieval", ...}'

# 2. 配置用户 MCP
curl -X POST "http://localhost:8000/api/v1/users/alice/mcp-servers" \
  -H "X-User-ID: alice" \
  -d '{"name": "filesystem", ...}'

# 3. 上传知识文件
curl -X PUT "http://localhost:8000/api/v1/users/alice/workspace/files/knowledge/faq.md" \
  -H "X-User-ID: alice" \
  -d '...'
```

详见：[user-knowledge-server-example.md](./user-knowledge-server-example.md)

### CLI 版本

适用于个人使用或本地开发：

```bash
# 1. 创建目录结构
mkdir -p ~/.deepagents/agent/{rules,knowledge}

# 2. 创建规则文件
cat > ~/.deepagents/agent/rules/knowledge-retrieval.md << 'EOF'
---
name: knowledge-retrieval
inclusion: always
---
## 知识检索规则
...
EOF

# 3. 创建知识文件
cat > ~/.deepagents/agent/knowledge/faq.md << 'EOF'
# FAQ
...
EOF

# 4. 启动 CLI
dataagent
```

详见：[user-knowledge-cli-example.md](./user-knowledge-cli-example.md)

## 📝 规则文件格式

```markdown
---
name: rule-name
description: 规则描述
inclusion: always|fileMatch|manual
fileMatchPattern: "*.sql"  # fileMatch 模式需要
priority: 90               # 1-100，越大优先级越高
---

# 规则内容

指导 AI 如何行为...
```

## 🔧 MCP 配置格式

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-xxx"],
      "env": {"KEY": "value"},
      "autoApprove": ["tool1", "tool2"]
    }
  }
}
```

## 🧪 隔离测试

DataAgent 提供完整的多租户隔离测试框架，用于验证安全性：

```bash
# 初始化测试用户
python scripts/init_test_users.py --verbose

# 运行所有隔离测试
make test-isolation

# 快速测试
make test-isolation-quick

# 生成测试报告
make test-isolation-report
```

测试覆盖：
- ✅ 文件系统隔离
- ✅ MCP 服务器隔离
- ✅ Rules 隔离
- ✅ Memory 隔离
- ✅ 路径遍历攻击防护
- ✅ 跨租户访问拒绝

详见：[多租户测试 Spec](../../.kiro/specs/multi-tenant-testing/)

## 📚 相关文档

- [Rules 使用示例](../rules/README.md)
- [MCP 配置示例](../mcp/README.md)
- [多租户部署指南](../../docs/multi-tenant/mcp-multi-tenant-deployment.md)
