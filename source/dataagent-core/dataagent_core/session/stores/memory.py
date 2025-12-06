"""In-memory session store implementation."""

import asyncio
from datetime import datetime

from dataagent_core.session.state import Session
from dataagent_core.session.store import SessionStore


class MemorySessionStore(SessionStore):
    """In-memory session store for development and testing.
    
    This implementation stores sessions in a dictionary and is not
    suitable for production use with multiple processes.
    """
    
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
    
    async def create(self, user_id: str, assistant_id: str) -> Session:
        """Create a new session."""
        session = Session.create(user_id=user_id, assistant_id=assistant_id)
        async with self._lock:
            self._sessions[session.session_id] = session
        return session
    
    async def get(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        async with self._lock:
            return self._sessions.get(session_id)
    
    async def update(self, session: Session) -> None:
        """Update an existing session.
        
        Note: This method does NOT automatically call touch().
        The caller is responsible for updating last_active if needed.
        """
        async with self._lock:
            if session.session_id in self._sessions:
                self._sessions[session.session_id] = session
    
    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        async with self._lock:
            self._sessions.pop(session_id, None)
    
    async def list_by_user(self, user_id: str) -> list[Session]:
        """List all sessions for a user."""
        async with self._lock:
            return [
                s for s in self._sessions.values()
                if s.user_id == user_id
            ]
    
    async def list_by_assistant(self, assistant_id: str) -> list[Session]:
        """List all sessions for an assistant."""
        async with self._lock:
            return [
                s for s in self._sessions.values()
                if s.assistant_id == assistant_id
            ]
    
    async def cleanup_expired(self, timeout_seconds: float) -> int:
        """Clean up expired sessions."""
        async with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if session.is_expired(timeout_seconds)
            ]
            for sid in expired_ids:
                del self._sessions[sid]
            return len(expired_ids)
    
    async def clear(self) -> None:
        """Clear all sessions (for testing)."""
        async with self._lock:
            self._sessions.clear()
    
    @property
    def count(self) -> int:
        """Get the number of sessions (for testing)."""
        return len(self._sessions)
