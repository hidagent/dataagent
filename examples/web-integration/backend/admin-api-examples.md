# DataAgent 管理 API 示例

本文档提供 DataAgent Server 管理功能 API 的详细使用示例。

## 目录

1. [用户档案管理](#用户档案管理)
2. [MCP 服务器管理](#mcp-服务器管理)
3. [规则管理](#规则管理)
4. [助手管理](#助手管理)
5. [用户记忆管理](#用户记忆管理)

## 基础配置

```bash
# 设置环境变量
export DATAAGENT_URL="http://localhost:8000"
export DATAAGENT_USER_ID="admin"
export DATAAGENT_API_KEY="your-api-key"  # 如果启用了认证
```

---

## 用户档案管理

用户档案用于存储用户的基本信息，支持个性化 Agent 响应。

### 创建用户档案

```bash
curl -X POST "$DATAAGENT_URL/api/v1/user-profiles" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: admin" \
  -d '{
    "user_id": "user001",
    "username": "zhangsan",
    "display_name": "张三",
    "email": "zhangsan@example.com",
    "department": "技术部",
    "role": "高级开发工程师",
    "custom_fields": {
      "team": "AI平台组",
      "level": "P7",
      "skills": ["Python", "AI", "数据分析"]
    }
  }'
```

### 批量创建用户档案（Python 示例）

```python
import asyncio
import httpx

async def batch_create_profiles():
    users = [
        {"user_id": "user001", "username": "zhangsan", "display_name": "张三", "department": "技术部"},
        {"user_id": "user002", "username": "lisi", "display_name": "李四", "department": "产品部"},
        {"user_id": "user003", "username": "wangwu", "display_name": "王五", "department": "运营部"},
    ]
    
    async with httpx.AsyncClient() as client:
        for user in users:
            try:
                response = await client.post(
                    "http://localhost:8000/api/v1/user-profiles",
                    json=user,
                    headers={"X-User-ID": "admin"}
                )
                print(f"Created: {user['user_id']} - {response.status_code}")
            except Exception as e:
                print(f"Error creating {user['user_id']}: {e}")

asyncio.run(batch_create_profiles())
```

### 查询和过滤用户

```bash
# 列出所有用户
curl -s "$DATAAGENT_URL/api/v1/user-profiles" \
  -H "X-User-ID: admin" | jq '.profiles[] | {user_id, display_name, department}'
```

---

## MCP 服务器管理

MCP (Model Context Protocol) 服务器用于扩展 Agent 的工具能力。

### 添加命令行 MCP 服务器

```bash
# AWS 文档服务器
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "aws-docs",
    "command": "uvx",
    "args": ["awslabs.aws-documentation-mcp-server@latest"],
    "env": {"FASTMCP_LOG_LEVEL": "ERROR"},
    "disabled": false,
    "autoApprove": ["search_documentation"]
  }'

# 文件系统服务器
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"],
    "disabled": false
  }'
```

### 添加 HTTP/SSE MCP 服务器

```bash
# 远程 MCP 服务器（SSE 传输）
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "remote-tools",
    "url": "http://mcp-server.example.com/sse",
    "transport": "sse",
    "headers": {
      "Authorization": "Bearer your-token",
      "X-Custom-Header": "value"
    },
    "disabled": false
  }'

# Streamable HTTP 传输
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "http-tools",
    "url": "http://mcp-server.example.com/mcp",
    "transport": "streamable_http",
    "disabled": false
  }'
```

### 连接并测试 MCP 服务器

```bash
# 连接服务器
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/connect" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq

# 查看可用工具
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/mcp-servers/aws-docs/status" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq '.tools'
```

### MCP 服务器管理脚本

```python
#!/usr/bin/env python3
"""MCP 服务器管理脚本"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"
USER_ID = "admin"

async def list_servers():
    """列出所有 MCP 服务器"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/users/{USER_ID}/mcp-servers",
            headers={"X-User-ID": USER_ID}
        )
        servers = response.json().get("servers", [])
        
        print(f"{'名称':<20} {'状态':<12} {'工具数':<8} {'错误'}")
        print("-" * 60)
        for s in servers:
            status = "✓ 已连接" if s["connected"] else "✗ 未连接"
            if s["disabled"]:
                status = "⊘ 已禁用"
            error = s.get("error", "-") or "-"
            print(f"{s['name']:<20} {status:<12} {s['tools_count']:<8} {error[:20]}")

async def connect_all():
    """连接所有启用的 MCP 服务器"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 获取服务器列表
        response = await client.get(
            f"{BASE_URL}/api/v1/users/{USER_ID}/mcp-servers",
            headers={"X-User-ID": USER_ID}
        )
        servers = response.json().get("servers", [])
        
        for s in servers:
            if s["disabled"]:
                print(f"跳过已禁用: {s['name']}")
                continue
            
            print(f"连接中: {s['name']}...", end=" ")
            try:
                result = await client.post(
                    f"{BASE_URL}/api/v1/users/{USER_ID}/mcp-servers/{s['name']}/connect",
                    headers={"X-User-ID": USER_ID}
                )
                data = result.json()
                if data["success"]:
                    print(f"✓ 成功 ({data['tools_count']} 个工具)")
                else:
                    print(f"✗ 失败: {data.get('error', 'Unknown')}")
            except Exception as e:
                print(f"✗ 错误: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "connect":
        asyncio.run(connect_all())
    else:
        asyncio.run(list_servers())
```

---

## 规则管理

规则用于定制 Agent 的行为和响应方式。

### 创建代码风格规则

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "python-code-style",
    "description": "Python 代码风格规范",
    "content": "在编写 Python 代码时，请遵循以下规范：\n\n1. 使用 4 空格缩进\n2. 函数和变量名使用 snake_case\n3. 类名使用 PascalCase\n4. 常量使用 UPPER_SNAKE_CASE\n5. 每行不超过 88 字符\n6. 使用类型注解\n7. 编写 docstring 文档",
    "scope": "user",
    "inclusion": "file_match",
    "file_match_pattern": "*.py",
    "priority": 60,
    "enabled": true
  }'
```

### 创建安全规则

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "security-guidelines",
    "description": "安全编码指南",
    "content": "在处理代码时，请注意以下安全事项：\n\n1. 不要在代码中硬编码密码、API Key 等敏感信息\n2. 使用参数化查询防止 SQL 注入\n3. 对用户输入进行验证和转义\n4. 使用 HTTPS 进行网络通信\n5. 遵循最小权限原则",
    "scope": "global",
    "inclusion": "always",
    "priority": 90,
    "enabled": true
  }'
```

### 创建项目特定规则

```bash
curl -X POST "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/rules" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "project-conventions",
    "description": "项目约定",
    "content": "本项目使用以下技术栈和约定：\n\n- 后端: FastAPI + SQLAlchemy\n- 前端: React + TypeScript\n- 数据库: PostgreSQL\n- 缓存: Redis\n\n目录结构：\n- src/api/ - API 路由\n- src/models/ - 数据模型\n- src/services/ - 业务逻辑\n- src/utils/ - 工具函数",
    "scope": "project",
    "inclusion": "always",
    "priority": 50,
    "enabled": true
  }'
```

### 规则管理脚本

```python
#!/usr/bin/env python3
"""规则管理脚本"""

import asyncio
import httpx
from pathlib import Path

BASE_URL = "http://localhost:8000"
USER_ID = "admin"

async def import_rules_from_directory(rules_dir: str):
    """从目录导入规则文件"""
    rules_path = Path(rules_dir)
    
    async with httpx.AsyncClient() as client:
        for rule_file in rules_path.glob("*.md"):
            content = rule_file.read_text()
            name = rule_file.stem
            
            # 解析 frontmatter（如果有）
            description = f"从 {rule_file.name} 导入的规则"
            
            rule = {
                "name": name,
                "description": description,
                "content": content,
                "scope": "user",
                "inclusion": "always",
                "priority": 50,
                "enabled": True,
            }
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/users/{USER_ID}/rules",
                    json=rule,
                    headers={"X-User-ID": USER_ID}
                )
                if response.status_code == 201:
                    print(f"✓ 导入成功: {name}")
                elif response.status_code == 409:
                    print(f"⊘ 已存在: {name}")
                else:
                    print(f"✗ 导入失败: {name} - {response.text}")
            except Exception as e:
                print(f"✗ 错误: {name} - {e}")

async def export_rules_to_directory(output_dir: str):
    """导出规则到目录"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/users/{USER_ID}/rules",
            headers={"X-User-ID": USER_ID}
        )
        rules = response.json().get("rules", [])
        
        for rule in rules:
            file_path = output_path / f"{rule['name']}.md"
            
            # 添加 frontmatter
            content = f"""---
description: {rule['description']}
scope: {rule['scope']}
inclusion: {rule['inclusion']}
priority: {rule['priority']}
enabled: {rule['enabled']}
---

{rule['content']}
"""
            file_path.write_text(content)
            print(f"✓ 导出: {rule['name']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python rules_manager.py [import|export] <directory>")
        sys.exit(1)
    
    action = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else "./rules"
    
    if action == "import":
        asyncio.run(import_rules_from_directory(directory))
    elif action == "export":
        asyncio.run(export_rules_to_directory(directory))
    else:
        print(f"未知操作: {action}")
```

---

## 助手管理

助手是预配置的 Agent 实例，可以有不同的系统提示和工具配置。

### 创建专业助手

```bash
# 代码审查助手
curl -X POST "$DATAAGENT_URL/api/v1/assistants" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "代码审查助手",
    "description": "专注于代码审查和质量改进",
    "system_prompt": "你是一个专业的代码审查助手。在审查代码时，请关注：\n1. 代码可读性和可维护性\n2. 潜在的 bug 和边界情况\n3. 性能优化机会\n4. 安全漏洞\n5. 最佳实践遵循情况\n\n请提供具体、可操作的改进建议。",
    "auto_approve": false,
    "metadata": {"category": "development", "expertise": "code-review"}
  }'

# SQL 助手
curl -X POST "$DATAAGENT_URL/api/v1/assistants" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: $DATAAGENT_USER_ID" \
  -d '{
    "name": "SQL 助手",
    "description": "专注于 SQL 查询优化和数据分析",
    "system_prompt": "你是一个 SQL 专家。帮助用户：\n1. 编写高效的 SQL 查询\n2. 优化慢查询\n3. 设计数据库表结构\n4. 解释执行计划\n5. 数据分析和报表",
    "auto_approve": true,
    "metadata": {"category": "data", "expertise": "sql"}
  }'
```

---

## 用户记忆管理

用户记忆存储 Agent 与用户交互的上下文信息。

### 查看记忆状态

```bash
curl -s "$DATAAGENT_URL/api/v1/users/$DATAAGENT_USER_ID/memory/status" \
  -H "X-User-ID: $DATAAGENT_USER_ID" | jq
```

### 清除用户记忆

```bash
# 清除特定用户的记忆
curl -X DELETE "$DATAAGENT_URL/api/v1/users/user001/memory" \
  -H "X-User-ID: admin" | jq
```

### 批量清除记忆（Python 示例）

```python
import asyncio
import httpx

async def clear_all_user_memories():
    """清除所有用户的记忆"""
    async with httpx.AsyncClient() as client:
        # 获取所有用户
        response = await client.get(
            "http://localhost:8000/api/v1/user-profiles",
            headers={"X-User-ID": "admin"}
        )
        profiles = response.json().get("profiles", [])
        
        for profile in profiles:
            user_id = profile["user_id"]
            try:
                result = await client.delete(
                    f"http://localhost:8000/api/v1/users/{user_id}/memory",
                    headers={"X-User-ID": "admin"}
                )
                print(f"✓ 清除: {user_id}")
            except Exception as e:
                print(f"✗ 错误: {user_id} - {e}")

asyncio.run(clear_all_user_memories())
```

---

## 综合管理脚本

```python
#!/usr/bin/env python3
"""DataAgent 综合管理脚本"""

import asyncio
import argparse
import httpx
import json

BASE_URL = "http://localhost:8000"

class DataAgentAdmin:
    def __init__(self, base_url: str, admin_user: str = "admin"):
        self.base_url = base_url
        self.admin_user = admin_user
    
    def _headers(self):
        return {"X-User-ID": self.admin_user, "Content-Type": "application/json"}
    
    async def status(self):
        """显示系统状态"""
        async with httpx.AsyncClient() as client:
            # 健康检查
            health = await client.get(f"{self.base_url}/api/v1/health")
            print(f"服务状态: {health.json()['status']}")
            print(f"版本: {health.json()['version']}")
            
            # 用户数
            profiles = await client.get(
                f"{self.base_url}/api/v1/user-profiles",
                headers=self._headers()
            )
            print(f"用户数: {profiles.json()['total']}")
            
            # 助手数
            assistants = await client.get(
                f"{self.base_url}/api/v1/assistants",
                headers=self._headers()
            )
            print(f"助手数: {assistants.json()['total']}")
    
    async def backup(self, output_file: str):
        """备份配置"""
        async with httpx.AsyncClient() as client:
            backup_data = {
                "profiles": [],
                "rules": [],
                "assistants": [],
            }
            
            # 备份用户档案
            response = await client.get(
                f"{self.base_url}/api/v1/user-profiles",
                headers=self._headers()
            )
            backup_data["profiles"] = response.json().get("profiles", [])
            
            # 备份助手
            response = await client.get(
                f"{self.base_url}/api/v1/assistants",
                headers=self._headers()
            )
            backup_data["assistants"] = response.json().get("assistants", [])
            
            # 备份规则
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.admin_user}/rules",
                headers=self._headers()
            )
            backup_data["rules"] = response.json().get("rules", [])
            
            with open(output_file, "w") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            print(f"备份完成: {output_file}")
            print(f"  - 用户档案: {len(backup_data['profiles'])}")
            print(f"  - 助手: {len(backup_data['assistants'])}")
            print(f"  - 规则: {len(backup_data['rules'])}")

async def main():
    parser = argparse.ArgumentParser(description="DataAgent 管理工具")
    parser.add_argument("command", choices=["status", "backup"])
    parser.add_argument("--output", "-o", default="backup.json")
    parser.add_argument("--url", default=BASE_URL)
    
    args = parser.parse_args()
    admin = DataAgentAdmin(args.url)
    
    if args.command == "status":
        await admin.status()
    elif args.command == "backup":
        await admin.backup(args.output)

if __name__ == "__main__":
    asyncio.run(main())
```
