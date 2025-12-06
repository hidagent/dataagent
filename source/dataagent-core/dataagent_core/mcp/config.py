"""MCP configuration data models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server.

    Attributes:
        name: Unique identifier for the MCP server.
        command: Command to execute (e.g., 'uvx', 'npx', 'python').
        args: Command arguments.
        env: Environment variables for the server process.
        url: HTTP/SSE URL for MCP server (alternative to command).
        transport: Transport type for URL-based servers ('sse' or 'streamable_http').
        headers: Custom HTTP headers for HTTP transport.
        disabled: Whether the server is disabled.
        auto_approve: List of tool names to auto-approve.
    """

    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    transport: str = "sse"  # 'sse' or 'streamable_http'
    headers: dict[str, str] = field(default_factory=dict)
    disabled: bool = False
    auto_approve: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPServerConfig:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url"),
            transport=data.get("transport", "sse"),
            headers=data.get("headers", {}),
            disabled=data.get("disabled", False),
            auto_approve=data.get("autoApprove", data.get("auto_approve", [])),
        )

    def to_mcp_client_config(self) -> dict[str, Any]:
        """Convert to langchain-mcp-adapters MultiServerMCPClient format."""
        if self.url:
            # HTTP transport (sse or streamable_http)
            config: dict[str, Any] = {
                "url": self.url,
                "transport": self.transport or "sse",
            }
            # 添加自定义 headers
            if self.headers:
                config["headers"] = self.headers
            return config
        else:
            # Stdio transport
            return {
                "command": self.command,
                "args": self.args,
                "env": self.env if self.env else None,
            }


@dataclass
class MCPConfig:
    """Configuration for multiple MCP servers.
    
    Attributes:
        servers: Dictionary of server name to server configuration.
    """
    
    servers: dict[str, MCPServerConfig] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (mcp.json format)."""
        mcp_servers = {}
        for name, server in self.servers.items():
            server_dict: dict[str, Any] = {}
            if server.url:
                server_dict["url"] = server.url
                server_dict["transport"] = server.transport
                if server.headers:
                    server_dict["headers"] = server.headers
            else:
                server_dict["command"] = server.command
                server_dict["args"] = server.args
                if server.env:
                    server_dict["env"] = server.env
            server_dict["disabled"] = server.disabled
            if server.auto_approve:
                server_dict["autoApprove"] = server.auto_approve
            mcp_servers[name] = server_dict
        return {"mcpServers": mcp_servers}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPConfig:
        """Create from dictionary (mcp.json format)."""
        servers = {}
        mcp_servers = data.get("mcpServers", {})
        for name, config in mcp_servers.items():
            config_with_name = {**config, "name": name}
            servers[name] = MCPServerConfig.from_dict(config_with_name)
        return cls(servers=servers)
    
    @classmethod
    def from_json_file(cls, path: Path) -> MCPConfig:
        """Load configuration from a JSON file."""
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_json_file(self, path: Path) -> None:
        """Save configuration to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_enabled_servers(self) -> dict[str, MCPServerConfig]:
        """Get only enabled servers."""
        return {
            name: server
            for name, server in self.servers.items()
            if not server.disabled
        }
    
    def to_mcp_client_config(self) -> dict[str, dict[str, Any]]:
        """Convert to langchain-mcp-adapters MultiServerMCPClient format.
        
        Returns a dict suitable for MultiServerMCPClient initialization.
        Only includes enabled servers.
        """
        return {
            name: server.to_mcp_client_config()
            for name, server in self.get_enabled_servers().items()
        }
    
    def add_server(self, server: MCPServerConfig) -> None:
        """Add or update a server configuration."""
        self.servers[server.name] = server
    
    def remove_server(self, name: str) -> bool:
        """Remove a server configuration. Returns True if removed."""
        if name in self.servers:
            del self.servers[name]
            return True
        return False
    
    def get_server(self, name: str) -> MCPServerConfig | None:
        """Get a server configuration by name."""
        return self.servers.get(name)
