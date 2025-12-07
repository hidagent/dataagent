---
name: security-practices
description: 安全实践检查清单，需要时手动引用 @security-practices
inclusion: manual
priority: 90
---

# 安全实践检查清单

## 🔐 敏感信息处理

### 禁止硬编码
- ❌ 密码、API Key、Token
- ❌ 数据库连接字符串
- ❌ 私钥、证书
- ✅ 使用环境变量或配置管理

### 日志安全
- 不记录敏感信息到日志
- 对敏感字段进行脱敏处理
- 生产环境关闭调试日志

## 🛡️ 输入验证

### SQL 注入防护
```python
# ❌ 危险
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### XSS 防护
- 对用户输入进行转义
- 使用 Content-Security-Policy
- 避免使用 innerHTML

## 🔑 认证授权

### 密码安全
- 使用 bcrypt/argon2 哈希
- 强制密码复杂度
- 实现账户锁定机制

### 会话管理
- 使用安全的会话 ID
- 设置合理的过期时间
- 支持会话撤销

## 📋 代码审查要点

在提交代码前检查：

- [ ] 没有硬编码的敏感信息
- [ ] 所有用户输入都经过验证
- [ ] 使用参数化查询
- [ ] 错误信息不泄露系统细节
- [ ] 日志不包含敏感数据
- [ ] 依赖包没有已知漏洞
