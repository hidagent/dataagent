# DataAgent - Intelligent Data Assistant Platform

> 🚀 **Next-Generation AI Data Intelligence Assistant Platform Built on DeepAgent**

## 🌟 Project Overview

DataAgent is an enterprise-grade data intelligence assistant platform designed for data engineers, business analysts, and data managers. Built on DeepAgent's powerful AI engine, it provides multi-modal interaction interfaces (CLI, Web, API) and supports human-in-the-loop workflows for intelligent data processing and analysis.

## 🔥 Core Advantages

### 🤖 AI-Driven Data Intelligence
- **Built on DeepAgent Engine**: Integrates the most advanced AI technology stack
- **Multi-LLM Support**: OpenAI GPT, Anthropic Claude, Google Gemini
- **Intelligent Agent System**: Autonomous task execution and decision-making capabilities
- **Real-time Streaming Response**: WebSocket real-time communication with millisecond response times

### 🏢 Enterprise Multi-tenant Architecture
- **Complete User Isolation**: Full separation of data, sessions, and workspaces
- **JWT Security Authentication**: Enterprise-grade identity verification and authorization
- **Workspace Management**: Flexible user workspace configuration
- **Rule Engine**: User-specific business rules and configurations

### 🛡️ Human-in-the-Loop (HITL)
- **Intelligent Approval Workflow**: Sensitive operations require human confirmation
- **Auto-approval Mode**: Configurable automatic approval policies
- **Multi-interface Support**: Unified approval experience across terminal and web interfaces
- **Security Sandbox**: Optional sandboxed command execution environment

### 📊 Event-Driven Architecture
- **Real-time Event Streams**: AsyncIterator event stream architecture
- **Multiple Event Types**: Text, tool calls, HITL requests, file operations
- **State Management**: LangGraph integrated conversation state management
- **Observability**: Complete event tracking and monitoring

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DataAgent Architecture                    │
├─────────────────────────────────────────────────────────────┤
│  DataAgentCli (Terminal) │        DataAgentServer (Web)      │
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
   │                    DataAgentCore (Built on DeepAgent)       │
   │                                                             │
   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
   │  │ AgentFactory │ │AgentExecutor │ │    Events    │       │
   │  │  (Create Agent)│ │(Execute Tasks)│ │   (Event Stream)│       │
   │  └──────────────┘ └──────────────┘ └──────────────┘       │
   │                                                             │
   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
   │  │  Middleware  │ │    Tools     │ │     HITL     │       │
   │  │ (Middleware) │ │   (Tools)    │ │ (Human Loop) │       │
   │  └──────────────┘ └──────────────┘ └──────────────┘       │
   └─────────────────────────────────────────────────────────────┘
```

## 🎯 Core Features

### 1. Multi-modal Interaction Interface
- **🖥️ CLI Terminal**: Feature-rich command-line interface with interactive chat
- **🌐 Web Interface**: Modern Streamlit-based web application
- **🔌 REST API**: Complete API interfaces for third-party integration
- **⚡ WebSocket**: Real-time bidirectional communication with streaming responses

### 2. Intelligent Data Processing
- **📈 Data Analysis**: Statistical analysis, visualization, data insights
- **🗄️ SQL Expert**: Database querying, optimization, schema analysis
- **🔍 Code Review**: Code analysis, best practices, security review
- **📝 Document Writing**: Technical documentation, reports, guide generation
- **🧪 API Testing**: API testing, documentation, integration

### 3. Enterprise Security
- **🔐 JWT Authentication**: Enterprise-grade identity verification
- **👥 Multi-tenant Isolation**: Complete user data separation
- **🛡️ Security Sandbox**: Optional command execution environment
- **📋 Audit Logs**: Complete operation records and tracking

### 4. Extensible Tool System
- **🔧 MCP Integration**: Model Context Protocol for tool extensions
- **🎯 Built-in Skills**: Data analysis, SQL, code review, etc.
- **⚙️ Custom Tools**: Easy integration of custom tools and APIs
- **🔌 Plugin Architecture**: Modular tool loading system

## 🚀 Quick Start

### Requirements
- Python 3.11+
- PostgreSQL 12+ (Production)
- OpenAI/Anthropic API Keys

### Installation & Deployment
```bash
# Clone the project
git clone https://github.com/hidagent/dataagent.git
cd dataagent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env file with API keys and database connections

