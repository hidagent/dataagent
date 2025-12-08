"""Database migration management for DataAgent.

This module provides a simple migration system that supports:
- SQLite3 and PostgreSQL databases
- Version tracking
- Forward migrations
- Rollback support (where possible)

Usage:
    manager = MigrationManager(engine)
    await manager.init()
    await manager.migrate()  # Apply all pending migrations
"""

import hashlib
import logging
from datetime import datetime
from typing import Callable, Awaitable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""
    
    def __init__(
        self,
        version: str,
        description: str,
        up_sqlite: str,
        up_postgres: str,
        down_sqlite: str | None = None,
        down_postgres: str | None = None,
    ):
        self.version = version
        self.description = description
        self.up_sqlite = up_sqlite
        self.up_postgres = up_postgres
        self.down_sqlite = down_sqlite
        self.down_postgres = down_postgres
    
    def get_checksum(self) -> str:
        """Calculate checksum of migration content."""
        content = f"{self.up_sqlite}{self.up_postgres}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class MigrationManager:
    """Manages database migrations.
    
    Supports both SQLite3 and PostgreSQL databases with automatic
    dialect detection.
    """
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._dialect: str | None = None
        self._migrations: list[Migration] = []
        self._register_migrations()
    
    @property
    def dialect(self) -> str:
        """Get the database dialect (sqlite or postgres)."""
        if self._dialect is None:
            self._dialect = self.engine.dialect.name
        return self._dialect
    
    def _register_migrations(self) -> None:
        """Register all migrations in order."""
        self._migrations = [
            # V001: Initial schema
            Migration(
                version="001",
                description="Initial schema - users, sessions, messages",
                up_sqlite=MIGRATION_001_SQLITE,
                up_postgres=MIGRATION_001_POSTGRES,
                down_sqlite="DROP TABLE IF EXISTS messages; DROP TABLE IF EXISTS sessions; DROP TABLE IF EXISTS users;",
                down_postgres="DROP TABLE IF EXISTS messages; DROP TABLE IF EXISTS sessions; DROP TABLE IF EXISTS users;",
            ),
            # V002: MCP servers
            Migration(
                version="002",
                description="MCP server configurations",
                up_sqlite=MIGRATION_002_SQLITE,
                up_postgres=MIGRATION_002_POSTGRES,
                down_sqlite="DROP TABLE IF EXISTS mcp_servers;",
                down_postgres="DROP TABLE IF EXISTS mcp_servers;",
            ),
            # V003: Workspaces
            Migration(
                version="003",
                description="User workspaces",
                up_sqlite=MIGRATION_003_SQLITE,
                up_postgres=MIGRATION_003_POSTGRES,
                down_sqlite="DROP TABLE IF EXISTS workspaces;",
                down_postgres="DROP TABLE IF EXISTS workspaces;",
            ),
            # V004: Rules and Skills
            Migration(
                version="004",
                description="Rules and skills tables",
                up_sqlite=MIGRATION_004_SQLITE,
                up_postgres=MIGRATION_004_POSTGRES,
                down_sqlite="DROP TABLE IF EXISTS skills; DROP TABLE IF EXISTS rules;",
                down_postgres="DROP TABLE IF EXISTS skills; DROP TABLE IF EXISTS rules;",
            ),
            # V005: API Keys and Audit Logs
            Migration(
                version="005",
                description="API keys and audit logs",
                up_sqlite=MIGRATION_005_SQLITE,
                up_postgres=MIGRATION_005_POSTGRES,
                down_sqlite="DROP TABLE IF EXISTS audit_logs; DROP TABLE IF EXISTS api_keys;",
                down_postgres="DROP TABLE IF EXISTS audit_logs; DROP TABLE IF EXISTS api_keys;",
            ),
        ]
    
    async def init(self) -> None:
        """Initialize the schema_versions table."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS schema_versions (
            id INTEGER PRIMARY KEY {autoincrement},
            version VARCHAR(32) UNIQUE NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64)
        )
        """.format(
            autoincrement="AUTOINCREMENT" if self.dialect == "sqlite" else "AUTO_INCREMENT"
        )
        
        async with self.engine.begin() as conn:
            await conn.execute(text(create_sql))
        
        logger.info("Schema versions table initialized")
    
    async def get_current_version(self) -> str | None:
        """Get the current schema version."""
        query = text("SELECT version FROM schema_versions ORDER BY id DESC LIMIT 1")
        
        async with self.engine.connect() as conn:
            result = await conn.execute(query)
            row = result.fetchone()
            return row[0] if row else None
    
    async def get_applied_versions(self) -> list[str]:
        """Get all applied migration versions."""
        query = text("SELECT version FROM schema_versions ORDER BY id")
        
        async with self.engine.connect() as conn:
            result = await conn.execute(query)
            return [row[0] for row in result.fetchall()]
    
    async def migrate(self, target_version: str | None = None) -> list[str]:
        """Apply pending migrations.
        
        Args:
            target_version: Optional target version. If None, applies all.
            
        Returns:
            List of applied migration versions.
        """
        applied = await self.get_applied_versions()
        applied_versions = []
        
        for migration in self._migrations:
            if migration.version in applied:
                continue
            
            if target_version and migration.version > target_version:
                break
            
            await self._apply_migration(migration)
            applied_versions.append(migration.version)
        
        if applied_versions:
            logger.info(f"Applied migrations: {applied_versions}")
        else:
            logger.info("No pending migrations")
        
        return applied_versions
    
    async def _apply_migration(self, migration: Migration) -> None:
        """Apply a single migration."""
        sql = migration.up_sqlite if self.dialect == "sqlite" else migration.up_postgres
        
        async with self.engine.begin() as conn:
            # Execute migration SQL (may contain multiple statements)
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))
            
            # Record migration
            await conn.execute(
                text("""
                    INSERT INTO schema_versions (version, description, checksum)
                    VALUES (:version, :description, :checksum)
                """),
                {
                    "version": migration.version,
                    "description": migration.description,
                    "checksum": migration.get_checksum(),
                }
            )
        
        logger.info(f"Applied migration {migration.version}: {migration.description}")
    
    async def rollback(self, target_version: str) -> list[str]:
        """Rollback to a specific version.
        
        Args:
            target_version: Version to rollback to.
            
        Returns:
            List of rolled back migration versions.
        """
        applied = await self.get_applied_versions()
        rolled_back = []
        
        # Find migrations to rollback (in reverse order)
        for migration in reversed(self._migrations):
            if migration.version <= target_version:
                break
            
            if migration.version not in applied:
                continue
            
            await self._rollback_migration(migration)
            rolled_back.append(migration.version)
        
        if rolled_back:
            logger.info(f"Rolled back migrations: {rolled_back}")
        
        return rolled_back
    
    async def _rollback_migration(self, migration: Migration) -> None:
        """Rollback a single migration."""
        sql = migration.down_sqlite if self.dialect == "sqlite" else migration.down_postgres
        
        if not sql:
            raise ValueError(f"Migration {migration.version} does not support rollback")
        
        async with self.engine.begin() as conn:
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))
            
            await conn.execute(
                text("DELETE FROM schema_versions WHERE version = :version"),
                {"version": migration.version}
            )
        
        logger.info(f"Rolled back migration {migration.version}")


