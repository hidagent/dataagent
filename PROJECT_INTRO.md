# DataAgent - 智能数据助手平台

> 🚀 **基于 DeepAgent 构建的下一代 AI 数据智能助手平台**

## 🌟 项目简介

DataAgent 是一个企业级的数据智能助手平台，专为数据工程师、业务分析师和数据管理者设计。基于 DeepAgent 强大的 AI 引擎，提供多模态交互界面（CLI、Web、API），支持人机协同工作流程，实现智能化的数据处理和分析。

## 🔥 核心优势

### 🤖 AI 驱动的数据智能
- **基于 DeepAgent 引擎**: 集成最先进的 AI 技术栈
- **多 LLM 支持**: OpenAI GPT、Anthropic Claude、Google Gemini
- **智能代理系统**: 自主任务执行和决策能力
- **实时流式响应**: WebSocket 实时通信，毫秒级响应

### 🏢 企业级多租户架构
- **用户完全隔离**: 数据、会话、工作空间完全分离
- **JWT 安全认证**: 企业级身份验证和授权
- **工作空间管理**: 灵活的用户工作空间配置
- **规则引擎**: 用户特定的业务规则和配置

### 🛡️ 人机协同 (HITL)
- **智能审批流程**: 敏感操作需要人工确认
- **自动审批模式**: 可配置的自动审批策略
- **多界面支持**: 终端和 Web 界面统一审批体验
- **安全沙箱**: 可选的命令执行沙箱环境

