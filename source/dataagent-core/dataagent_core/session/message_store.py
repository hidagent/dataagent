"""Abstract message store interface for DataAgent Core."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class Message:
    """Represents a chat message.
    
    Attributes:
        message_id: Unique identifier for the message.
        session_id: Session this message belongs to.
        role: Role of the message sender (user/assistant/system).
        content: Message content.
        created_at: Timestamp when the message was created.
        metadata: Additional metadata for the message.
    """
    
    message_id: str
    session_id: str
    role: str  # user, assistant, system
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        """Create a new message with generated ID."""
        return cls(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now(),
            metadata=metadata or {},
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class MessageStore(ABC):
    """Abstract base class for message storage.
    
    Implementations can provide different storage backends:
    - MemoryMessageStore: In-memory storage (for development/testing)
    - MySQLMessageStore: MySQL database storage (for production)
    """
    
    @abstractmethod
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save a message.
        
        Args:
            session_id: Session identifier.
            role: Role of the message sender (user/assistant/system).
            content: Message content.
            metadata: Optional metadata.
            
        Returns:
            The message_id of the saved message.
        """
        ...
    
    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a session.
        
        Args:
            session_id: Session identifier.
            limit: Maximum number of messages to return.
            offset: Number of messages to skip.
            
        Returns:
            List of messages ordered by created_at (oldest first).
        """
        ...
    
    @abstractmethod
    async def delete_messages(self, session_id: str) -> int:
        """Delete all messages for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Number of messages deleted.
        """
        ...
    
    @abstractmethod
    async def count_messages(self, session_id: str) -> int:
        """Count messages for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Number of messages in the session.
        """
        ...