# =============================================================================
# Migration SQL Definitions
# =============================================================================

MIGRATION_001_SQLITE = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    password_hash TEXT,
    department TEXT,
    role TEXT,
    status TEXT DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'inactive', 'suspended')),
    custom_fields TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assistant_id TEXT NOT NULL,
    title TEXT,
    state TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_archived INTEGER DEFAULT 0 NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_assistant_id ON sessions(assistant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_user_assistant ON sessions(user_id, assistant_id);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls TEXT,
    tool_call_id TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)
"""

MIGRATION_001_POSTGRES = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    email VARCHAR(256),
    password_hash VARCHAR(256),
    department VARCHAR(128),
    role VARCHAR(64),
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active' NOT NULL,
    custom_fields JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP NULL,
    INDEX idx_users_user_id (user_id),
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_status (status),
    INDEX idx_users_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    assistant_id VARCHAR(64) NOT NULL,
    title VARCHAR(256),
    state JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    is_archived BOOLEAN DEFAULT FALSE NOT NULL,
    INDEX idx_sessions_session_id (session_id),
    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_assistant_id (assistant_id),
    INDEX idx_sessions_last_active (last_active),
    INDEX idx_sessions_user_assistant (user_id, assistant_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    role ENUM('user', 'assistant', 'system', 'tool') NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSON,
    tool_call_id VARCHAR(64),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_messages_message_id (message_id),
    INDEX idx_messages_session_id (session_id),
    INDEX idx_messages_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

MIGRATION_002_SQLITE = """
-- MCP Servers table
CREATE TABLE IF NOT EXISTS mcp_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    server_name TEXT NOT NULL,
    command TEXT,
    args TEXT,
    env TEXT,
    url TEXT,
    transport TEXT DEFAULT 'stdio' NOT NULL,
    headers TEXT,
    disabled INTEGER DEFAULT 0 NOT NULL,
    auto_approve TEXT,
    timeout_seconds INTEGER DEFAULT 30 NOT NULL,
    max_retries INTEGER DEFAULT 3 NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, server_name)
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_user_id ON mcp_servers(user_id)
"""

MIGRATION_002_POSTGRES = """
-- MCP Servers table
CREATE TABLE IF NOT EXISTS mcp_servers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    server_name VARCHAR(128) NOT NULL,
    command VARCHAR(512),
    args JSON,
    env JSON,
    url VARCHAR(512),
    transport VARCHAR(32) DEFAULT 'stdio' NOT NULL,
    headers JSON,
    disabled BOOLEAN DEFAULT FALSE NOT NULL,
    auto_approve JSON,
    timeout_seconds INT DEFAULT 30 NOT NULL,
    max_retries INT DEFAULT 3 NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    UNIQUE KEY unique_user_server (user_id, server_name),
    INDEX idx_mcp_servers_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

