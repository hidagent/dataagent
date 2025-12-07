# DataAgent CLI 用户知识库配置示例

本示例展示如何通过 DataAgent CLI 为用户配置专属的知识库、规则和 MCP 工具，实现个性化的 AI 助手。

## 📋 场景描述

为用户配置：
1. **专属规则 (Rule)** - 指导 AI 如何检索知识、使用工具
2. **知识目录** - 存放用户常见问题、领域知识
3. **专属 MCP** - 用户特定的数据查询工具

## 📁 目录结构

```
~/.deepagents/
├── rules/                          # 全局规则
│   └── security-practices.md
├── agent/                          # 默认 agent 目录
│   ├── agent.md                    # 用户记忆
│   ├── mcp.json                    # MCP 配置
│   ├── rules/                      # 用户规则
│   │   └── knowledge-retrieval.md
│   └── knowledge/                  # 知识库目录
│       ├── faq.md
│       ├── best-practices.md
│       └── domain/
│           ├── product-guide.md
│           └── troubleshooting.md
└── project/                        # 项目级配置（可选）
    └── .dataagent/
        └── rules/
```

## 🚀 配置步骤

### 步骤 1: 创建目录结构

```bash
# 创建 agent 目录和知识库
mkdir -p ~/.deepagents/agent/rules
mkdir -p ~/.deepagents/agent/knowledge/domain

# 或使用 dataagent 命令
dataagent init
```

### 步骤 2: 创建知识文件

#### ~/.deepagents/agent/knowledge/faq.md

```bash
cat > ~/.deepagents/agent/knowledge/faq.md << 'EOF'
# 常见问题 FAQ

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

## Q4: 报表导出格式支持哪些？
- Excel (.xlsx)
- CSV (.csv)
- PDF (.pdf)
- 图片 (.png)

## Q5: 数据异常如何反馈？
联系数据团队：data-support@company.com
或在企业微信群"数据支持群"反馈
EOF
```

#### ~/.deepagents/agent/knowledge/best-practices.md

```bash
cat > ~/.deepagents/agent/knowledge/best-practices.md << 'EOF'
# 最佳实践

## 数据查询优化

### SQL 查询规范
1. 优先使用索引字段作为查询条件
2. 避免 SELECT *，只查询需要的字段
3. 大数据量查询使用分页（LIMIT/OFFSET）
4. 复杂查询先在测试环境验证

### 查询示例
```sql
-- 推荐写法
SELECT user_id, user_name, created_at
FROM users
WHERE department = 'sales'
  AND created_at >= '2024-01-01'
LIMIT 100;

-- 避免写法
SELECT * FROM users;
```

## 报表设计规范

1. **标题清晰**：包含数据范围和时间
2. **关键指标突出**：使用颜色或加粗
3. **数据来源说明**：注明数据表和更新时间
4. **图表选择**：
   - 趋势数据用折线图
   - 占比数据用饼图
   - 对比数据用柱状图

## 数据安全规范

1. 不在公共场所展示敏感数据
2. 导出数据需脱敏处理
3. 定期清理本地数据文件
4. 不通过非安全渠道传输数据
EOF
```

#### ~/.deepagents/agent/knowledge/domain/product-guide.md

```bash
cat > ~/.deepagents/agent/knowledge/domain/product-guide.md << 'EOF'
# 产品使用指南

## FineBI 报表系统

### 登录方式
- 地址：https://bi.company.com
- 账号：企业邮箱前缀
- 密码：统一认证密码

### 功能模块
1. **数据中心**：查看和导出报表
2. **自助分析**：创建自定义报表
3. **仪表板**：查看实时数据大屏
4. **数据集**：管理数据源

### 常用操作
- 筛选数据：点击筛选器图标
- 导出报表：右上角"导出"按钮
- 分享报表：点击"分享"生成链接
- 订阅报表：设置定时邮件推送

## 数据仓库 (DW_STORE)

### 表命名规范
- `dwd_*`：明细层数据
- `dws_*`：汇总层数据
- `ads_*`：应用层数据
- `dim_*`：维度表

### 常用表说明
| 表名 | 说明 | 更新频率 |
|------|------|----------|
| dwd_order_detail | 订单明细 | 实时 |
| dws_sales_daily | 日销售汇总 | T+1 |
| ads_user_profile | 用户画像 | 周更新 |
| dim_product | 产品维度 | 日更新 |
EOF
```

