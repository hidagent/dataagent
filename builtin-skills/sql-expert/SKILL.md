---
name: sql-expert
description: SQL 专家技能，帮助编写、优化和调试 SQL 查询
category: database
tags: [sql, database, query, optimization, mysql, postgresql]
---

# SQL 专家技能

## 概述

这个技能帮助你处理各种 SQL 相关任务：
- 编写复杂 SQL 查询
- 优化查询性能
- 数据库设计建议
- SQL 语法调试
- 跨数据库方言转换

## 支持的数据库

- MySQL / MariaDB
- PostgreSQL
- SQLite
- SQL Server
- Oracle

## 使用方法

### 1. 查询编写

根据需求编写 SQL 查询：

**简单查询**
```sql
-- 基本查询
SELECT column1, column2
FROM table_name
WHERE condition
ORDER BY column1 DESC
LIMIT 10;
```

**多表关联**
```sql
-- JOIN 查询
SELECT 
    u.name,
    o.order_id,
    o.total_amount
FROM users u
INNER JOIN orders o ON u.id = o.user_id
WHERE o.created_at >= '2024-01-01'
ORDER BY o.total_amount DESC;
```

**聚合分析**
```sql
-- 分组统计
SELECT 
    DATE(created_at) as date,
    COUNT(*) as order_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount
FROM orders
WHERE status = 'completed'
GROUP BY DATE(created_at)
HAVING COUNT(*) > 10
ORDER BY date DESC;
```

**窗口函数**
```sql
-- 排名和累计
SELECT 
    product_name,
    sales,
    RANK() OVER (ORDER BY sales DESC) as rank,
    SUM(sales) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING) as cumulative_sales
FROM product_sales;
```

### 2. 查询优化

优化慢查询的常用技巧：

**添加索引**
```sql
-- 为常用查询条件创建索引
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);

-- 复合索引
CREATE INDEX idx_products_category_price ON products(category_id, price);
```

**查询重写**
```sql
-- 避免 SELECT *
-- 不好
SELECT * FROM users WHERE id = 1;

-- 好
SELECT id, name, email FROM users WHERE id = 1;

-- 避免在 WHERE 中使用函数
-- 不好
SELECT * FROM orders WHERE YEAR(created_at) = 2024;

-- 好
SELECT * FROM orders WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
```

**使用 EXPLAIN 分析**
```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id;
```

### 3. 常用模式

**分页查询**
```sql
-- 偏移分页（适合小数据量）
SELECT * FROM products
ORDER BY id
LIMIT 20 OFFSET 40;

-- 游标分页（适合大数据量）
SELECT * FROM products
WHERE id > :last_id
ORDER BY id
LIMIT 20;
```

**递归查询（树形结构）**
```sql
-- PostgreSQL / MySQL 8+
WITH RECURSIVE category_tree AS (
    SELECT id, name, parent_id, 0 as level
    FROM categories
    WHERE parent_id IS NULL
    
    UNION ALL
    
    SELECT c.id, c.name, c.parent_id, ct.level + 1
    FROM categories c
    INNER JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree;
```

**UPSERT（插入或更新）**
```sql
-- MySQL
INSERT INTO users (id, name, email)
VALUES (1, 'John', 'john@example.com')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    email = VALUES(email);

-- PostgreSQL
INSERT INTO users (id, name, email)
VALUES (1, 'John', 'john@example.com')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email;
```

## 输出格式

SQL 建议应包含：

```markdown
## SQL 查询建议

### 查询语句
```sql
[优化后的 SQL]
```

### 说明
- 查询目的: [描述]
- 预期性能: [估计]

### 索引建议
```sql
[建议创建的索引]
```

### 注意事项
- [注意点1]
- [注意点2]
```

## 性能检查清单

- [ ] 是否使用了 SELECT *？
- [ ] WHERE 条件是否可以使用索引？
- [ ] JOIN 条件是否有索引？
- [ ] 是否有不必要的子查询？
- [ ] 是否可以使用 EXISTS 替代 IN？
- [ ] 分页是否使用了高效方式？
- [ ] 是否有 N+1 查询问题？
