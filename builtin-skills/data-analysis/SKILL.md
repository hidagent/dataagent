---
name: data-analysis
description: 数据分析技能，帮助分析数据、生成可视化图表和提供数据洞察
category: data
tags: [data, analysis, visualization, statistics, pandas]
---

# 数据分析技能

## 概述

这个技能帮助你进行专业的数据分析，包括：
- 数据探索和清洗
- 统计分析
- 数据可视化
- 趋势识别和预测
- 数据报告生成

## 使用方法

### 1. 数据探索

首先了解数据的基本情况：

```python
import pandas as pd

# 加载数据
df = pd.read_csv('data.csv')

# 基本信息
print(df.info())
print(df.describe())
print(df.head())

# 缺失值检查
print(df.isnull().sum())

# 数据类型检查
print(df.dtypes)
```

### 2. 数据清洗

处理常见的数据质量问题：

```python
# 处理缺失值
df.fillna(df.mean(), inplace=True)  # 数值型
df.fillna('Unknown', inplace=True)  # 分类型

# 处理重复值
df.drop_duplicates(inplace=True)

# 处理异常值
Q1 = df['column'].quantile(0.25)
Q3 = df['column'].quantile(0.75)
IQR = Q3 - Q1
df = df[(df['column'] >= Q1 - 1.5*IQR) & (df['column'] <= Q3 + 1.5*IQR)]
```

### 3. 统计分析

进行描述性和推断性统计：

```python
# 描述性统计
mean = df['column'].mean()
median = df['column'].median()
std = df['column'].std()

# 相关性分析
correlation = df.corr()

# 分组统计
grouped = df.groupby('category').agg({
    'value': ['mean', 'sum', 'count']
})
```

### 4. 数据可视化

使用 matplotlib 和 seaborn 创建图表：

```python
import matplotlib.pyplot as plt
import seaborn as sns

# 分布图
plt.figure(figsize=(10, 6))
sns.histplot(df['column'], kde=True)
plt.title('数据分布')
plt.savefig('distribution.png')

# 相关性热力图
plt.figure(figsize=(12, 8))
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
plt.title('相关性矩阵')
plt.savefig('correlation.png')

# 趋势图
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['value'])
plt.title('趋势分析')
plt.xlabel('日期')
plt.ylabel('数值')
plt.savefig('trend.png')
```

## 输出格式

分析报告应包含：

```markdown
## 数据分析报告

### 数据概览
- 数据集大小: X 行 × Y 列
- 时间范围: [开始日期] 至 [结束日期]
- 数据质量: 缺失值 X%，重复值 Y 条

### 关键发现

1. **发现一**: [描述]
   - 数据支持: [具体数据]
   - 图表: [图表引用]

2. **发现二**: [描述]
   - 数据支持: [具体数据]

### 统计摘要

| 指标 | 数值 |
|------|------|
| 平均值 | X |
| 中位数 | Y |
| 标准差 | Z |

### 建议

1. [基于数据的建议一]
2. [基于数据的建议二]

### 附录
- 完整代码
- 原始数据链接
```

## 常用分析模板

### 销售数据分析
- 销售趋势（按日/周/月）
- 产品销售排名
- 客户分布分析
- 季节性分析

### 用户行为分析
- 用户活跃度
- 留存率分析
- 转化漏斗
- 用户分群

### 财务数据分析
- 收入/支出趋势
- 成本结构分析
- 利润率分析
- 预算对比