### 步骤 3: 创建知识检索规则

#### ~/.deepagents/agent/rules/knowledge-retrieval.md

```bash
cat > ~/.deepagents/agent/rules/knowledge-retrieval.md << 'EOF'
---
name: knowledge-retrieval
description: 指导AI如何检索用户知识库和使用工具
inclusion: always
priority: 90
---

## 知识检索规则

当用户提问时，按以下流程获取上下文：

### 1. 搜索知识库

首先在知识目录搜索相关内容：

```bash
# 搜索关键词
rgrep "关键词" ~/.deepagents/agent/knowledge/

# 列出知识文件
ls ~/.deepagents/agent/knowledge/
```

### 2. 读取匹配文件

找到相关文件后读取完整内容：

```bash
read_file '~/.deepagents/agent/knowledge/faq.md'
read_file '~/.deepagents/agent/knowledge/domain/product-guide.md'
```

### 3. 查询业务数据

如需查询实时数据，使用配置的 MCP 工具：

| 工具名称 | 用途 | 示例 |
|---------|------|------|
| `filesystem` | 文件操作 | 读取、搜索知识文件 |
| `database` | 数据库查询 | 查询业务数据 |
| `search` | 全文搜索 | 搜索文档内容 |

### 4. 综合回答

结合知识库内容和查询结果，给出准确、有依据的回答。

### 回答格式

```
根据知识库记录：
[回答内容]

来源：[文件路径]
```

### 注意事项

- ✅ 优先使用知识库中的信息
- ✅ 引用来源时说明文件路径
- ✅ 不确定时主动询问用户
- ❌ 不要编造不存在的信息
- ❌ 不要泄露敏感配置信息
EOF
```

### 步骤 4: 配置 MCP 服务器

#### ~/.deepagents/agent/mcp.json

```bash
cat > ~/.deepagents/agent/mcp.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", 
               "~/.deepagents/agent/knowledge",
               "~/Documents"],
      "autoApprove": ["read_file", "list_directory", "search_files"]
    },
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost:5432/mydb"
      },
      "autoApprove": ["query"]
    },
    "search": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
EOF
```

### 步骤 5: 配置用户记忆 (可选)

#### ~/.deepagents/agent/agent.md

```bash
cat > ~/.deepagents/agent/agent.md << 'EOF'
# 用户偏好

## 身份信息
- 部门：数据分析部
- 角色：数据分析师
- 常用工具：FineBI, SQL, Python

## 工作习惯
- 偏好简洁的回答
- 需要时提供 SQL 示例
- 报表相关问题优先查看 product-guide.md

## 常用查询
- 日销售数据：dws_sales_daily
- 用户信息：ads_user_profile
- 产品信息：dim_product

## 注意事项
- 数据导出需要脱敏
- 敏感数据不要在回答中展示完整值
EOF
```

## 🎯 使用 CLI 命令

### 启动 DataAgent

```bash
# 使用默认 agent
dataagent

# 指定 agent 名称
dataagent --agent my-agent

# 指定 MCP 配置
dataagent --mcp-config ~/.deepagents/agent/mcp.json
```

### 规则管理命令

```bash
# 在 dataagent 交互界面中

# 查看所有规则
/rules list

# 查看特定规则
/rules show knowledge-retrieval

# 创建新规则
/rules create my-rule --scope user

# 验证规则
/rules validate

# 重新加载规则
/rules reload

# 查看规则冲突
/rules conflicts
```

### MCP 管理命令

```bash
# 查看 MCP 服务器状态
/mcp

# 重新加载 MCP 配置
/mcp reload

# 连接特定服务器
/mcp connect filesystem

# 断开服务器
/mcp disconnect database
```

### 知识库操作

```bash
# 在对话中直接使用

# 搜索知识库
你: 帮我搜索知识库中关于"报表"的内容

# AI 会执行:
# rgrep "报表" ~/.deepagents/agent/knowledge/

# 读取特定文件
你: 读取 FAQ 文件

# AI 会执行:
# read_file '~/.deepagents/agent/knowledge/faq.md'
```

