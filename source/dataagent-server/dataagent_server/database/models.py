"""ORM models for DataAgent Server database.

All system tables use s_ prefix.
All relationship tables use _rel suffix.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class SSchemaVersion(Base):
    """Schema version tracking table."""
    
    __tablename__ = "s_schema_version"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(32), unique=True, nullable=False)
    description = Column(String(256))
    checksum = Column(String(64))
    applied_at = Column(DateTime, default=func.now())
    applied_by = Column(String(64))


class SUser(Base):
    """User account table."""
    
    __tablename__ = "s_user"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    user_account = Column(String(128), comment="Domain account (LDAP/AD)")
    user_source = Column(String(32), nullable=False, default="local",
                        comment="User source: local, ldap, oauth, sso")
    display_name = Column(String(128), nullable=False)
    email = Column(String(256))
    password_hash = Column(String(256))
    department = Column(String(128))
    role = Column(String(64))
    status = Column(String(32), default="active", comment="active, inactive, suspended")
    custom_fields = Column(Text, comment="JSON custom fields")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime)
    
    # Relationships
    api_keys = relationship("SApiKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("SSession", back_populates="user", cascade="all, delete-orphan")
    mcp_servers = relationship("SMcpServer", back_populates="user", cascade="all, delete-orphan")
    rules = relationship("SRule", back_populates="user", cascade="all, delete-orphan")
    skills = relationship("SSkill", back_populates="user", cascade="all, delete-orphan")
    workspace_rels = relationship("SUserWorkspaceRel", back_populates="user", cascade="all, delete-orphan")


class SApiKey(Base):
    """API key table."""
    
    __tablename__ = "s_api_key"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("s_user.user_id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(256), nullable=False)
    name = Column(String(128))
    scopes = Column(Text, comment="JSON array of scopes")
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("SUser", back_populates="api_keys")
    
    __table_args__ = (
        Index("ix_s_api_key_user_id", "user_id"),
    )


class SSession(Base):
    """Session table."""
    
    __tablename__ = "s_session"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("s_user.user_id", ondelete="CASCADE"), nullable=False)
    assistant_id = Column(String(64), nullable=False)
    title = Column(String(256))
    state = Column(Text, comment="JSON session state")
    extra_data = Column(Text, comment="JSON metadata")
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    is_archived = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("SUser", back_populates="sessions")
    message_rels = relationship("SSessionMessageRel", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_s_session_user_id", "user_id"),
    )


class SMessage(Base):
    """Message entity table."""
    
    __tablename__ = "s_message"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(64), unique=True, nullable=False, index=True)
    role = Column(String(32), nullable=False, comment="user, assistant, system, tool")
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, comment="JSON tool calls")
    tool_call_id = Column(String(64))
    extra_data = Column(Text, comment="JSON metadata")
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    session_rels = relationship("SSessionMessageRel", back_populates="message", cascade="all, delete-orphan")


class SSessionMessageRel(Base):
    """Session-Message relationship table."""
    
    __tablename__ = "s_session_message_rel"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("s_session.session_id", ondelete="CASCADE"), nullable=False)
    message_id = Column(String(64), ForeignKey("s_message.message_id", ondelete="CASCADE"), nullable=False)
    sequence_number = Column(Integer, nullable=False, comment="Message order in session")
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    session = relationship("SSession", back_populates="message_rels")
    message = relationship("SMessage", back_populates="session_rels")
    
    __table_args__ = (
        UniqueConstraint("session_id", "message_id", name="uq_session_message"),
        UniqueConstraint("session_id", "sequence_number", name="uq_session_sequence"),
        Index("ix_s_session_message_rel_session_id", "session_id"),
    )


class SMcpServer(Base):
    """MCP server configuration table."""
    
    __tablename__ = "s_mcp_server"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("s_user.user_id", ondelete="CASCADE"), nullable=False)
    server_name = Column(String(128), nullable=False)
    command = Column(String(512))
    args = Column(Text, comment="JSON array of arguments")
    env = Column(Text, comment="JSON environment variables")
    url = Column(String(512))
    transport = Column(String(32), default="stdio", comment="stdio, sse, streamable_http")
    headers = Column(Text, comment="JSON HTTP headers")
    auto_approve = Column(Text, comment="JSON array of auto-approve tools")
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("SUser", back_populates="mcp_servers")
    
    __table_args__ = (
        UniqueConstraint("user_id", "server_name", name="uq_user_mcp_server"),
        Index("ix_s_mcp_server_user_id", "user_id"),
    )


class SWorkspace(Base):
    """Workspace entity table."""
    
    __tablename__ = "s_workspace"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    path = Column(String(512), nullable=False)
    description = Column(Text)
    max_size_bytes = Column(BigInteger, default=1073741824, comment="1GB default")
    max_files = Column(Integer, default=10000)
    current_size_bytes = Column(BigInteger, default=0)
    current_file_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    settings = Column(Text, comment="JSON settings")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_accessed_at = Column(DateTime)
    
    # Relationships
    user_rels = relationship("SUserWorkspaceRel", back_populates="workspace", cascade="all, delete-orphan")


class SUserWorkspaceRel(Base):
    """User-Workspace relationship table."""
    
    __tablename__ = "s_user_workspace_rel"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("s_user.user_id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(String(64), ForeignKey("s_workspace.workspace_id", ondelete="CASCADE"), nullable=False)
    is_default = Column(Boolean, default=False)
    permission = Column(String(32), default="read_write", comment="read_only, read_write, admin")
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("SUser", back_populates="workspace_rels")
    workspace = relationship("SWorkspace", back_populates="user_rels")
    
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace"),
        Index("ix_s_user_workspace_rel_user_id", "user_id"),
    )


class SRule(Base):
    """User rule table."""
    
    __tablename__ = "s_rule"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("s_user.user_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    scope = Column(String(32), default="user", comment="global, user, project, session")
    priority = Column(Integer, default=50, comment="1-100, higher is more important")
    is_active = Column(Boolean, default=True)
    extra_data = Column(Text, comment="JSON metadata")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("SUser", back_populates="rules")
    
    __table_args__ = (
        Index("ix_s_rule_user_id", "user_id"),
    )


class SSkill(Base):
    """User skill table."""
    
    __tablename__ = "s_skill"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("s_user.user_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    category = Column(String(64))
    tags = Column(Text, comment="JSON array of tags")
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    extra_data = Column(Text, comment="JSON metadata")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("SUser", back_populates="skills")
    
    __table_args__ = (
        Index("ix_s_skill_user_id", "user_id"),
    )


class SAuditLog(Base):
    """Security audit log table."""
    
    __tablename__ = "s_audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(64), unique=True, nullable=False, index=True)
    requesting_user_id = Column(String(64))
    target_user_id = Column(String(64))
    resource_type = Column(String(64), nullable=False, comment="user, session, mcp_server, etc.")
    resource_id = Column(String(64))
    action = Column(String(32), nullable=False, comment="create, read, update, delete")
    result = Column(String(32), nullable=False, comment="success, denied, error")
    details = Column(Text, comment="JSON details")
    ip_address = Column(String(64))
    user_agent = Column(String(512))
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("ix_s_audit_log_created_at", "created_at"),
        Index("ix_s_audit_log_requesting_user_id", "requesting_user_id"),
    )