MIGRATION_003_SQLITE = """
-- Workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    max_size_bytes INTEGER DEFAULT 1073741824 NOT NULL,
    max_files INTEGER DEFAULT 10000 NOT NULL,
    current_size_bytes INTEGER DEFAULT 0 NOT NULL,
    current_file_count INTEGER DEFAULT 0 NOT NULL,
    is_default INTEGER DEFAULT 0 NOT NULL,
    is_active INTEGER DEFAULT 1 NOT NULL,
    description TEXT,
    settings TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workspaces_workspace_id ON workspaces(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_user_default ON workspaces(user_id, is_default)
"""

MIGRATION_003_POSTGRES = """
-- Workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id INT AUTO_INCREMENT PRIMARY KEY,
    workspace_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    path VARCHAR(512) NOT NULL,
    max_size_bytes BIGINT DEFAULT 1073741824 NOT NULL,
    max_files INT DEFAULT 10000 NOT NULL,
    current_size_bytes BIGINT DEFAULT 0 NOT NULL,
    current_file_count INT DEFAULT 0 NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    description TEXT,
    settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMP NULL,
    INDEX idx_workspaces_workspace_id (workspace_id),
    INDEX idx_workspaces_user_id (user_id),
    INDEX idx_workspaces_user_default (user_id, is_default),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

MIGRATION_004_SQLITE = """
-- Rules table
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope TEXT DEFAULT 'user' NOT NULL CHECK (scope IN ('global', 'user', 'project', 'session')),
    inclusion TEXT DEFAULT 'always' NOT NULL CHECK (inclusion IN ('always', 'fileMatch', 'manual')),
    file_match_pattern TEXT,
    priority INTEGER DEFAULT 50 NOT NULL,
    override INTEGER DEFAULT 0 NOT NULL,
    enabled INTEGER DEFAULT 1 NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, rule_name)
);