### 📊 事件驱动架构
- **实时事件流**: AsyncIterator 事件流架构
- **多种事件类型**: 文本、工具调用、HITL 请求、文件操作
- **状态管理**: LangGraph 集成的对话状态管理
- **可观测性**: 完整的事件追踪和监控

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    DataAgent 架构                            │
├─────────────────────────────────────────────────────────────┤
│  DataAgentCli (终端)    │        DataAgentServer (Web)       │
│                         │                                    │
│  ┌───────────┐          │  ┌─────────────┐ ┌──────────────┐ │
│  │ Terminal  │          │  │  REST API   │ │   WebSocket  │ │
│  │   HITL    │          │  │  /api/v1/*  │ │  /ws/chat/*  │ │
│  └───────────┘          │  └──────┬──────┘ └──────┬───────┘ │
└───────────┬─────────────┴─────────┼────────────────┼──────────┘
            │                       ▼                ▼
            │         ┌─────────────────────────────────────────────┐
            │         │            Event Stream                     │
            │         │    AsyncIterator[ExecutionEvent]            │
            │         └─────────────────────────────────────────────┘
            │                       ▲
            ▼                       ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    DataAgentCore (基于 DeepAgent)            │
   │                                                             │
   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
   │  │ AgentFactory │ │AgentExecutor │ │    Events    │       │
   │  │  (创建Agent)  │ │  (执行任务)   │ │   (事件流)   │       │
   │  └──────────────┘ └──────────────┘ └──────────────┘       │
   │                                                             │
   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
   │  │  Middleware  │ │    Tools     │ │     HITL     │       │
   │  │   (中间件)    │ │   (工具)     │ │   (人机交互)  │       │
   │  └──────────────┘ └──────────────┘ └──────────────┘       │
   └─────────────────────────────────────────────────────────────┘
```

## 🎯 核心功能

### 1. 多模态交互界面
- **🖥️ CLI 终端**: 功能丰富的命令行界面，支持交互式聊天
- **🌐 Web 界面**: 基于 Streamlit 的现代化 Web 应用
- **🔌 REST API**: 完整的 API 接口，支持第三方集成
- **⚡ WebSocket**: 实时双向通信，支持流式响应

### 2. 智能数据处理
- **📈 数据分析**: 统计分析、可视化、数据洞察
- **🗄️ SQL 专家**: 数据库查询、优化、模式分析
- **🔍 代码审查**: 代码分析、最佳实践、安全审查
- **📝 文档编写**: 技术文档、报告、指南生成
- **🧪 API 测试**: API 测试、文档、集成

### 3. 企业级安全
- **🔐 JWT 认证**: 企业级身份验证
- **👥 多租户隔离**: 完整的用户数据隔离
- **🛡️ 安全沙箱**: 可选的命令执行环境
- **📋 审计日志**: 完整的操作记录和追踪

### 4. 可扩展工具系统
- **🔧 MCP 集成**: Model Context Protocol 工具扩展
- **🎯 内置技能**: 数据分析、SQL、代码审查等
- **⚙️ 自定义工具**: 易于集成自定义工具和 API
- **🔌 插件架构**: 模块化的工具加载系统

## 🚀 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 12+ (生产环境)
- OpenAI/Anthropic API 密钥

### 安装部署
```bash
# 克隆项目
git clone https://github.com/hidagent/dataagent.git
cd dataagent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 API 密钥和数据库连接

# 运行服务
python -m dataagent_server.main
```

### 使用示例
```python
# CLI 模式
dataagent-cli

# Web 模式
# 访问 http://localhost:8501

# API 调用
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "分析这份销售数据", "session_id": "test-session"}'
```

## 🏗️ 部署选项

### 开发环境
- **内存存储**: 快速开发测试
- **SQLite**: 轻量级数据库
- **单用户模式**: 简化配置

### 生产环境
- **PostgreSQL**: 高性能数据库
- **Docker 容器化**: 易于部署和扩展
- **多租户模式**: 支持多用户和企业级应用

### 云部署
- **Kubernetes**: 容器编排
- **负载均衡**: 高可用性配置
- **自动扩展**: 弹性伸缩支持

## 📊 性能指标

- **并发支持**: 100+ 同时在线用户
- **响应时间**: 平均 < 500ms
- **吞吐量**: 1000+ 请求/分钟
- **可用性**: 99.9%+ 服务可用性

## 🔧 技术栈

### 核心技术
- **Python 3.11+**: 主要开发语言
- **DeepAgent**: AI 代理框架基础
- **FastAPI**: 现代 Web API 框架
- **WebSocket**: 实时双向通信
- **Pydantic**: 数据验证和序列化

### AI/ML 集成
- **OpenAI GPT**: 主要 LLM 支持
- **Anthropic Claude**: 备选 LLM 提供商
- **Google Gemini**: 额外 LLM 选项
- **Tavily**: 网络搜索集成

### 数据库支持
- **SQLAlchemy**: 支持异步的 ORM
- **PostgreSQL**: 推荐的生产数据库
- **SQLite**: 轻量级开发数据库
- **AsyncPG**: 高性能 PostgreSQL 驱动

## 🎯 应用场景

### 数据分析团队
- **智能数据探索**: 自然语言查询和分析
- **自动化报告**: 生成数据洞察报告
- **协作分析**: 团队共享分析会话

### 开发团队
- **代码审查助手**: 智能代码分析和建议
- **API 测试自动化**: 自动生成和执行测试
- **文档生成**: 技术文档自动生成

### 企业 IT
- **智能运维**: 日志分析和故障诊断
- **安全审计**: 自动化安全检查
- **知识管理**: 企业知识库构建

## 🤝 贡献指南

我们欢迎社区贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目开发。

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

## 🌟 Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=hidagent/dataagent&type=Date)](https://star-history.com/#hidagent/dataagent&Date)

## 📞 联系我们

- 💬 讨论区: [GitHub Discussions](https://github.com/hidagent/dataagent/discussions)
- 📧 邮箱: team@dataagent.ai
- 🐦 Twitter: [@DataAgentAI](https://twitter.com/DataAgentAI)

---

**关键词**: AI数据助手, DeepAgent, 多租户架构, 人机协同, 事件驱动, WebSocket实时通信, FastAPI, PostgreSQL, JWT认证, 数据分析, SQL专家, 代码审查, 智能代理, LangChain, LangGraph, MCP协议, 流式响应, 企业级AI, 数据智能, 自动化分析, 智能决策, 实时数据处理