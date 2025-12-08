"""Database module for DataAgent Core.

This module provides:
- Database models (SQLAlchemy ORM)
- Migration management (Alembic-style versioning)
- Multi-database support (SQLite3, PostgreSQL)
- Database factory for unified store creation

Usage:
    from dataagent_core.database import DatabaseFactory
    
    # SQLite (default)
    factory = DatabaseFactory.sqlite()
    await factory.init_schema()
    
    # PostgreSQL
    factory = DatabaseFactory.postgres("postgres+aiopostgres://user:pass@localhost/db")
    await factory.init_schema()
    
    # Create stores
    user_store = await factory.create_user_store()
    session_store = await factory.create_session_store()
    mcp_store = await factory.create_mcp_store()
"""

from dataagent_core.database.models import (
    Base,
    UserModel,
    SessionModel,
    MessageModel,
    MCPServerModel,
    WorkspaceModel,
    RuleModel,
    SkillModel,
    AuditLogModel,
    APIKeyModel,
    SchemaVersionModel,
)
from dataagent_core.database.migration import MigrationManager
from dataagent_core.database.factory import DatabaseFactory, create_default_factory

__all__ = [
    # Models
    "Base",
    "UserModel",
    "SessionModel",
    "MessageModel",
    "MCPServerModel",
    "WorkspaceModel",
    "RuleModel",
    "SkillModel",
    "AuditLogModel",
    "APIKeyModel",
    "SchemaVersionModel",
    # Migration
    "MigrationManager",
    # Factory
    "DatabaseFactory",
    "create_default_factory",
]
