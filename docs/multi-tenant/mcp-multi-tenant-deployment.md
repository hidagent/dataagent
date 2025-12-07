# MCP 多租户部署指南

## 1. 架构概览

### 1.1 部署拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                    负载均衡器 (Nginx/HAProxy)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼────┐
│ Server 1 │  │ Server 2 │  │ Server 3 │
│ (Alice)  │  │ (Bob)    │  │(Charlie) │
└───────┬──┘  ┌──────┬──┐  └─────┬────┘
        │     │      │           │
        └─────┼──────┼───────────┘
              │      │
        ┌─────▼──────▼─────┐
        │  Shared Database │
        │  (MySQL/SQLite)  │
        └──────────────────┘
```

### 1.2 隔离层次

| 层次 | 隔离方式 | 实现 |
|------|--------|------|
| **网络层** | 用户请求路由 | 负载均衡器根据 user_id 路由 |
| **应用层** | 用户上下文隔离 | 每个请求携带 user_id |
| **数据层** | 数据库隔离 | 所有查询都带 user_id 过滤 |
| **连接层** | MCP 连接隔离 | 每个 user_id 独立连接池 |
| **工具层** | 工具隔离 | 每个 user_id 独立工具集 |

## 2. 单机部署

### 2.1 基础配置

```bash
# 目录结构
/opt/dataagent/
├── config/
│   ├── settings.py
│   └── mcp_config.json
├── data/
│   ├── mcp_config.db
│   └── logs/
├── scripts/
│   ├── start.sh
│   ├── stop.sh
│   └── health_check.sh
└── venv/
```

### 2.2 启动脚本

```bash
#!/bin/bash
# /opt/dataagent/scripts/start.sh

set -e

# 加载环境变量
export PYTHONUNBUFFERED=1
export LOG_LEVEL=INFO
export MCP_MAX_CONNECTIONS_PER_USER=10
export MCP_MAX_TOTAL_CONNECTIONS=100

# 激活虚拟环境
source /opt/dataagent/venv/bin/activate

# 启动服务器
cd /opt/dataagent
python -m dataagent_server \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level $LOG_LEVEL \
  --db-url sqlite:////opt/dataagent/data/mcp_config.db
```

### 2.3 配置文件

```python
# /opt/dataagent/config/settings.py

import os
from pathlib import Path

