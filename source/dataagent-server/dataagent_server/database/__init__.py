"""Database module for DataAgent Server.

This module provides multi-tenant database support with:
- ORM models with s_ prefix for system tables
- _rel suffix for relationship tables
- Support for both SQLite (development) and MySQL (production)
- Migration management
"""

from dataagent_server.database.models import (
    Base,
    SUser,
    SApiKey,
    SSession,
    SMessage,
    SSessionMessageRel,
    SMcpServer,
    SWorkspace,
    SUserWorkspaceRel,
    SRule,
    SSkill,
    SAuditLog,
    SSchemaVersion,
)
from dataagent_server.database.factory import DatabaseFactory, get_db_session

__all__ = [
    "Base",
    "SUser",
    "SApiKey",
    "SSession",
    "SMessage",
    "SSessionMessageRel",
    "SMcpServer",
    "SWorkspace",
    "SUserWorkspaceRel",
    "SRule",
    "SSkill",
    "SAuditLog",
    "SSchemaVersion",
    "DatabaseFactory",
    "get_db_session",
]
