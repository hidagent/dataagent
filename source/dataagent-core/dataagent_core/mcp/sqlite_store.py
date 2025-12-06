"""SQLite MCP configuration storage backend."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from dataagent_core.mcp.config import MCPConfig, MCPServerConfig
from dataagent_core.mcp.store import MCPConfigStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class SQLiteMCPConfigStore(MCPConfigStore):
    """SQLite-based MCP configuration storage.
    
    Ideal for development and single-instance deployments.
    
    Args:
        db_path: Path to SQLite database file.
        engine: Optional existing SQLAlchemy async engine to share.
    """
    
    def __init__(
        self,
        db_path: str | Path | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        if engine is not None:
            self._engine = engine
            self._owns_engine = False
        else:
            if db_path is None:
                db_path = Path.home() / ".dataagent" / "dataagent.db"
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            url = f"sqlite+aiosqlite:///{db_path}"
            self._engine = create_async_engine(url, echo=False)
            self._owns_engine = True
        
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._table_created = False

    async def init_tables(self) -> None:
        """Create the mcp_servers table if it doesn't exist."""
        if self._table_created:
            return

        from sqlalchemy import text

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            server_name TEXT NOT NULL,
            command TEXT DEFAULT '',
            args TEXT,
            env TEXT,
            url TEXT,
            transport TEXT DEFAULT 'sse',
            headers TEXT,
            disabled INTEGER DEFAULT 0,
            auto_approve TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, server_name)
        )
        """

        async with self._engine.begin() as conn:
            await conn.execute(text(create_table_sql))
            # Add columns if not exists (for migration)
            for col in ["url TEXT", "transport TEXT DEFAULT 'sse'", "headers TEXT"]:
                try:
                    await conn.execute(
                        text(f"ALTER TABLE mcp_servers ADD COLUMN {col}")
                    )
                except Exception:
                    pass  # Column already exists

        self._table_created = True
        logger.info("SQLite MCP servers table initialized")
    
    async def close(self) -> None:
        """Close the database engine if owned."""
        if self._owns_engine:
            await self._engine.dispose()
    
    async def get_user_config(self, user_id: str) -> MCPConfig:
        await self.init_tables()

        from sqlalchemy import text

        query = text("""
            SELECT server_name, command, args, env, url, transport, headers, disabled, auto_approve
            FROM mcp_servers
            WHERE user_id = :user_id
        """)

        async with self._engine.connect() as conn:
            result = await conn.execute(query, {"user_id": user_id})
            rows = result.fetchall()

        servers = {}
        for row in rows:
            server = MCPServerConfig(
                name=row[0],
                command=row[1] or "",
                args=json.loads(row[2]) if row[2] else [],
                env=json.loads(row[3]) if row[3] else {},
                url=row[4],
                transport=row[5] or "sse",
                headers=json.loads(row[6]) if row[6] else {},
                disabled=bool(row[7]),
                auto_approve=json.loads(row[8]) if row[8] else [],
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
        
        async with self._engine.begin() as conn:
            result = await conn.execute(query, {"user_id": user_id})
            return result.rowcount > 0
    
    async def add_server(self, user_id: str, server: MCPServerConfig) -> None:
        await self.init_tables()

        from sqlalchemy import text

        # SQLite uses INSERT OR REPLACE for upsert
        query = text("""
            INSERT OR REPLACE INTO mcp_servers 
            (user_id, server_name, command, args, env, url, transport, headers, disabled, auto_approve)
            VALUES (:user_id, :server_name, :command, :args, :env, :url, :transport, :headers, :disabled, :auto_approve)
        """)

        async with self._engine.begin() as conn:
            await conn.execute(
                query,
                {
                    "user_id": user_id,
                    "server_name": server.name,
                    "command": server.command,
                    "args": json.dumps(server.args),
                    "env": json.dumps(server.env),
                    "url": server.url,
                    "transport": server.transport or "sse",
                    "headers": json.dumps(server.headers) if server.headers else None,
                    "disabled": 1 if server.disabled else 0,
                    "auto_approve": json.dumps(server.auto_approve),
                },
            )
    
    async def remove_server(self, user_id: str, server_name: str) -> bool:
        await self.init_tables()
        
        from sqlalchemy import text
        
        query = text("""
            DELETE FROM mcp_servers
            WHERE user_id = :user_id AND server_name = :server_name
        """)
        
        async with self._engine.begin() as conn:
            result = await conn.execute(query, {
                "user_id": user_id,
                "server_name": server_name,
            })
            return result.rowcount > 0
    
    async def get_server(self, user_id: str, server_name: str) -> MCPServerConfig | None:
        await self.init_tables()

        from sqlalchemy import text

        query = text("""
            SELECT server_name, command, args, env, url, transport, headers, disabled, auto_approve
            FROM mcp_servers
            WHERE user_id = :user_id AND server_name = :server_name
        """)

        async with self._engine.connect() as conn:
            result = await conn.execute(
                query,
                {
                    "user_id": user_id,
                    "server_name": server_name,
                },
            )
            row = result.fetchone()

        if not row:
            return None

        return MCPServerConfig(
            name=row[0],
            command=row[1] or "",
            args=json.loads(row[2]) if row[2] else [],
            env=json.loads(row[3]) if row[3] else {},
            url=row[4],
            transport=row[5] or "sse",
            headers=json.loads(row[6]) if row[6] else {},
            disabled=bool(row[7]),
            auto_approve=json.loads(row[8]) if row[8] else [],
        )
