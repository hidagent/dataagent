"""Unit tests for SessionManager."""

import pytest
import asyncio
from datetime import datetime, timedelta

from dataagent_core.session import Session, MemorySessionStore, SessionManager


@pytest.fixture
def store():
    """Create a fresh MemorySessionStore for each test."""
    return MemorySessionStore()


@pytest.fixture
def manager(store):
    """Create a SessionManager with the test store."""
    return SessionManager(store=store, timeout_seconds=3600, auto_cleanup=False)


class TestSessionManager:
    """Tests for SessionManager."""
    
    @pytest.mark.asyncio
    async def test_get_or_create_creates_new_session(self, manager):
        """Test that get_or_create creates a new session when none exists."""
        session = await manager.get_or_create_session(
            user_id="user-1",
            assistant_id="assistant-1",
        )
        
        assert session is not None
        assert session.user_id == "user-1"
        assert session.assistant_id == "assistant-1"
    
    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_session(self, manager):
        """Test that get_or_create returns existing session when ID provided."""
        created = await manager.get_or_create_session(
            user_id="user-1",
            assistant_id="assistant-1",
        )
        
        retrieved = await manager.get_or_create_session(
            user_id="user-1",
            assistant_id="assistant-1",
            session_id=created.session_id,
        )
        
        assert retrieved.session_id == created.session_id
    
    @pytest.mark.asyncio
    async def test_get_or_create_creates_new_if_id_not_found(self, manager):
        """Test that get_or_create creates new session if ID not found."""
        session = await manager.get_or_create_session(
            user_id="user-1",
            assistant_id="assistant-1",
            session_id="nonexistent-id",
        )
        
        assert session is not None
        assert session.session_id != "nonexistent-id"
    
    @pytest.mark.asyncio
    async def test_get_session_returns_active_session(self, manager):
        """Test getting an active session."""
        created = await manager.get_or_create_session(
            user_id="user-1",
            assistant_id="assistant-1",
        )
        
        retrieved = await manager.get_session(created.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == created.session_id
    
    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_expired(self, manager, store):
        """Test that get_session returns None for expired session."""
        session = await store.create(user_id="user-1", assistant_id="assistant-1")
        session.last_active = datetime.now() - timedelta(seconds=7200)  # 2 hours ago
        await store.update(session)
        
        result = await manager.get_session(session.session_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self, manager):
        """Test deleting a session."""
        session = await manager.get_or_create_session(
            user_id="user-1",
            assistant_id="assistant-1",
        )
        
        await manager.delete_session(session.session_id)
        
        assert await manager.get_session(session.session_id) is None
    
    @pytest.mark.asyncio
    async def test_list_user_sessions(self, manager):
        """Test listing sessions for a user."""
        await manager.get_or_create_session(user_id="user-1", assistant_id="assistant-1")
        await manager.get_or_create_session(user_id="user-1", assistant_id="assistant-2")
        await manager.get_or_create_session(user_id="user-2", assistant_id="assistant-1")
        
        user1_sessions = await manager.list_user_sessions("user-1")
        
        assert len(user1_sessions) == 2
        assert all(s.user_id == "user-1" for s in user1_sessions)
    
    @pytest.mark.asyncio
    async def test_list_user_sessions_filters_expired(self, manager, store):
        """Test that list_user_sessions filters out expired sessions."""
        session1 = await store.create(user_id="user-1", assistant_id="assistant-1")
        session2 = await store.create(user_id="user-1", assistant_id="assistant-2")
        
        # Expire session1
        session1.last_active = datetime.now() - timedelta(seconds=7200)
        await store.update(session1)
        
        sessions = await manager.list_user_sessions("user-1")
        
        assert len(sessions) == 1
        assert sessions[0].session_id == session2.session_id
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, manager, store):
        """Test manual cleanup of expired sessions."""
        session1 = await store.create(user_id="user-1", assistant_id="assistant-1")
        session2 = await store.create(user_id="user-2", assistant_id="assistant-1")
        
        # Expire session1
        session1.last_active = datetime.now() - timedelta(seconds=7200)
        await store.update(session1)
        
        count = await manager.cleanup_expired()
        
        assert count == 1
        assert await store.get(session1.session_id) is None
        assert await store.get(session2.session_id) is not None
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, manager):
        """Test starting and stopping the manager."""
        await manager.start()
        assert manager._running is True
        
        await manager.stop()
        assert manager._running is False
    
    @pytest.mark.asyncio
    async def test_timeout_property(self, manager):
        """Test timeout_seconds property."""
        assert manager.timeout_seconds == 3600
    
    @pytest.mark.asyncio
    async def test_store_property(self, manager, store):
        """Test store property."""
        assert manager.store is store
