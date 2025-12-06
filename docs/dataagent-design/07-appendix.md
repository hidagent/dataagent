# DataAgent 架构设计方案

## 第七章：附录

### A. 完整目录结构

```
libs/
├── dataagent-core/
│   ├── pyproject.toml
│   ├── README.md
│   └── dataagent_core/
│       ├── __init__.py
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── factory.py
│       │   ├── executor.py
│       │   ├── streaming.py
│       │   └── types.py
│       ├── events/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── text.py
│       │   ├── tool.py
│       │   ├── hitl.py
│       │   ├── file.py
│       │   └── system.py
│       ├── middleware/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── memory.py
│       │   ├── skills.py
│       │   └── shell.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py
│       │   ├── web.py
│       │   ├── file_tracker.py
│       │   └── data/
│       │       ├── __init__.py
│       │       ├── sql.py
│       │       ├── catalog.py
│       │       └── report.py
│       ├── skills/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   ├── manager.py
│       │   └── types.py
│       ├── sandbox/
│       │   ├── __init__.py
│       │   ├── factory.py
│       │   ├── modal.py
│       │   ├── runloop.py
│       │   └── daytona.py
│       ├── session/
│       │   ├── __init__.py
│       │   ├── manager.py
│       │   ├── state.py
│       │   ├── store.py
│       │   └── stores/
│       │       ├── __init__.py
│       │       ├── memory.py
│       │       ├── redis.py
│       │       └── database.py
│       ├── hitl/
│       │   ├── __init__.py
│       │   ├── protocol.py
│       │   ├── types.py
│       │   └── auto_approve.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   ├── models.py
│       │   └── prompts.py
│       └── utils/
│           ├── __init__.py
│           ├── tokens.py
│           ├── diff.py
│           └── paths.py
│
├── dataagent-cli/
│   ├── pyproject.toml
│   ├── README.md
│   └── dataagent_cli/
│       ├── __init__.py
│       ├── main.py
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── console.py
│       │   ├── renderer.py
│       │   ├── diff.py
│       │   ├── todo.py
│       │   └── colors.py
│       ├── input/
│       │   ├── __init__.py
│       │   ├── session.py
│       │   ├── completers.py
│       │   └── keybindings.py
│       ├── hitl/
│       │   ├── __init__.py
│       │   └── terminal.py
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── slash.py
│       │   ├── bash.py
│       │   └── skills.py
│       └── config.py
│
└── dataagent-server/
    ├── pyproject.toml
    ├── README.md
    └── dataagent_server/
        ├── __init__.py
        ├── main.py
        ├── api/
        │   ├── __init__.py
        │   ├── deps.py
        │   └── v1/
        │       ├── __init__.py
        │       ├── chat.py
        │       ├── sessions.py
        │       ├── agents.py
        │       ├── skills.py
        │       └── admin.py
        ├── websocket/
        │   ├── __init__.py
        │   ├── manager.py
        │   ├── handlers.py
        │   └── protocol.py
        ├── services/
        │   ├── __init__.py
        │   ├── chat.py
        │   ├── session.py
        │   └── user.py
        ├── models/
        │   ├── __init__.py
        │   ├── user.py
        │   ├── session.py
        │   └── message.py
        ├── db/
        │   ├── __init__.py
        │   ├── database.py
        │   └── repositories/
        ├── auth/
        │   ├── __init__.py
        │   ├── jwt.py
        │   └── middleware.py
        ├── hitl/
        │   ├── __init__.py
        │   └── websocket_handler.py
        └── config/
            ├── __init__.py
            └── settings.py
```

### B. 依赖关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        依赖关系                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  dataagent-cli ──────────────► dataagent-core                  │
│       │                              │                          │
│       │                              ▼                          │
│       │                        deepagents                       │
│       │                              │                          │
│       │                              ▼                          │
│       │                     langchain/langgraph                 │
│       │                                                         │
│       ▼                                                         │
│  rich, prompt-toolkit                                           │
│                                                                 │
│                                                                 │
│  dataagent-server ───────────► dataagent-core                  │
│       │                              │                          │
│       │                              ▼                          │
│       │                        deepagents                       │
│       │                                                         │
│       ▼                                                         │
│  fastapi, uvicorn, websockets, sqlalchemy                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### C. 配置示例

#### C.1 dataagent-core 配置

```python
# 环境变量
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
TAVILY_API_KEY=tvly-xxx

# 可选沙箱
MODAL_TOKEN_ID=xxx
MODAL_TOKEN_SECRET=xxx
RUNLOOP_API_KEY=xxx
DAYTONA_API_KEY=xxx
```

#### C.2 dataagent-server 配置

```python
# dataagent_server/config/settings.py

from pydantic_settings import BaseSettings

class ServerSettings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # 数据库
    database_url: str = "postgresql+asyncpg://user:pass@localhost/dataagent"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # JWT
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    
    # Agent
    default_model: str = "claude-sonnet-4-5-20250929"
    
    class Config:
        env_file = ".env"
```

### D. 数据库 Schema

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话表
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    assistant_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(50) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### E. 文档索引

| 章节 | 文件 | 内容 |
|------|------|------|
| 第一章 | 01-overview.md | 概述与架构总览 |
| 第二章 | 02-deepagents-cli-analysis.md | deepagents_cli 可拆解性分析 |
| 第三章 | 03-dataagent-core.md | DataAgentCore 详细设计 |
| 第四章 | 04-dataagent-server.md | DataAgentServer 详细设计 |
| 第五章 | 05-dataagent-cli.md | DataAgentCli 设计 |
| 第六章 | 06-implementation-plan.md | 实施计划 |
| 第七章 | 07-appendix.md | 附录 |

### F. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1.0 | 2024-12-05 | 初始设计方案 |

---

**文档结束**
