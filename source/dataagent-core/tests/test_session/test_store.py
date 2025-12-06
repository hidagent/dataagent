"""Unit tests for MemorySessionStore."""

import pytest
from datetime import datetime, timedelta

from dataagent_core.session import Session, MemorySessionStore


@pytest.fixture
def store():
    """Create a fresh MemorySessionStore for each test."""
    return MemorySessionStore()


class TestMemorySessionStore:
    """Tests for MemorySessionStore implementation."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, store):
        """Test creating a new session."""
        session = await store.create(user_id="user-1", assistant_id="assistant-1")
        
        assert session.user_id == "user-1"
        assert session.assistant_id == "assistant-1"
        assert session.session_id is not None
        assert store.count == 1
    
    @pytest.mark.asyncio
    async def test_get_existing_session(self, store):
        """Test retrieving an existing session."""
        created = await store.create(user_id="user-1", assistant_id="assistant-1")
        
        retrieved = await store.get(created.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.user_id == created.user_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, store):
        """Test retrieving a non-existent session returns None."""
        result = await store.get("nonexistent-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_session(self, store):
        """Test updating a session."""
        session = await store.create(user_id="user-1", assistant_id="assistant-1")
        session.state["key"] = "value"
        
        await store.update(session)
        
        retrieved = await store.get(session.session_id)
        assert retrieved.state["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_delete_session(self, store):
        """Test deleting a session."""
        session = await store.create(user_id="user-1", assistant_id="assistant-1")
        
        await store.delete(session.session_id)
        
        assert await store.get(session.session_id) is None
        assert store.count == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, store):
        """Test deleting a non-existent session doesn't raise."""
        await store.delete("nonexistent-id")  # Should not raise
    
    @pytest.mark.asyncio
    async def test_list_by_user(self, store):
        """Test listing sessions by user."""
        await store.create(user_id="user-1", assistant_id="assistant-1")
        await store.create(user_id="user-1", assistant_id="assistant-2")
        await store.create(user_id="user-2", assistant_id="assistant-1")
        
        user1_sessions = await store.list_by_user("user-1")
        user2_sessions = await store.list_by_user("user-2")
        
        assert len(user1_sessions) == 2
        assert len(user2_sessions) == 1
        assert all(s.user_id == "user-1" for s in user1_sessions)
    
    @pytest.mark.asyncio
    async def test_list_by_assistant(self, store):
        """Test listing sessions by assistant."""
        await store.create(user_id="user-1", assistant_id="assistant-1")
        await store.create(user_id="user-2", assistant_id="assistant-1")
        await store.create(user_id="user-1", assistant_id="assistant-2")
        
        assistant1_sessions = await store.list_by_assistant("assistant-1")
        assistant2_sessions = await store.list_by_assistant("assistant-2")
        
        assert len(assistant1_sessions) == 2
        assert len(assistant2_sessions) == 1
        assert all(s.assistant_id == "assistant-1" for s in assistant1_sessions)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, store):
        """Test cleaning up expired sessions."""
        # Create sessions
        session1 = await store.create(user_id="user-1", assistant_id="assistant-1")
        session2 = await store.create(user_id="user-2", assistant_id="assistant-1")
        
        # Manually expire session1
        session1.last_active = datetime.now() - timedelta(seconds=100)
        await store.update(session1)
        
        # Cleanup with 60 second timeout
        count = await store.cleanup_expired(timeout_seconds=60)
        
        assert count == 1
        assert await store.get(session1.session_id) is None
        assert await store.get(session2.session_id) is not None
    
    @pytest.mark.asyncio
    async def test_clear(self, store):
        """Test clearing all sessions."""
        await store.create(user_id="user-1", assistant_id="assistant-1")
        await store.create(user_id="user-2", assistant_id="assistant-2")
        
        await store.clear()
        
        assert store.count == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, store):
        """Test concurrent session operations."""
        import asyncio
        
        async def create_session(user_id: str):
            return await store.create(user_id=user_id, assistant_id="assistant-1")
        
        # Create multiple sessions concurrently
        sessions = await asyncio.gather(*[
            create_session(f"user-{i}") for i in range(10)
        ])
        
        assert len(sessions) == 10
        assert store.count == 10
        
        # All sessions should have unique IDs
        session_ids = [s.session_id for s in sessions]
        assert len(set(session_ids)) == 10
