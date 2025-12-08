"""MCP configuration storage backends."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from dataagent_core.mcp.config import MCPConfig, MCPServerConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class MCPConfigStore(ABC):
    """Abstract base class for MCP configuration storage."""
    
    @abstractmethod
    async def get_user_config(self, user_id: str) -> MCPConfig:
        """Get MCP configuration for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            MCPConfig instance (empty if no config exists).
        """
        pass
    
    @abstractmethod
    async def save_user_config(self, user_id: str, config: MCPConfig) -> None:
        """Save MCP configuration for a user.
        
        Args:
            user_id: The user identifier.
            config: The MCP configuration to save.
        """
        pass
    
    @abstractmethod
    async def delete_user_config(self, user_id: str) -> bool:
        """Delete MCP configuration for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            True if config was deleted, False if not found.
        """
        pass
    
    @abstractmethod
    async def add_server(
        self,
        user_id: str,
        server: MCPServerConfig,
    ) -> None:
        """Add or update a server in user's configuration.
        
        Args:
            user_id: The user identifier.
            server: The server configuration to add.
        """
        pass
    
    @abstractmethod
    async def remove_server(self, user_id: str, server_name: str) -> bool:
        """Remove a server from user's configuration.
        
        Args:
            user_id: The user identifier.
            server_name: The server name to remove.
            
        Returns:
            True if server was removed, False if not found.
        """
        pass
    
    @abstractmethod
    async def get_server(
        self,
        user_id: str,
        server_name: str,
    ) -> MCPServerConfig | None:
        """Get a specific server configuration.
        
        Args:
            user_id: The user identifier.
            server_name: The server name.
            
        Returns:
            Server configuration or None if not found.
        """
        pass


class MemoryMCPConfigStore(MCPConfigStore):
    """In-memory MCP configuration storage."""
    
    def __init__(self) -> None:
        self._configs: dict[str, MCPConfig] = {}
    
    async def get_user_config(self, user_id: str) -> MCPConfig:
        return self._configs.get(user_id, MCPConfig())
    
    async def save_user_config(self, user_id: str, config: MCPConfig) -> None:
        self._configs[user_id] = config
    
    async def delete_user_config(self, user_id: str) -> bool:
        if user_id in self._configs:
            del self._configs[user_id]
            return True
        return False
    
    async def add_server(
        self,
        user_id: str,
        server: MCPServerConfig,
    ) -> None:
        config = await self.get_user_config(user_id)
        config.add_server(server)
        await self.save_user_config(user_id, config)
    
    async def remove_server(self, user_id: str, server_name: str) -> bool:
        config = await self.get_user_config(user_id)
        result = config.remove_server(server_name)
        if result:
            await self.save_user_config(user_id, config)
        return result
    
    async def get_server(
        self,
        user_id: str,
        server_name: str,
    ) -> MCPServerConfig | None:
        config = await self.get_user_config(user_id)
        return config.get_server(server_name)


class PostgresMCPConfigStore(MCPConfigStore):
    """PostgreSQL-based MCP configuration storage."""
    
    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize with SQLAlchemy async engine.
        
        Args:
            engine: SQLAlchemy async engine instance.
        """
        self.engine = engine
        self._table_created = False
    
    async def init_tables(self) -> None:
        """Create the mcp_servers table if it doesn't exist."""
        if self._table_created:
            return
        
        from sqlalchemy import text
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            server_name VARCHAR(255) NOT NULL,
            command VARCHAR(255) NOT NULL,
            args JSONB,
            env JSONB,
            disabled BOOLEAN DEFAULT FALSE,
            auto_approve JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, server_name)
        )
        """
        
        async with self.engine.begin() as conn:
            await conn.execute(text(create_table_sql))
            # Create index if not exists
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_mcp_servers_user_id ON mcp_servers(user_id)"
            ))
        
        self._table_created = True
        logger.info("PostgreSQL MCP servers table initialized")
    
    async def get_user_config(self, user_id: str) -> MCPConfig:
        await self.init_tables()
        
        from sqlalchemy import text
        
        query = text("""
            SELECT server_name, command, args, env, disabled, auto_approve
            FROM mcp_servers
            WHERE user_id = :user_id
        """)
        
        async with self.engine.connect() as conn:
            result = await conn.execute(query, {"user_id": user_id})
            rows = result.fetchall()
        
        servers = {}
        for row in rows:
            server = MCPServerConfig(
                name=row[0],
                command=row[1],
                args=json.loads(row[2]) if row[2] else [],
                env=json.loads(row[3]) if row[3] else {},
                disabled=bool(row[4]),
                auto_approve=json.loads(row[5]) if row[5] else [],
            )
            servers[server.name] = server
        
        return MCPConfig(servers=servers)
    
    async def save_user_config(self, user_id: str, config: MCPConfig) -> None:
        await self.init_tables()
        
        # Delete existing and insert new
        await self.delete_user_config(user_id)
        
        for server in config.servers.values():
            await self.add_server(user_id, server)
    
    async def delete_user_config(self, user_id: str) -> bool:
        await self.init_tables()
        
        from sqlalchemy import text
        
        query = text("DELETE FROM mcp_servers WHERE user_id = :user_id")
        
        async with self.engine.begin() as conn:
            result = await conn.execute(query, {"user_id": user_id})
            return result.rowcount > 0
    
    async def add_server(
        self,
        user_id: str,
        server: MCPServerConfig,
    ) -> None:
        await self.init_tables()
        
        from sqlalchemy import text
        
        query = text("""
            INSERT INTO mcp_servers (user_id, server_name, command, args, env, disabled, auto_approve)
            VALUES (:user_id, :server_name, :command, :args, :env, :disabled, :auto_approve)
            ON CONFLICT (user_id, server_name) DO UPDATE SET
                command = EXCLUDED.command,
                args = EXCLUDED.args,
                env = EXCLUDED.env,
                disabled = EXCLUDED.disabled,
                auto_approve = EXCLUDED.auto_approve,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        async with self.engine.begin() as conn:
            await conn.execute(query, {
                "user_id": user_id,
                "server_name": server.name,
                "command": server.command,
                "args": json.dumps(server.args),
                "env": json.dumps(server.env),
                "disabled": server.disabled,
                "auto_approve": json.dumps(server.auto_approve),
            })
    
    async def remove_server(self, user_id: str, server_name: str) -> bool:
        await self.init_tables()
        
        from sqlalchemy import text
        
        query = text("""
            DELETE FROM mcp_servers
            WHERE user_id = :user_id AND server_name = :server_name
        """)
        
        async with self.engine.begin() as conn:
            result = await conn.execute(query, {
                "user_id": user_id,
                "server_name": server_name,
            })
            return result.rowcount > 0
    
    async def get_server(
        self,
        user_id: str,
        server_name: str,
    ) -> MCPServerConfig | None:
        await self.init_tables()
        
        from sqlalchemy import text
        
        query = text("""
            SELECT server_name, command, args, env, disabled, auto_approve
            FROM mcp_servers
            WHERE user_id = :user_id AND server_name = :server_name
        """)
        
        async with self.engine.connect() as conn:
            result = await conn.execute(query, {
                "user_id": user_id,
                "server_name": server_name,
            })
            row = result.fetchone()
        
        if not row:
            return None
        
        return MCPServerConfig(
            name=row[0],
            command=row[1],
            args=json.loads(row[2]) if row[2] else [],
            env=json.loads(row[3]) if row[3] else {},
            disabled=bool(row[4]),
            auto_approve=json.loads(row[5]) if row[5] else [],
        )
