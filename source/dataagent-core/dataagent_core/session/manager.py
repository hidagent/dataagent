"""Session manager for DataAgent Core."""

import asyncio
import logging
from typing import TYPE_CHECKING

from dataagent_core.session.state import Session
from dataagent_core.session.store import SessionStore
from dataagent_core.session.stores.memory import MemorySessionStore

if TYPE_CHECKING:
    from dataagent_core.engine import AgentConfig, AgentExecutor
    from dataagent_core.hitl import HITLHandler

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions and provides executors.
    
    The SessionManager is responsible for:
    - Creating and retrieving sessions
    - Managing session lifecycle
    - Providing configured AgentExecutors for sessions
    - Automatic cleanup of expired sessions
    """
    
    DEFAULT_TIMEOUT_SECONDS = 3600.0  # 1 hour
    CLEANUP_INTERVAL_SECONDS = 300.0  # 5 minutes
    
    def __init__(
        self,
        store: SessionStore | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        auto_cleanup: bool = True,
    ) -> None:
        """Initialize the session manager.
        
        Args:
            store: Session store implementation. Defaults to MemorySessionStore.
            timeout_seconds: Session timeout in seconds.
            auto_cleanup: Whether to automatically clean up expired sessions.
        """
        self._store = store or MemorySessionStore()
        self._timeout_seconds = timeout_seconds
        self._auto_cleanup = auto_cleanup
        self._cleanup_task: asyncio.Task | None = None
        self._running = False
    
    @property
    def store(self) -> SessionStore:
        """Get the session store."""
        return self._store
    
    @property
    def timeout_seconds(self) -> float:
        """Get the session timeout in seconds."""
        return self._timeout_seconds
    
    async def start(self) -> None:
        """Start the session manager and cleanup task."""
        if self._running:
            return
        self._running = True
        if self._auto_cleanup:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session cleanup task started")
    
    async def stop(self) -> None:
        """Stop the session manager and cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Session cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while self._running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                count = await self._store.cleanup_expired(self._timeout_seconds)
                if count > 0:
                    logger.info(f"Cleaned up {count} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def get_or_create_session(
        self,
        user_id: str,
        assistant_id: str,
        session_id: str | None = None,
    ) -> Session:
        """Get an existing session or create a new one.
        
        Args:
            user_id: The user identifier.
            assistant_id: The assistant identifier.
            session_id: Optional existing session ID to retrieve.
            
        Returns:
            The existing or newly created Session.
        """
        if session_id:
            session = await self._store.get(session_id)
            if session:
                session.touch()
                await self._store.update(session)
                return session
        
        # Create new session
        session = await self._store.create(user_id, assistant_id)
        logger.info(f"Created new session: {session.session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.
        
        Args:
            session_id: The session identifier.
            
        Returns:
            The Session if found and not expired, None otherwise.
        """
        session = await self._store.get(session_id)
        if session and session.is_expired(self._timeout_seconds):
            await self._store.delete(session_id)
            logger.info(f"Session expired and deleted: {session_id}")
            return None
        return session
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session.
        
        Args:
            session_id: The session identifier to delete.
        """
        await self._store.delete(session_id)
        logger.info(f"Session deleted: {session_id}")
    
    async def list_user_sessions(self, user_id: str) -> list[Session]:
        """List all sessions for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            List of active sessions for the user.
        """
        sessions = await self._store.list_by_user(user_id)
        # Filter out expired sessions
        active = []
        for session in sessions:
            if session.is_expired(self._timeout_seconds):
                await self._store.delete(session.session_id)
            else:
                active.append(session)
        return active
    
    def get_executor(
        self,
        session: Session,
        config: "AgentConfig",
        hitl_handler: "HITLHandler | None" = None,
    ) -> "AgentExecutor":
        """Get an AgentExecutor configured for the session.
        
        Args:
            session: The session to create an executor for.
            config: Agent configuration.
            hitl_handler: Optional HITL handler for user approval.
            
        Returns:
            Configured AgentExecutor instance.
        """
        from dataagent_core.engine import AgentFactory, AgentExecutor
        
        factory = AgentFactory()
        agent, backend = factory.create_agent(config)
        
        return AgentExecutor(
            agent=agent,
            backend=backend,
            hitl_handler=hitl_handler,
            thread_id=session.session_id,
        )
    
    async def cleanup_expired(self) -> int:
        """Manually trigger cleanup of expired sessions.
        
        Returns:
            Number of sessions cleaned up.
        """
        count = await self._store.cleanup_expired(self._timeout_seconds)
        if count > 0:
            logger.info(f"Manually cleaned up {count} expired sessions")
        return count