## 🔄 使用流程示例

```
$ dataagent

DataAgent CLI v1.0.0
已加载规则: knowledge-retrieval, security-practices
已连接 MCP: filesystem, database

> 如何查询报表数据？

[知识检索] 搜索关键词: 报表
[读取文件] ~/.deepagents/agent/knowledge/faq.md
[生成回答]

根据知识库记录，查询报表数据的步骤如下：

使用 FineBI 报表系统，访问路径：
1. 数据中心 > 报表查询 > 选择报表类型

登录信息：
- 地址：https://bi.company.com
- 账号：企业邮箱前缀

来源：~/.deepagents/agent/knowledge/faq.md

> 帮我查询昨天的销售数据

[知识检索] 搜索关键词: 销售
[读取文件] ~/.deepagents/agent/knowledge/domain/product-guide.md
[MCP调用] database.query

根据知识库，日销售数据存储在 dws_sales_daily 表。

执行查询：
```sql
SELECT * FROM dws_sales_daily 
WHERE dt = CURRENT_DATE - 1;
```

[查询结果]
| 日期 | 销售额 | 订单数 |
|------|--------|--------|
| 2024-12-06 | 125,000 | 1,234 |

来源：~/.deepagents/agent/knowledge/domain/product-guide.md
```

## 📝 快速配置脚本

将以下脚本保存为 `setup-knowledge.sh` 并执行：

```bash
#!/bin/bash
# setup-knowledge.sh - 一键配置用户知识库

set -e

AGENT_DIR=~/.deepagents/agent
KNOWLEDGE_DIR=$AGENT_DIR/knowledge
RULES_DIR=$AGENT_DIR/rules

echo "📁 创建目录结构..."
mkdir -p $KNOWLEDGE_DIR/domain
mkdir -p $RULES_DIR

echo "📝 创建知识文件..."
# 创建 FAQ
cat > $KNOWLEDGE_DIR/faq.md << 'EOF'
# 常见问题 FAQ

## Q1: 示例问题1
示例回答1

## Q2: 示例问题2
示例回答2
EOF

# 创建最佳实践
cat > $KNOWLEDGE_DIR/best-practices.md << 'EOF'
# 最佳实践

## 规范1
内容...

## 规范2
内容...
EOF

echo "📋 创建规则文件..."
cat > $RULES_DIR/knowledge-retrieval.md << 'EOF'
---
name: knowledge-retrieval
description: 知识检索规则
inclusion: always
priority: 90
---

## 知识检索规则

当用户提问时：
1. 搜索 ~/.deepagents/agent/knowledge/ 目录
2. 读取相关文件
3. 综合回答
EOF

echo "⚙️ 创建 MCP 配置..."
cat > $AGENT_DIR/mcp.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/.deepagents/agent/knowledge"],
      "autoApprove": ["read_file", "list_directory"]
    }
  }
}
EOF

echo "✅ 配置完成！"
echo ""
echo "目录结构："
tree $AGENT_DIR 2>/dev/null || ls -la $AGENT_DIR

echo ""
echo "启动 DataAgent："
echo "  dataagent"
```

## 🛡️ 安全建议

1. **敏感信息**：不要在知识文件中存储密码、密钥等
2. **MCP 配置**：数据库连接串使用环境变量
3. **文件权限**：确保 ~/.deepagents 目录权限为 700
4. **定期清理**：清理不再需要的知识文件

```bash
# 设置目录权限
chmod 700 ~/.deepagents

# 使用环境变量配置敏感信息
export POSTGRES_CONNECTION_STRING="postgresql://..."
```

## 📚 相关命令

| 命令 | 说明 |
|------|------|
| `dataagent` | 启动 CLI |
| `dataagent --help` | 查看帮助 |
| `/rules list` | 列出规则 |
| `/rules reload` | 重载规则 |
| `/mcp` | 查看 MCP 状态 |
| `/memory` | 查看用户记忆 |
| `/clear` | 清除对话历史 |
| `/exit` | 退出 CLI |
