---
name: dw-store-guide
description: DW_STORE 项目检索指引，指导 Agent 如何高效准确地检索项目信息
inclusion: always
priority: 80
---

# DW_STORE 项目检索指引

## 🎯 检索优先级原则

### 1. README.md优先原则

- **首要检索源**: 所有检索请求请优先通过读取README.md文件获取线索
- **权威文档**: README.md文件是经过精心整理的高质量文档，准确描述各目录作用及使用方法
- **检索路径**: 项目根目录 → 各子目录 → 具体功能模块的README.md

### 2. 检索层级策略

```
1. 项目根目录/README.md - 了解项目整体结构
2. FineBI/Reports/README.md - 优先检索FineBI报表和看板信息
3. 主要目录/README.md - 了解业务域分工
4. 具体业务/README.md - 了解详细功能
5. 相关SQL/代码文件 - 获取实现细节
```

### 2.1 FineBI报表检索特殊规则

**优先级最高**: 凡是涉及FineBI报表和看板的信息查询，都应优先从以下路径检索：

- `FineBI/Reports/` - 所有报表和看板的主目录
- `FineBI/Reports/README.md` - 报表总索引和分类指南
- `FineBI/Reports/{具体BG或域}/` - 各业务单元的报表目录

### 3. 信息准确性要求

- ✅ **可信来源**: README.md文档中的信息
- ✅ **可信来源**: 实际存在的代码文件内容  
- ❌ **禁止杜撰**: 如果在README.md和代码中都找不到相关信息，请明确说明"未找到相关信息"
- ❌ **禁止推测**: 不要基于假设或经验推测项目结构或功能

### 4. 典型检索流程示例

**查找某个业务功能时**:

```
1. 先读取 /README.md - 了解项目整体架构
2. 再读取 /FineBI/Datasets/README.md - 了解BI数据集分类
3. 然后读取 /FineBI/Datasets/公共业务包-抽取/{具体业务}/README.md
4. 最后查看具体的SQL文件
```

**查找开发规范时**:

```
1. 先读取 /README.md - 确认规范文档位置
2. 再读取 /Standards/README.md - 了解规范分类
3. 查看具体的规范文档
```

### 5. 特殊注意事项

- **历史归档**: 标记为"历史代码归档"的目录已过期，请优先参考当前活跃代码
- **多版本文件**: 如发现类似功能的多个版本，请参考README.md说明使用哪个版本
- **中文路径**: 项目使用中文目录名，这是正常的业务需求，不是错误

## 📚 核心README.md文件索引

### 项目层级

- `/README.md` - 项目总览和架构说明
- `/Utils/README.md` - 工具脚本使用指南

### 业务层级  

- `/FineBI/Datasets/README.md` - BI数据集总览
- `/DW/README.md` - 数据仓库说明
- `/Standards/README.md` - 规范标准索引

### 功能层级

- 各BG业务目录下的README.md - 具体业务功能说明
- 各域目录下的README.md - 跨BG通用功能说明

---

遵循以上原则，可以高效准确地获取项目信息，避免无效检索和错误推测。