CREATE INDEX IF NOT EXISTS idx_rules_user_id ON rules(user_id);
CREATE INDEX IF NOT EXISTS idx_rules_scope ON rules(scope);

-- Skills table
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category TEXT,
    tags TEXT,
    parameters TEXT,
    enabled INTEGER DEFAULT 1 NOT NULL,
    usage_count INTEGER DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_skills_user_id ON skills(user_id);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)
"""

MIGRATION_004_POSTGRES = """
-- Rules table
CREATE TABLE IF NOT EXISTS rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    scope ENUM('global', 'user', 'project', 'session') DEFAULT 'user' NOT NULL,
    inclusion ENUM('always', 'fileMatch', 'manual') DEFAULT 'always' NOT NULL,
    file_match_pattern VARCHAR(256),
    priority INT DEFAULT 50 NOT NULL,
    override BOOLEAN DEFAULT FALSE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    UNIQUE KEY unique_user_rule (user_id, rule_name),
    INDEX idx_rules_user_id (user_id),
    INDEX idx_rules_scope (scope),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Skills table
CREATE TABLE IF NOT EXISTS skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    skill_name VARCHAR(128) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category VARCHAR(64),
    tags JSON,
    parameters JSON,
    enabled BOOLEAN DEFAULT TRUE NOT NULL,
    usage_count INT DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    UNIQUE KEY unique_user_skill (user_id, skill_name),
    INDEX idx_skills_user_id (user_id),
    INDEX idx_skills_category (category),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

MIGRATION_005_SQLITE = """
-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    scopes TEXT,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);

-- Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    requesting_user_id TEXT NOT NULL,
    target_user_id TEXT,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('user', 'session', 'message', 'mcp', 'workspace', 'rule', 'skill', 'api_key')),
    resource_id TEXT,
    action TEXT NOT NULL CHECK (action IN ('create', 'read', 'update', 'delete', 'execute', 'login', 'logout')),
    result TEXT NOT NULL CHECK (result IN ('success', 'failure', 'denied')),
    ip_address TEXT,
    user_agent TEXT,
    session_id TEXT,
    request_id TEXT,
    details TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_requesting_user ON audit_logs(requesting_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target_user ON audit_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)
"""

MIGRATION_005_POSTGRES = """
-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    key_hash VARCHAR(256) NOT NULL,
    name VARCHAR(128) NOT NULL,
    scopes JSON,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_api_keys_key_id (key_id),
    INDEX idx_api_keys_user_id (user_id),
    INDEX idx_api_keys_expires_at (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    requesting_user_id VARCHAR(64) NOT NULL,
    target_user_id VARCHAR(64),
    resource_type ENUM('user', 'session', 'message', 'mcp', 'workspace', 'rule', 'skill', 'api_key') NOT NULL,
    resource_id VARCHAR(128),
    action ENUM('create', 'read', 'update', 'delete', 'execute', 'login', 'logout') NOT NULL,
    result ENUM('success', 'failure', 'denied') NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(512),
    session_id VARCHAR(64),
    request_id VARCHAR(64),
    details JSON,
    error_message TEXT,
    INDEX idx_audit_logs_timestamp (timestamp),
    INDEX idx_audit_logs_requesting_user (requesting_user_id),
    INDEX idx_audit_logs_target_user (target_user_id),
    INDEX idx_audit_logs_resource_type (resource_type),
    INDEX idx_audit_logs_action (action),
    INDEX idx_audit_logs_timestamp_user (timestamp, requesting_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""
