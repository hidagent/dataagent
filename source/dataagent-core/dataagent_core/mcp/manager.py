"""MCP connection manager for Server mode."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from dataagent_core.mcp.config import MCPConfig, MCPServerConfig

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class MCPConnection:
    """Represents a connection to an MCP server."""
    
    server_config: MCPServerConfig
    client: Any = None  # MultiServerMCPClient instance
    tools: list[BaseTool] = field(default_factory=list)
    connected: bool = False
    error: str | None = None


class MCPConnectionManager:
    """Manages MCP connections for multiple users.
    
    Supports per-user connection pools with configurable limits.
    """
    
    def __init__(
        self,
        max_connections_per_user: int = 10,
        max_total_connections: int = 100,
    ) -> None:
        """Initialize the connection manager.
        
        Args:
            max_connections_per_user: Maximum MCP connections per user.
            max_total_connections: Maximum total MCP connections.
        """
        self.max_connections_per_user = max_connections_per_user
        self.max_total_connections = max_total_connections
        
        # user_id -> {server_name -> MCPConnection}
        self._connections: dict[str, dict[str, MCPConnection]] = {}
        self._lock = asyncio.Lock()
        self._total_connections = 0
    
    async def connect(
        self,
        user_id: str,
        config: MCPConfig,
    ) -> dict[str, MCPConnection]:
        """Connect to MCP servers for a user.
        
        Args:
            user_id: The user identifier.
            config: MCP configuration with server definitions.
            
        Returns:
            Dictionary of server name to connection.
        """
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = {}
            
            user_connections = self._connections[user_id]
            enabled_servers = config.get_enabled_servers()
            
            for name, server_config in enabled_servers.items():
                if name in user_connections and user_connections[name].connected:
                    continue  # Already connected
                
                # Check limits
                if len(user_connections) >= self.max_connections_per_user:
                    logger.warning(
                        f"User {user_id} reached max connections ({self.max_connections_per_user})"
                    )
                    break
                
                if self._total_connections >= self.max_total_connections:
                    logger.warning(
                        f"Total connections limit reached ({self.max_total_connections})"
                    )
                    break
                
                # Create connection
                connection = await self._create_connection(server_config)
                user_connections[name] = connection
                if connection.connected:
                    self._total_connections += 1
            
            return user_connections
    
    async def _create_connection(
        self,
        server_config: MCPServerConfig,
    ) -> MCPConnection:
        """Create a connection to an MCP server."""
        connection = MCPConnection(server_config=server_config)
        
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            connection.error = "langchain-mcp-adapters not installed"
            logger.warning(connection.error)
            return connection
        
        try:
            mcp_config = {server_config.name: server_config.to_mcp_client_config()}
            client = MultiServerMCPClient(mcp_config)
            await client.__aenter__()
            
            connection.client = client
            connection.tools = client.get_tools()
            connection.connected = True
            logger.info(
                f"Connected to MCP server '{server_config.name}' "
                f"with {len(connection.tools)} tools"
            )
        except Exception as e:
            connection.error = str(e)
            logger.warning(f"Failed to connect to MCP server '{server_config.name}': {e}")
        
        return connection
    
    async def disconnect(self, user_id: str, server_name: str | None = None) -> None:
        """Disconnect MCP server(s) for a user.
        
        Args:
            user_id: The user identifier.
            server_name: Specific server to disconnect, or None for all.
        """
        async with self._lock:
            if user_id not in self._connections:
                return
            
            user_connections = self._connections[user_id]
            
            if server_name:
                servers_to_disconnect = [server_name] if server_name in user_connections else []
            else:
                servers_to_disconnect = list(user_connections.keys())
            
            for name in servers_to_disconnect:
                connection = user_connections.get(name)
                if connection and connection.client:
                    try:
                        await connection.client.__aexit__(None, None, None)
                        logger.info(f"Disconnected MCP server '{name}' for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Error disconnecting MCP server '{name}': {e}")
                    
                    if connection.connected:
                        self._total_connections -= 1
                
                if name in user_connections:
                    del user_connections[name]
            
            if not user_connections:
                del self._connections[user_id]
    
    async def disconnect_all(self) -> None:
        """Disconnect all MCP connections."""
        async with self._lock:
            for user_id in list(self._connections.keys()):
                await self.disconnect(user_id)
    
    def get_tools(self, user_id: str) -> list[BaseTool]:
        """Get all MCP tools for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            List of LangChain tools from connected MCP servers.
        """
        if user_id not in self._connections:
            return []
        
        tools = []
        for connection in self._connections[user_id].values():
            if connection.connected:
                tools.extend(connection.tools)
        return tools
    
    def get_connection_status(self, user_id: str) -> dict[str, dict[str, Any]]:
        """Get connection status for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            Dictionary of server name to status info.
        """
        if user_id not in self._connections:
            return {}
        
        status = {}
        for name, connection in self._connections[user_id].items():
            status[name] = {
                "connected": connection.connected,
                "tools_count": len(connection.tools),
                "error": connection.error,
            }
        return status
    
    async def health_check(self, user_id: str) -> dict[str, bool]:
        """Check health of MCP connections for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            Dictionary of server name to health status.
        """
        if user_id not in self._connections:
            return {}
        
        health = {}
        for name, connection in self._connections[user_id].items():
            # Simple health check - just verify connection state
            health[name] = connection.connected and connection.client is not None
        return health
    
    @property
    def total_connections(self) -> int:
        """Get total number of active connections."""
        return self._total_connections
    
    def get_user_count(self) -> int:
        """Get number of users with active connections."""
        return len(self._connections)