# MCP 配置
MCP_CONFIG = {
    "max_connections_per_user": int(os.getenv("MCP_MAX_CONNECTIONS_PER_USER", 10)),
    "max_total_connections": int(os.getenv("MCP_MAX_TOTAL_CONNECTIONS", 100)),
    "connection_timeout": 30,
    "enable_audit_log": True,
}

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////opt/dataagent/data/mcp_config.db"
)

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path("/opt/dataagent/data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
```

## 3. 多机部署

### 3.1 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MySQL 数据库
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: dataagent
      MYSQL_USER: dataagent
      MYSQL_PASSWORD: dataagent_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  # DataAgent 服务器 - Alice
  dataagent-alice:
    build: .
    environment:
      USER_ID: alice
      DATABASE_URL: mysql+aiomysql://dataagent:dataagent_password@mysql:3306/dataagent
      MCP_MAX_CONNECTIONS_PER_USER: 10
      MCP_MAX_TOTAL_CONNECTIONS: 100
      LOG_LEVEL: INFO
      # Alice 的环境变量
      ALICE_GITHUB_TOKEN: ${ALICE_GITHUB_TOKEN}
      ALICE_SLACK_TOKEN: ${ALICE_SLACK_TOKEN}
    ports:
      - "8001:8000"
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - ./logs/alice:/opt/dataagent/logs

  # DataAgent 服务器 - Bob
  dataagent-bob:
    build: .
    environment:
      USER_ID: bob
      DATABASE_URL: mysql+aiomysql://dataagent:dataagent_password@mysql:3306/dataagent
      MCP_MAX_CONNECTIONS_PER_USER: 10
      MCP_MAX_TOTAL_CONNECTIONS: 100
      LOG_LEVEL: INFO
      # Bob 的环境变量
      BOB_GITHUB_TOKEN: ${BOB_GITHUB_TOKEN}
      BOB_JIRA_TOKEN: ${BOB_JIRA_TOKEN}
    ports:
      - "8002:8000"
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - ./logs/bob:/opt/dataagent/logs

  # DataAgent 服务器 - Charlie
  dataagent-charlie:
    build: .
    environment:
      USER_ID: charlie
      DATABASE_URL: mysql+aiomysql://dataagent:dataagent_password@mysql:3306/dataagent
      MCP_MAX_CONNECTIONS_PER_USER: 10
      MCP_MAX_TOTAL_CONNECTIONS: 100
      LOG_LEVEL: INFO
      # Charlie 的环境变量
      CHARLIE_GITHUB_TOKEN: ${CHARLIE_GITHUB_TOKEN}
      CHARLIE_AWS_ACCESS_KEY: ${CHARLIE_AWS_ACCESS_KEY}
      CHARLIE_AWS_SECRET_KEY: ${CHARLIE_AWS_SECRET_KEY}
    ports:
      - "8003:8000"
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - ./logs/charlie:/opt/dataagent/logs

  # Nginx 负载均衡器
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - dataagent-alice
      - dataagent-bob
      - dataagent-charlie

volumes:
  mysql_data:
```

### 3.2 Nginx 配置

```nginx
# nginx.conf
upstream dataagent_alice {
    server dataagent-alice:8000;
}

upstream dataagent_bob {
    server dataagent-bob:8000;
}

upstream dataagent_charlie {
    server dataagent-charlie:8000;
}

server {
    listen 80;
    server_name dataagent.example.com;

    # 根据 user_id 路由到不同的后端
    location /api/v1/users/alice/ {
        proxy_pass http://dataagent_alice;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-User-ID alice;
    }

    location /api/v1/users/bob/ {
        proxy_pass http://dataagent_bob;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-User-ID bob;
    }

    location /api/v1/users/charlie/ {
        proxy_pass http://dataagent_charlie;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-User-ID charlie;
    }

    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### 3.3 环境变量文件

```bash
# .env
# MySQL 配置
MYSQL_ROOT_PASSWORD=root_password
MYSQL_USER=dataagent
MYSQL_PASSWORD=dataagent_password

# Alice 的凭证
ALICE_GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
ALICE_SLACK_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxx

# Bob 的凭证
BOB_GITHUB_TOKEN=ghp_yyyyyyyyyyyyyyyyyyyy
BOB_JIRA_TOKEN=atcyyyyyyyyyyyyyyyyy

# Charlie 的凭证
CHARLIE_GITHUB_TOKEN=ghp_zzzzzzzzzzzzzzzzzzzz
CHARLIE_AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
CHARLIE_AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

## 4. Kubernetes 部署

### 4.1 Namespace 隔离

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dataagent
```

### 4.2 ConfigMap 配置

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataagent-config
  namespace: dataagent
data:
  settings.py: |
    MCP_CONFIG = {
        "max_connections_per_user": 10,
        "max_total_connections": 100,
        "connection_timeout": 30,
        "enable_audit_log": True,
    }
    DATABASE_URL = "mysql+aiomysql://dataagent:password@mysql:3306/dataagent"
    LOG_LEVEL = "INFO"
```

### 4.3 Secret 配置

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: dataagent-secrets
  namespace: dataagent
type: Opaque
stringData:
  alice-github-token: ghp_xxxxxxxxxxxxxxxxxxxx
  alice-slack-token: xoxb-xxxxxxxxxxxxxxxxxxxx
  bob-github-token: ghp_yyyyyyyyyyyyyyyyyyyy
  bob-jira-token: atcyyyyyyyyyyyyyyyyy
  charlie-github-token: ghp_zzzzzzzzzzzzzzzzzzzz
  charlie-aws-access-key: AKIAIOSFODNN7EXAMPLE
  charlie-aws-secret-key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### 4.4 Deployment 配置

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataagent-alice
  namespace: dataagent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dataagent
      user: alice
  template:
    metadata:
      labels:
        app: dataagent
        user: alice
    spec:
      containers:
      - name: dataagent
        image: dataagent:latest
        ports:
        - containerPort: 8000
        env:
        - name: USER_ID
          value: "alice"
        - name: DATABASE_URL
          value: "mysql+aiomysql://dataagent:password@mysql:3306/dataagent"
        - name: ALICE_GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: dataagent-secrets
              key: alice-github-token
        - name: ALICE_SLACK_TOKEN
          valueFrom:
            secretKeyRef:
              name: dataagent-secrets
              key: alice-slack-token
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 4.5 Service 配置

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: dataagent-alice
  namespace: dataagent
spec:
  selector:
    app: dataagent
    user: alice
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

## 5. 监控和告警

### 5.1 Prometheus 指标

```python
# dataagent_server/metrics.py
from prometheus_client import Counter, Gauge, Histogram

# MCP 连接指标
mcp_connections_total = Counter(
    'mcp_connections_total',
    'Total MCP connections',
    ['user_id', 'server_name', 'status']
)

mcp_connections_active = Gauge(
    'mcp_connections_active',
    'Active MCP connections',
    ['user_id']
)

mcp_connection_duration = Histogram(
    'mcp_connection_duration_seconds',
    'MCP connection duration',
    ['user_id', 'server_name']
)

# 工具执行指标
mcp_tool_executions = Counter(
    'mcp_tool_executions_total',
    'Total MCP tool executions',
    ['user_id', 'server_name', 'tool_name', 'status']
)

mcp_tool_duration = Histogram(
    'mcp_tool_duration_seconds',
    'MCP tool execution duration',
    ['user_id', 'server_name', 'tool_name']
)
```

### 5.2 告警规则

```yaml
# prometheus/alerts.yaml
groups:
- name: dataagent_mcp
  rules:
  # 连接失败告警
  - alert: MCPConnectionFailure
    expr: rate(mcp_connections_total{status="failed"}[5m]) > 0.1
    for: 5m
    annotations:
      summary: "MCP connection failures detected for {{ $labels.user_id }}"

  # 连接数过高告警
  - alert: MCPConnectionLimitWarning
    expr: mcp_connections_active / 10 > 0.8
    for: 5m
    annotations:
      summary: "MCP connections at 80% capacity for {{ $labels.user_id }}"

  # 工具执行错误告警
  - alert: MCPToolExecutionError
    expr: rate(mcp_tool_executions{status="error"}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "MCP tool execution errors for {{ $labels.user_id }}"
```

### 5.3 日志聚合

```python
# dataagent_server/logging_config.py
import logging
import json
from pythonjsonlogger import jsonlogger

# 结构化日志
class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_mcp_event(self, event_type, user_id, server_name, **kwargs):
        """记录 MCP 事件"""
        self.logger.info(json.dumps({
            "event_type": event_type,
            "user_id": user_id,
            "server_name": server_name,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }))

# 使用示例
logger = StructuredLogger("mcp")
logger.log_mcp_event(
    "connection_established",
    user_id="alice",
    server_name="github",
    tools_count=15
)
```

## 6. 安全加固

### 6.1 网络隔离

```bash
# 防火墙规则
# 只允许特定 IP 访问
iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP

# 限制连接数
iptables -A INPUT -p tcp --dport 8000 -m limit --limit 100/minute -j ACCEPT
```

### 6.2 认证和授权

```python
# dataagent_server/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    """验证用户身份"""
    token = credentials.credentials
    
    # 验证 JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_id(user_id: str = Depends(get_current_user)):
    """获取当前用户 ID"""
    return user_id
```

### 6.3 速率限制

```python
# dataagent_server/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 应用速率限制
@app.get("/api/v1/users/{user_id}/mcp-servers")
@limiter.limit("100/minute")
async def list_mcp_servers(user_id: str, request: Request):
    """列出 MCP 服务器，限制为每分钟 100 个请求"""
    pass
```

## 7. 故障恢复

### 7.1 健康检查

```python
# dataagent_server/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy"}

@router.get("/health/detailed")
async def detailed_health_check(mcp_manager: MCPConnectionManager):
    """详细健康检查"""
    return {
        "status": "healthy",
        "mcp": {
            "total_connections": mcp_manager.total_connections,
            "active_users": mcp_manager.get_user_count(),
            "capacity_usage": mcp_manager.total_connections / mcp_manager.max_total_connections,
        }
    }
```

### 7.2 自动恢复

```python
# dataagent_server/recovery.py
import asyncio

async def auto_reconnect_mcp_servers(manager: MCPConnectionManager, store: MCPConfigStore):
    """定期检查并重新连接失败的 MCP 服务器"""
    while True:
        try:
            # 检查所有用户的连接状态
            for user_id in manager._connections.keys():
                config = await store.get_user_config(user_id)
                status = manager.get_connection_status(user_id)
                
                # 重新连接失败的服务器
                for server_name, info in status.items():
                    if not info["connected"] and info["error"]:
                        logger.info(f"Attempting to reconnect {server_name} for {user_id}")
                        await manager.connect(user_id, config)
        
        except Exception as e:
            logger.error(f"Error in auto-reconnect: {e}")
        
        # 每 5 分钟检查一次
        await asyncio.sleep(300)
```

## 8. 性能优化

### 8.1 连接池配置

```python
# dataagent_server/config/settings.py
MCP_CONNECTION_POOL = {
    "max_connections_per_user": 10,
    "max_total_connections": 1000,
    "connection_timeout": 30,
    "idle_timeout": 300,  # 5 分钟
    "max_retries": 3,
    "retry_delay": 1,
}
```

### 8.2 缓存策略

```python
# dataagent_server/cache.py
from functools import lru_cache
import asyncio

class MCPToolCache:
    def __init__(self, ttl=300):
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
    
    async def get_tools(self, user_id: str, manager: MCPConnectionManager):
        """获取工具，使用缓存"""
        now = time.time()
        
        # 检查缓存是否过期
        if user_id in self.cache:
            if now - self.timestamps[user_id] < self.ttl:
                return self.cache[user_id]
        
        # 从管理器获取工具
        tools = manager.get_tools(user_id)
        self.cache[user_id] = tools
        self.timestamps[user_id] = now
        
        return tools
```

## 总结

这个多租户部署指南涵盖了：

✅ **单机部署** - 基础配置和启动脚本  
✅ **多机部署** - Docker Compose 和 Nginx 配置  
✅ **Kubernetes 部署** - 完整的 K8s 配置  
✅ **监控告警** - Prometheus 指标和告警规则  
✅ **安全加固** - 认证、授权和速率限制  
✅ **故障恢复** - 健康检查和自动恢复  
✅ **性能优化** - 连接池和缓存策略  

根据你的部署环境选择合适的方案，确保多租户隔离的同时保证系统的高可用性和性能。
