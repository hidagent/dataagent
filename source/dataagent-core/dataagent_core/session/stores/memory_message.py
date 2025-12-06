"""In-memory message store implementation."""

import asyncio
from typing import Any

from dataagent_core.session.message_store import Message, MessageStore


class MemoryMessageStore(MessageStore):
    """In-memory message store for development and testing.
    
    This implementation stores messages in a dictionary and is not
    suitable for production use with multiple processes.
    """
    
    def __init__(self) -> None:
        self._messages: dict[str, list[Message]] = {}
        self._lock = asyncio.Lock()
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save a message."""
        message = Message.create(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        
        async with self._lock:
            if session_id not in self._messages:
                self._messages[session_id] = []
            self._messages[session_id].append(message)
        
        return message.message_id
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a session."""
        async with self._lock:
            messages = self._messages.get(session_id, [])
            # Sort by created_at (oldest first)
            sorted_messages = sorted(messages, key=lambda m: m.created_at)
            return sorted_messages[offset:offset + limit]
    
    async def delete_messages(self, session_id: str) -> int:
        """Delete all messages for a session."""
        async with self._lock:
            messages = self._messages.pop(session_id, [])
            return len(messages)
    
    async def count_messages(self, session_id: str) -> int:
        """Count messages for a session."""
        async with self._lock:
            return len(self._messages.get(session_id, []))
    
    async def clear(self) -> None:
        """Clear all messages (for testing)."""
        async with self._lock:
            self._messages.clear()
