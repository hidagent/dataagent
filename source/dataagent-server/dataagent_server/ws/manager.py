"""WebSocket connection manager."""

import asyncio
import time
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Thread-safe WebSocket connection manager.
    
    Manages WebSocket connections, active tasks, and HITL decisions.
    Supports concurrent connections with configurable limits.
    """
    
    def __init__(self, max_connections: int = 200):
        """Initialize connection manager.
        
        Args:
            max_connections: Maximum number of concurrent connections.
        """
        self._connections: dict[str, WebSocket] = {}
        self._pending_decisions: dict[str, asyncio.Future[dict]] = {}
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()
        self._max_connections = max_connections
    
    @property
    def connection_count(self) -> int:
        """Get current number of connections."""
        return len(self._connections)
    
    @property
    def is_at_capacity(self) -> bool:
        """Check if connection limit is reached."""
        return self.connection_count >= self._max_connections
    
    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """Accept and register a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to register.
            session_id: Session ID for the connection.
            
        Returns:
            True if connection was accepted, False if at capacity.
        """
        async with self._lock:
            if len(self._connections) >= self._max_connections:
                return False
            
            await websocket.accept()
            self._connections[session_id] = websocket
            return True
    
    async def disconnect(self, session_id: str) -> None:
        """Disconnect and cleanup a session.
        
        Args:
            session_id: Session ID to disconnect.
        """
        async with self._lock:
            # Remove connection
            self._connections.pop(session_id, None)
            
            # Cancel pending HITL decision
            if session_id in self._pending_decisions:
                future = self._pending_decisions.pop(session_id)
                if not future.done():
                    future.cancel()
            
            # Cancel active task
            if session_id in self._active_tasks:
                task = self._active_tasks.pop(session_id)
                if not task.done():
                    task.cancel()
    
    async def send(self, session_id: str, message: dict) -> bool:
        """Send a JSON message to a session.
        
        Args:
            session_id: Session ID to send to.
            message: Message dict to send as JSON.
            
        Returns:
            True if message was sent, False if session not found.
        """
        websocket = self._connections.get(session_id)
        if websocket is None:
            return False
        
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            # Connection may have closed
            await self.disconnect(session_id)
            return False
    
    async def send_event(self, session_id: str, event: Any) -> bool:
        """Send an ExecutionEvent to a session.
        
        Args:
            session_id: Session ID to send to.
            event: ExecutionEvent to send.
            
        Returns:
            True if event was sent, False if session not found.
        """
        event_dict = event.to_dict() if hasattr(event, "to_dict") else {}
        return await self.send(session_id, {
            "event_type": getattr(event, "event_type", "unknown"),
            "data": event_dict,
            "timestamp": getattr(event, "timestamp", time.time()),
        })
    
    async def start_task(
        self,
        session_id: str,
        coro: Any,
    ) -> asyncio.Task[Any]:
        """Start a cancellable task for a session.
        
        Args:
            session_id: Session ID for the task.
            coro: Coroutine to run as task.
            
        Returns:
            The created asyncio Task.
        """
        task = asyncio.create_task(coro)
        async with self._lock:
            # Cancel any existing task
            if session_id in self._active_tasks:
                old_task = self._active_tasks[session_id]
                if not old_task.done():
                    old_task.cancel()
            self._active_tasks[session_id] = task
        return task
    
    async def cancel_task(self, session_id: str) -> bool:
        """Cancel an active task for a session.
        
        Args:
            session_id: Session ID to cancel task for.
            
        Returns:
            True if task was cancelled, False if no active task.
        """
        async with self._lock:
            task = self._active_tasks.get(session_id)
            if task is None or task.done():
                return False
            
            task.cancel()
            self._active_tasks.pop(session_id, None)
            return True
    
    async def wait_for_decision(
        self,
        session_id: str,
        timeout: float = 300,
    ) -> dict | None:
        """Wait for a HITL decision from the client.
        
        Args:
            session_id: Session ID to wait for.
            timeout: Timeout in seconds.
            
        Returns:
            Decision dict if received, None if timeout or cancelled.
        """
        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict] = loop.create_future()
        
        async with self._lock:
            # Cancel any existing pending decision
            if session_id in self._pending_decisions:
                old_future = self._pending_decisions[session_id]
                if not old_future.done():
                    old_future.cancel()
            self._pending_decisions[session_id] = future
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        except asyncio.CancelledError:
            return None
        finally:
            async with self._lock:
                self._pending_decisions.pop(session_id, None)
    
    def resolve_decision(self, session_id: str, decision: dict) -> bool:
        """Resolve a pending HITL decision.
        
        Args:
            session_id: Session ID to resolve.
            decision: Decision dict from client.
            
        Returns:
            True if decision was resolved, False if no pending decision.
        """
        future = self._pending_decisions.get(session_id)
        if future is None or future.done():
            return False
        
        future.set_result(decision)
        return True
    
    def has_connection(self, session_id: str) -> bool:
        """Check if a session has an active connection.
        
        Args:
            session_id: Session ID to check.
            
        Returns:
            True if session has active connection.
        """
        return session_id in self._connections
    
    def has_active_task(self, session_id: str) -> bool:
        """Check if a session has an active task.
        
        Args:
            session_id: Session ID to check.
            
        Returns:
            True if session has active task.
        """
        task = self._active_tasks.get(session_id)
        return task is not None and not task.done()
