"""Abstract session store interface for DataAgent Core."""

from abc import ABC, abstractmethod

from dataagent_core.session.state import Session


class SessionStore(ABC):
    """Abstract base class for session storage.
    
    Implementations can provide different storage backends:
    - MemorySessionStore: In-memory storage (for development/testing)
    - RedisSessionStore: Redis-based storage (for production)
    - DatabaseSessionStore: SQL database storage (for persistence)
    """
    
    @abstractmethod
    async def create(self, user_id: str, assistant_id: str) -> Session:
        """Create a new session.
        
        Args:
            user_id: Identifier for the user.
            assistant_id: Identifier for the assistant/agent.
            
        Returns:
            The newly created Session.
        """
        ...
    
    @abstractmethod
    async def get(self, session_id: str) -> Session | None:
        """Get a session by ID.
        
        Args:
            session_id: The session identifier.
            
        Returns:
            The Session if found, None otherwise.
        """
        ...
    
    @abstractmethod
    async def update(self, session: Session) -> None:
        """Update an existing session.
        
        Args:
            session: The session to update.
        """
        ...
    
    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete a session.
        
        Args:
            session_id: The session identifier to delete.
        """
        ...
    
    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Session]:
        """List all sessions for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            List of sessions belonging to the user.
        """
        ...
    
    @abstractmethod
    async def list_by_assistant(self, assistant_id: str) -> list[Session]:
        """List all sessions for an assistant.
        
        Args:
            assistant_id: The assistant identifier.
            
        Returns:
            List of sessions for the assistant.
        """
        ...
    
    @abstractmethod
    async def cleanup_expired(self, timeout_seconds: float) -> int:
        """Clean up expired sessions.
        
        Args:
            timeout_seconds: Sessions inactive longer than this are expired.
            
        Returns:
            Number of sessions cleaned up.
        """
        ...
