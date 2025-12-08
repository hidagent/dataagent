"""SQLAlchemy ORM models for DataAgent multi-tenant system.

This module defines all database models for the multi-tenant backend:
- UserModel: User accounts and authentication
- SessionModel: User chat sessions
- MessageModel: Chat messages within sessions
- MCPServerModel: MCP server configurations per user
- WorkspaceModel: User workspace metadata
- RuleModel: User-specific rules
- SkillModel: User-specific skills
- AuditLogModel: Security audit logs
- APIKeyModel: API keys for authentication

All tables support multi-tenant isolation via user_id foreign keys.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =============================================================================
# User Management Tables
# =============================================================================

class UserModel(Base):
    """User accounts table.
    
    Stores user authentication and profile information.
    This is the central table for multi-tenant isolation.
    """
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    email = Column(String(256), nullable=True, index=True)
    password_hash = Column(String(256), nullable=True)  # For local auth
    department = Column(String(128), nullable=True)
    role = Column(String(64), nullable=True)
    status = Column(
        Enum("active", "inactive", "suspended", name="user_status"),
        default="active",
        nullable=False,
    )
    custom_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    mcp_servers = relationship("MCPServerModel", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("WorkspaceModel", back_populates="user", cascade="all, delete-orphan")
    rules = relationship("RuleModel", back_populates="user", cascade="all, delete-orphan")
    skills = relationship("SkillModel", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKeyModel", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_status", "status"),
        Index("idx_users_department", "department"),
    )


class APIKeyModel(Base):
    """API keys for user authentication.
    
    Supports multiple API keys per user with expiration and scopes.
    """
    
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(256), nullable=False)  # Hashed API key
    name = Column(String(128), nullable=False)  # Key description
    scopes = Column(JSON, nullable=True)  # Allowed scopes/permissions
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="api_keys")
    
    __table_args__ = (
        Index("idx_api_keys_user_id", "user_id"),
        Index("idx_api_keys_expires_at", "expires_at"),
    )


# =============================================================================
# Session Management Tables
# =============================================================================

class SessionModel(Base):
    """User chat sessions table.
    
    Stores session metadata and state for multi-turn conversations.
    """
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    assistant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=True)  # Session title/summary
    state = Column(JSON, nullable=True)  # Session state data
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    last_active = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="sessions")
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_last_active", "last_active"),
        Index("idx_sessions_user_assistant", "user_id", "assistant_id"),
    )


class MessageModel(Base):
    """Chat messages within sessions.
    
    Stores individual messages with role and content.
    """
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(
        String(64), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4())
    )
    session_id = Column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    role = Column(
        Enum("user", "assistant", "system", "tool", name="message_role"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)  # For assistant tool calls
    tool_call_id = Column(String(64), nullable=True)  # For tool responses
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # Relationships
    session = relationship("SessionModel", back_populates="messages")
    
    __table_args__ = (
        Index("idx_messages_session_id", "session_id"),
        Index("idx_messages_created_at", "created_at"),
    )


# =============================================================================
# MCP Configuration Tables
# =============================================================================

class MCPServerModel(Base):
    """MCP server configurations per user.
    
    Stores MCP server connection settings with multi-tenant isolation.
    """
    
    __tablename__ = "mcp_servers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    server_name = Column(String(128), nullable=False)
    
    # Connection settings
    command = Column(String(512), nullable=True)  # For stdio transport
    args = Column(JSON, nullable=True)
    env = Column(JSON, nullable=True)
    url = Column(String(512), nullable=True)  # For SSE/HTTP transport
    transport = Column(String(32), default="stdio", nullable=False)
    headers = Column(JSON, nullable=True)  # For HTTP transport
    
    # Configuration
    disabled = Column(Boolean, default=False, nullable=False)
    auto_approve = Column(JSON, nullable=True)  # Auto-approved tools
    timeout_seconds = Column(Integer, default=30, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="mcp_servers")
    
    __table_args__ = (
        Index("idx_mcp_servers_user_id", "user_id"),
        Index("idx_mcp_servers_user_server", "user_id", "server_name", unique=True),
    )


# =============================================================================
# Workspace Tables
# =============================================================================

class WorkspaceModel(Base):
    """User workspace metadata.
    
    Stores workspace configuration and quota information.
    Actual files are stored in the filesystem.
    """
    
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(
        String(64), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    path = Column(String(512), nullable=False)  # Filesystem path
    
    # Quota settings
    max_size_bytes = Column(BigInteger, default=1073741824, nullable=False)  # 1GB
    max_files = Column(Integer, default=10000, nullable=False)
    current_size_bytes = Column(BigInteger, default=0, nullable=False)
    current_file_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    settings = Column(JSON, nullable=True)  # Workspace-specific settings
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="workspaces")
    
    __table_args__ = (
        Index("idx_workspaces_user_id", "user_id"),
        Index("idx_workspaces_user_default", "user_id", "is_default"),
    )


# =============================================================================
# Rules Tables
# =============================================================================

class RuleModel(Base):
    """User-specific rules.
    
    Stores rules that guide agent behavior per user.
    """
    
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rule_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    
    # Rule configuration
    scope = Column(
        Enum("global", "user", "project", "session", name="rule_scope"),
        default="user",
        nullable=False,
    )
    inclusion = Column(
        Enum("always", "fileMatch", "manual", name="rule_inclusion"),
        default="always",
        nullable=False,
    )
    file_match_pattern = Column(String(256), nullable=True)
    priority = Column(Integer, default=50, nullable=False)
    override = Column(Boolean, default=False, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="rules")
    
    __table_args__ = (
        Index("idx_rules_user_id", "user_id"),
        Index("idx_rules_user_name", "user_id", "rule_name", unique=True),
        Index("idx_rules_scope", "scope"),
    )


# =============================================================================
# Skills Tables
# =============================================================================

class SkillModel(Base):
    """User-specific skills.
    
    Stores reusable skill definitions per user.
    """
    
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)  # Skill definition/prompt
    
    # Skill configuration
    category = Column(String(64), nullable=True)
    tags = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)  # Input parameters schema
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="skills")
    
    __table_args__ = (
        Index("idx_skills_user_id", "user_id"),
        Index("idx_skills_user_name", "user_id", "skill_name", unique=True),
        Index("idx_skills_category", "category"),
    )


# =============================================================================
# Audit Log Tables
# =============================================================================

class AuditLogModel(Base):
    """Security audit logs.
    
    Records all security-relevant operations for compliance and debugging.
    """
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now, index=True)
    
    # Actor information
    requesting_user_id = Column(String(64), nullable=False, index=True)
    target_user_id = Column(String(64), nullable=True, index=True)
    
    # Resource information
    resource_type = Column(
        Enum("user", "session", "message", "mcp", "workspace", "rule", "skill", "api_key", name="resource_type"),
        nullable=False,
    )
    resource_id = Column(String(128), nullable=True)
    
    # Action information
    action = Column(
        Enum("create", "read", "update", "delete", "execute", "login", "logout", name="audit_action"),
        nullable=False,
    )
    result = Column(
        Enum("success", "failure", "denied", name="audit_result"),
        nullable=False,
    )
    
    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(512), nullable=True)
    session_id = Column(String(64), nullable=True)
    request_id = Column(String(64), nullable=True)
    
    # Details
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_audit_logs_requesting_user", "requesting_user_id"),
        Index("idx_audit_logs_target_user", "target_user_id"),
        Index("idx_audit_logs_resource_type", "resource_type"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_timestamp_user", "timestamp", "requesting_user_id"),
    )


# =============================================================================
# Schema Version Table (for migrations)
# =============================================================================

class SchemaVersionModel(Base):
    """Database schema version tracking.
    
    Tracks applied migrations for version management.
    """
    
    __tablename__ = "schema_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(32), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=False, default=datetime.now)
    checksum = Column(String(64), nullable=True)  # For integrity verification
