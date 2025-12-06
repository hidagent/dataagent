"""Session state dataclass for DataAgent Core."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Session:
    """Represents a user session with an agent.
    
    Attributes:
        session_id: Unique identifier for the session.
        user_id: Identifier for the user.
        assistant_id: Identifier for the assistant/agent.
        created_at: Timestamp when the session was created.
        last_active: Timestamp of the last activity.
        state: Mutable state dictionary for session data.
        metadata: Additional metadata for the session.
    """
    
    session_id: str
    user_id: str
    assistant_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        user_id: str,
        assistant_id: str,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Session":
        """Create a new session with generated ID if not provided."""
        now = datetime.now()
        return cls(
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            assistant_id=assistant_id,
            created_at=now,
            last_active=now,
            state=state or {},
            metadata=metadata or {},
        )
    
    def touch(self) -> None:
        """Update the last_active timestamp."""
        self.last_active = datetime.now()
    
    def is_expired(self, timeout_seconds: float) -> bool:
        """Check if the session has expired based on timeout."""
        elapsed = (datetime.now() - self.last_active).total_seconds()
        return elapsed > timeout_seconds
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "assistant_id": self.assistant_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "state": self.state,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Deserialize session from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            assistant_id=data["assistant_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            state=data.get("state", {}),
            metadata=data.get("metadata", {}),
        )
