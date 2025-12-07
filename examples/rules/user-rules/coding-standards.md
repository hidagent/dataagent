---
name: coding-standards
description: 通用编码规范，适用于所有项目
inclusion: always
priority: 50
---

# 通用编码规范

## 代码风格

### Python
- 遵循 PEP 8 规范
- 使用 4 空格缩进
- 行长度不超过 88 字符（Black 默认）
- 使用类型注解

### TypeScript/JavaScript
- 使用 ESLint + Prettier
- 优先使用 `const`，其次 `let`
- 使用箭头函数
- 使用 async/await 而非 Promise 链

## 命名规范

| 类型 | Python | TypeScript |
|------|--------|------------|
| 变量 | snake_case | camelCase |
| 函数 | snake_case | camelCase |
| 类 | PascalCase | PascalCase |
| 常量 | UPPER_SNAKE | UPPER_SNAKE |

## 注释原则

- 解释"为什么"而非"是什么"
- 复杂逻辑必须有注释
- 公共 API 必须有文档字符串
- 避免无意义的注释

## Git 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关
