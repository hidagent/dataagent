# 快速开始

## 环境要求

- Python 3.11+
- 至少一个 LLM API Key (OpenAI / Anthropic / Google)

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd deepagents
```

### 2. 安装依赖

```bash
# 安装所有组件
pip install -e libs/dataagent-core
pip install -e libs/dataagent-cli
pip install -e libs/dataagent-server
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# LLM API Keys (至少配置一个)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx

# 可选：Web 搜索
TAVILY_API_KEY=tvly-xxx

# 可选：LangSmith 追踪
LANGSMITH_API_KEY=xxx
LANGSMITH_TRACING_V2=true
```

## 运行

### CLI 模式

```bash
# 启动交互式终端
dataagent-cli

# 指定 Agent
dataagent-cli --agent my-agent

# 自动审批模式
dataagent-cli --auto-approve
```

### Server 模式

```bash
# 启动服务器
dataagent-server

# 指定端口
DATAAGENT_PORT=8080 dataagent-server

# 使用 MySQL 存储
DATAAGENT_SESSION_STORE=mysql \
DATAAGENT_MYSQL_HOST=localhost \
DATAAGENT_MYSQL_USER=root \
DATAAGENT_MYSQL_PASSWORD=xxx \
DATAAGENT_MYSQL_DATABASE=dataagent \
dataagent-server
```

### Demo 应用

```bash
# 启动 Streamlit Demo
cd libs/dataagent-server-demo
streamlit run dataagent_server_demo/app.py
```

## 验证安装

```bash
# 检查 CLI
dataagent-cli --help

# 检查 Server 健康状态
curl http://localhost:8000/api/v1/health
```

## 下一步

- 阅读 [架构概览](./architecture.md) 了解系统设计
- 阅读 [开发人员手册](./developer-guide.md) 参与开发
- 阅读 [API 参考](./api-reference.md) 了解接口详情
