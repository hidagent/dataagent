# DataAgent CLI MCP 配置示例

本目录展示如何在 DataAgent CLI 中配置和使用 MCP (Model Context Protocol) 服务器。

## 📁 目录结构

```
examples/mcp/
├── README.md                    # 本文档
├── mcp.json                     # MCP 配置文件示例
├── mcp-minimal.json             # 最小配置示例
└── mcp-advanced.json            # 高级配置示例
```

## 🚀 快速开始

### 1. 配置 MCP 服务器

将 `mcp.json` 文件放到以下位置之一：

```bash
# 方式1: Agent 级别配置（推荐）
~/.deepagents/{agent_name}/mcp.json

# 方式2: 启动时指定配置文件
dataagent --mcp-config /path/to/mcp.json
```

### 2. 复制示例配置

```bash
# 复制到默认 agent 目录
mkdir -p ~/.deepagents/agent
cp examples/mcp/mcp.json ~/.deepagents/agent/mcp.json
```

### 3. CLI 命令

```bash
# 启动 DataAgent CLI
dataagent

# 查看已配置的 MCP 服务器
/mcp

# 重新加载 MCP 配置
/mcp reload
```

## 📝 配置文件格式

### 基本结构

```json
{
  "mcpServers": {
    "server-name": {
      "command": "命令",
      "args": ["参数1", "参数2"],
      "env": {
        "ENV_VAR": "value"
      },
      "disabled": false,
      "autoApprove": ["tool1", "tool2"]
    }
  }
}
```

### 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是* | 启动命令（stdio 模式） |
| `args` | string[] | 否 | 命令参数 |
| `env` | object | 否 | 环境变量 |
| `url` | string | 是* | SSE/WebSocket URL（网络模式） |
| `transport` | string | 否 | 传输类型: `stdio`, `sse`, `websocket` |
| `disabled` | boolean | 否 | 是否禁用，默认 false |
| `autoApprove` | string[] | 否 | 自动批准的工具列表 |

*注: `command` 和 `url` 二选一

## 🔧 常用 MCP 服务器配置

### 1. 文件系统服务器

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
      "autoApprove": ["read_file", "list_directory"]
    }
  }
}
```

### 2. GitHub 服务器

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

### 3. PostgreSQL 服务器

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://user:pass@localhost:5432/db"
      }
    }
  }
}
```

### 4. 使用 uvx (Python)

```json
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### 5. SSE 远程服务器

```json
{
  "mcpServers": {
    "remote-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse"
    }
  }
}
```

## 🛡️ 安全建议

1. **不要在配置文件中硬编码敏感信息**
   - 使用环境变量引用: `"$ENV_VAR_NAME"`
   - 或在 shell 中设置环境变量后启动

2. **限制文件系统访问范围**
   - 只授权必要的目录
   - 使用 `autoApprove` 谨慎

3. **定期审查 MCP 服务器权限**

## 📚 更多资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)
