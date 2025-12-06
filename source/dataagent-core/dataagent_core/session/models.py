"""SQLAlchemy ORM models for session storage.

Compatible with SQLAlchemy 1.4+ and 2.0+.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SessionModel(Base):
    """SQLAlchemy model for sessions table."""
    
    __tablename__ = "sessions"
    
    session_id = Column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(String(64), nullable=False, index=True)
    assistant_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    last_active = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    state = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    
    # Relationship to messages
    messages = relationship(
        "MessageModel", back_populates="session", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_last_active", "last_active"),
    )


class MessageModel(Base):
    """SQLAlchemy model for messages table."""
    
    __tablename__ = "messages"
    
    message_id = Column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id = Column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    role = Column(
        Enum("user", "assistant", "system", name="message_role"), nullable=False
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    metadata_ = Column("metadata", JSON, nullable=True)
    
    # Relationship to session
    session = relationship("SessionModel", back_populates="messages")
    
    __table_args__ = (
        Index("idx_session_id", "session_id"),
        Index("idx_created_at", "created_at"),
    )
