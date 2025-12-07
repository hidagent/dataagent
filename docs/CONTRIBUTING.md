# 贡献指南

## Commit Message 规范

本项目使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范来管理 commit message，以便自动化版本管理。

### 格式

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### 类型 (type)

| 类型 | 说明 | 版本影响 |
|------|------|----------|
| `feat` | 新功能 | Minor (0.1.0 → 0.2.0) |
| `fix` | Bug 修复 | Patch (0.1.0 → 0.1.1) |
| `perf` | 性能优化 | Patch |
| `refactor` | 代码重构 | Patch |
| `build` | 构建系统变更 | Patch |
| `docs` | 文档更新 | 无 |
| `style` | 代码风格 | 无 |
| `test` | 测试相关 | 无 |
| `chore` | 杂项维护 | 无 |
| `ci` | CI/CD 配置 | 无 |

### 作用域 (scope)

可选，用于指明影响的模块：

- `core` - dataagent-core
- `cli` - dataagent-cli
- `server` - dataagent-server
- `harbor` - dataagent-harbor

### Breaking Changes

如果是破坏性变更，需要在类型后加 `!` 或在 footer 中添加 `BREAKING CHANGE:`：

```
feat(server)!: change API response format

BREAKING CHANGE: The response format has changed from array to object.
```

这会触发 Major 版本更新 (0.1.0 → 1.0.0)。

### 示例

```bash
# 新功能
feat(server): add user authentication endpoint
feat(cli): support multiple output formats

# Bug 修复
fix(core): resolve memory leak in agent execution
fix(server): handle empty request body

# 文档
docs: update API reference
docs(cli): add usage examples

# 重构
refactor(core): simplify event handling logic

# 测试
test(server): add multi-tenant isolation tests

# 杂项
chore: update dependencies
chore(ci): add version auto-bump
```

## 版本管理

### 查看当前版本

```bash
python scripts/version_manager.py show-all
```

### 分析版本变更

```bash
# 分析某个模块的 commits，显示建议的版本变更
python scripts/version_manager.py analyze dataagent-server
```

### 手动更新版本

```bash
# 更新 patch 版本
python scripts/version_manager.py bump dataagent-server --type patch

# 更新 minor 版本
python scripts/version_manager.py bump dataagent-server --type minor

# 预览变更（不实际修改）
python scripts/version_manager.py bump dataagent-server --type minor --dry-run
```

### 自动更新版本

```bash
# 根据 commits 自动分析并更新版本
python scripts/version_manager.py auto-bump dataagent-server
```

## CI/CD 流程

1. **提交代码** - 使用规范的 commit message
2. **创建 MR** - CI 会自动分析版本变更建议
3. **合并到主分支** - 可手动触发版本更新
4. **发布** - 手动触发 release 流程

## 开发流程

1. 创建功能分支
2. 开发并提交（使用规范的 commit message）
3. 创建 Merge Request
4. 代码审查
5. 合并到主分支
6. 版本自动/手动更新