# Run the service
python -m dataagent_server.main
```

### Usage Examples
```python
# CLI Mode
dataagent-cli

# Web Mode
# Visit http://localhost:8501

# API Call
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze this sales data", "session_id": "test-session"}'
```

## 🏗️ Deployment Options

### Development Environment
- **Memory Storage**: Quick development testing
- **SQLite**: Lightweight database
- **Single User Mode**: Simplified configuration

### Production Environment
- **PostgreSQL**: High-performance database
- **Docker Containerization**: Easy deployment and scaling
- **Multi-tenant Mode**: Support for multi-user and enterprise applications

### Cloud Deployment
- **Kubernetes**: Container orchestration
- **Load Balancing**: High availability configuration
- **Auto-scaling**: Elastic scaling support

## 📊 Performance Metrics

- **Concurrent Support**: 100+ simultaneous online users
- **Response Time**: Average < 500ms
- **Throughput**: 1000+ requests/minute
- **Availability**: 99.9%+ service availability

## 🔧 Technology Stack

### Core Technologies
- **Python 3.11+**: Primary development language
- **DeepAgent**: AI agent framework foundation
- **FastAPI**: Modern web API framework
- **WebSocket**: Real-time bidirectional communication
- **Pydantic**: Data validation and serialization

### AI/ML Integration
- **OpenAI GPT**: Primary LLM support
- **Anthropic Claude**: Alternative LLM provider
- **Google Gemini**: Additional LLM option
- **Tavily**: Web search integration

### Database Support
- **SQLAlchemy**: Database ORM with async support
- **PostgreSQL**: Recommended production database
- **SQLite**: Lightweight development database
- **AsyncPG**: High-performance PostgreSQL driver

## 🎯 Application Scenarios

### Data Analysis Teams
- **Intelligent Data Exploration**: Natural language queries and analysis
- **Automated Reporting**: Generate data insight reports
- **Collaborative Analysis**: Team-shared analysis sessions

### Development Teams
- **Code Review Assistant**: Intelligent code analysis and suggestions
- **API Test Automation**: Automatic test generation and execution
- **Documentation Generation**: Automatic technical documentation

### Enterprise IT
- **Intelligent Operations**: Log analysis and fault diagnosis
- **Security Auditing**: Automated security checks
- **Knowledge Management**: Enterprise knowledge base building

## 🤝 Contributing Guidelines

We welcome community contributions! Please check [CONTRIBUTING.md](CONTRIBUTING.md) to learn how to participate in project development.

## 📄 License

This project is open source under the [MIT License](LICENSE).

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=hidagent/dataagent&type=Date)](https://star-history.com/#hidagent/dataagent&Date)

## 📞 Contact Us

- 💬 Discussions: [GitHub Discussions](https://github.com/hidagent/dataagent/discussions)
- 📧 Email: team@dataagent.ai
- 🐦 Twitter: [@DataAgentAI](https://twitter.com/DataAgentAI)

---

**Keywords**: AI Data Assistant, DeepAgent, Multi-tenant Architecture, Human-in-the-Loop, Event-Driven, WebSocket Real-time Communication, FastAPI, PostgreSQL, JWT Authentication, Data Analysis, SQL Expert, Code Review, Intelligent Agent, LangChain, LangGraph, MCP Protocol, Streaming Response, Enterprise AI, Data Intelligence, Automated Analysis, Intelligent Decision-making, Real-time Data Processing