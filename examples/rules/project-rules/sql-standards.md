---
name: sql-standards
description: SQL 文件编写规范，当处理 SQL 文件时自动应用
inclusion: fileMatch
fileMatchPattern: "*.sql"
priority: 70
---

# SQL 编写规范

## 命名规范

### 表命名
- 使用小写字母和下划线
- 格式: `{层级}_{业务域}_{表名}`
- 示例: `dwd_sales_order_detail`

### 字段命名
- 使用小写字母和下划线
- 主键: `id` 或 `{表名}_id`
- 外键: `{关联表}_id`
- 时间字段: `created_at`, `updated_at`

## 代码格式

### 关键字大写
```sql
SELECT
    column1,
    column2
FROM table_name
WHERE condition = 'value'
ORDER BY column1
```

### 缩进规则
- 使用 4 个空格缩进
- 每个主要子句独占一行
- 多个字段时每个字段独占一行

## 注释规范

### 文件头注释
```sql
/*
 * 文件名: xxx.sql
 * 描述: 简要说明
 * 作者: xxx
 * 创建日期: YYYY-MM-DD
 * 修改记录:
 *   - YYYY-MM-DD: 修改说明
 */
```

### 复杂逻辑注释
```sql
-- 计算销售额（含税）
SELECT amount * (1 + tax_rate) AS total_amount
```

## 性能建议

- 避免 `SELECT *`，明确列出需要的字段
- 大表查询必须有 WHERE 条件
- 合理使用索引字段作为查询条件
- 避免在 WHERE 子句中对字段进行函数操作
