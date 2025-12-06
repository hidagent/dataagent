# DataAgent Harbor

DataAgent Harbor 是 DataAgent Server 的测试和评估框架，支持批量压测、结果统计和 LangSmith 追踪。

## 功能特性

- **批量压测**: 支持从测试问题集批量发送请求到 DataAgent Server
- **结果统计**: 收集成功/失败率、响应时间、是否符合预期等指标
- **并发测试**: 支持配置并发数进行压力测试
- **LangSmith 追踪**: 集成 LangSmith 进行请求追踪和分析
- **多种输出格式**: 支持 JSON、CSV、Markdown 报告

## 安装

```bash
pip install dataagent-harbor
```

## 快速开始

### 1. 准备测试问题集

创建一个 JSON 文件包含测试问题：

```json
{
  "name": "basic-qa-test",
  "description": "Basic Q&A test cases",
  "questions": [
    {
      "id": "q1",
      "question": "What is Python?",
      "expected_keywords": ["programming", "language"],
      "category": "general"
    },
    {
      "id": "q2", 
      "question": "How to create a list in Python?",
      "expected_keywords": ["list", "[]", "append"],
      "category": "python"
    }
  ]
}
```

### 2. 运行压测

```bash
# 基本压测
dataagent-harbor run --dataset questions.json --server http://localhost:8000

# 并发压测
dataagent-harbor run --dataset questions.json --server http://localhost:8000 --concurrency 10

# 启用 LangSmith 追踪
export LANGSMITH_API_KEY="lsv2_..."
export LANGSMITH_TRACING_V2=true
dataagent-harbor run --dataset questions.json --server http://localhost:8000 --trace
```

### 3. 查看结果

```bash
# 生成报告
dataagent-harbor report --job-dir jobs/2024-01-01__12-00-00

# 分析失败案例
dataagent-harbor analyze --job-dir jobs/2024-01-01__12-00-00 --failed-only
```

## 配置

通过环境变量配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DATAAGENT_HARBOR_SERVER` | DataAgent Server 地址 | `http://localhost:8000` |
| `DATAAGENT_HARBOR_API_KEY` | API Key | - |
| `DATAAGENT_HARBOR_TIMEOUT` | 请求超时秒数 | `300` |
| `LANGSMITH_API_KEY` | LangSmith API Key | - |
| `LANGSMITH_TRACING_V2` | 启用 LangSmith 追踪 | `false` |
| `LANGSMITH_PROJECT` | LangSmith 项目名 | `dataagent-harbor` |

## 测试问题集格式

```json
{
  "name": "dataset-name",
  "description": "Dataset description",
  "version": "1.0",
  "questions": [
    {
      "id": "unique-id",
      "question": "The question to ask",
      "expected_keywords": ["keyword1", "keyword2"],
      "expected_pattern": "regex pattern (optional)",
      "category": "category name",
      "difficulty": "easy|medium|hard",
      "timeout": 60,
      "metadata": {}
    }
  ]
}
```

## 输出格式

### 结果 JSON

```json
{
  "job_id": "2024-01-01__12-00-00",
  "dataset": "basic-qa-test",
  "total": 100,
  "passed": 85,
  "failed": 15,
  "success_rate": 0.85,
  "avg_response_time": 2.5,
  "results": [...]
}
```

### 报告 Markdown

```markdown
# DataAgent Harbor Report

## Summary
- Total: 100
- Passed: 85 (85%)
- Failed: 15 (15%)
- Avg Response Time: 2.5s

## Failed Cases
...
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=dataagent_harbor
```
