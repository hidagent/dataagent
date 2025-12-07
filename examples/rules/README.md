# DataAgent CLI Rules 使用示例

本目录展示如何在 DataAgent CLI 中配置和使用 Agent Rules 功能。

## 📁 目录结构

```
examples/rules/
├── README.md                    # 本文档
├── project-rules/               # 项目级规则示例（放在项目 .dataagent/rules/ 下）
│   └── dw-store-guide.md        # DW_STORE 项目检索指引规则
├── user-rules/                  # 用户级规则示例（放在 ~/.deepagents/{agent}/rules/ 下）
│   └── coding-standards.md      # 编码规范规则
└── global-rules/                # 全局规则示例（放在 ~/.deepagents/rules/ 下）
    └── security-practices.md    # 安全实践规则
```

## 🚀 快速开始

### 1. 在项目中配置规则

将规则文件放到项目的 `.dataagent/rules/` 目录下：

```bash
# 在你的 dw_store 项目根目录
mkdir -p .dataagent/rules

# 复制示例规则
cp examples/rules/project-rules/dw-store-guide.md .dataagent/rules/
```

### 2. 使用 CLI 命令管理规则

```bash
# 启动 DataAgent CLI
dataagent

# 查看所有规则
/rules list

# 查看特定规则内容
/rules show dw-store-guide

# 创建新规则
/rules create my-rule --scope project

# 验证规则文件
/rules validate

# 重新加载规则
/rules reload

# 查看规则冲突
/rules conflicts
```

### 3. 在对话中引用规则

```
# 手动引用规则（使用 @规则名）
你: @dw-store-guide 帮我查找 FineBI 报表相关的信息

# 规则会自动注入到系统提示词中
```

## 📝 规则文件格式

每个规则文件是一个 Markdown 文件，包含 YAML frontmatter：

```markdown
---
name: rule-name
description: 规则描述
inclusion: always|fileMatch|manual
fileMatchPattern: "*.sql"  # 仅 fileMatch 模式需要
priority: 50               # 1-100，越大优先级越高
---

# 规则内容

这里是规则的 Markdown 内容...
```

## 🔧 规则包含模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| `always` | 始终包含 | 通用规则，如项目指引 |
| `fileMatch` | 文件匹配时包含 | 特定文件类型规则，如 SQL 规范 |
| `manual` | 手动引用时包含 | 按需使用的规则，如安全检查清单 |

## 📂 规则作用域

| 作用域 | 存储位置 | 优先级 |
|--------|----------|--------|
| `global` | `~/.deepagents/rules/` | 最低 |
| `user` | `~/.deepagents/{agent}/rules/` | 中 |
| `project` | `{project}/.dataagent/rules/` | 最高 |

同名规则时，高优先级作用域的规则会覆盖低优先级的。
