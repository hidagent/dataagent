# DataAgent Server

DataAgent Server 是 DataAgent 平台的 Web 服务层，通过 FastAPI 提供 REST API 和 WebSocket 接口。

## 功能特性

- **REST API**: 提供同步聊天、会话管理、健康检查等接口
- **WebSocket**: 提供实时流式聊天和 HITL 交互
- **高并发**: 支持 100+ 用户同时问答
- **问答终止**: 支持随时取消正在进行的问答
- **API Key 认证**: 支持多 API Key 认证

## 安装

```bash
pip install dataagent-server
```

## 快速开始

```bash
# 启动服务
dataagent-server

# 或使用 uvicorn
uvicorn dataagent_server.main:app --host 0.0.0.0 --port 8000
```

## 配置

通过环境变量配置服务：

### 基础配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DATAAGENT_HOST` | 监听地址 | `0.0.0.0` |
| `DATAAGENT_PORT` | 监听端口 | `8000` |
| `DATAAGENT_WORKERS` | 工作进程数 | `1` |
| `DATAAGENT_API_KEYS` | API Key 列表（逗号分隔） | - |
| `DATAAGENT_CORS_ORIGINS` | CORS 允许的源（逗号分隔） | `*` |
| `DATAAGENT_SESSION_TIMEOUT` | 会话超时秒数 | `3600` |
| `DATAAGENT_AUTH_DISABLED` | 禁用认证 | `false` |
| `DATAAGENT_MAX_CONNECTIONS` | 最大并发连接数 | `200` |

### 会话存储配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DATAAGENT_SESSION_STORE` | 存储类型（memory/mysql） | `memory` |
| `DATAAGENT_MYSQL_HOST` | MySQL 主机地址 | `localhost` |
| `DATAAGENT_MYSQL_PORT` | MySQL 端口 | `3306` |
| `DATAAGENT_MYSQL_USER` | MySQL 用户名 | `root` |
| `DATAAGENT_MYSQL_PASSWORD` | MySQL 密码 | - |
| `DATAAGENT_MYSQL_DATABASE` | MySQL 数据库名 | `dataagent` |
| `DATAAGENT_MYSQL_POOL_SIZE` | 连接池大小 | `10` |
| `DATAAGENT_MYSQL_MAX_OVERFLOW` | 连接池最大溢出 | `20` |

### MySQL 存储配置示例

```bash
# 使用 MySQL 存储
export DATAAGENT_SESSION_STORE=mysql
export DATAAGENT_MYSQL_HOST=localhost
export DATAAGENT_MYSQL_PORT=3306
export DATAAGENT_MYSQL_USER=dataagent
export DATAAGENT_MYSQL_PASSWORD=your_password
export DATAAGENT_MYSQL_DATABASE=dataagent

# 启动服务
dataagent-server
```

服务启动时会自动创建所需的数据库表（sessions 和 messages）。

## API 端点

### REST API

- `GET /api/v1/health` - 健康检查
- `POST /api/v1/chat` - 发送消息（同步）
- `POST /api/v1/chat/{session_id}/cancel` - 取消问答
- `GET /api/v1/sessions` - 列出会话
- `GET /api/v1/sessions/{session_id}` - 获取会话详情
- `DELETE /api/v1/sessions/{session_id}` - 删除会话
- `GET /api/v1/sessions/{session_id}/messages` - 获取会话历史消息（支持分页）

### WebSocket

- `/ws/chat/{session_id}` - 实时聊天

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=dataagent_server
```
