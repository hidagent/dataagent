"""Tests for message history API endpoints.

**Feature: dataagent-development-specs, Property 46: 消息查询分页正确性**
"""

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_server.main import create_app


@pytest.fixture
def client():
    """Create test client with initialized app state."""
    app = create_app()
    
    # Initialize stores for testing
    from dataagent_core.session import MemorySessionStore, MemoryMessageStore
    app.state.session_store = MemorySessionStore()
    app.state.message_store = MemoryMessageStore()
    
    with TestClient(app) as client:
        yield client, app


class TestMessageHistoryEndpoint:
    """Tests for GET /api/v1/sessions/{session_id}/messages endpoint."""
    
    @pytest.mark.asyncio
    async def test_messages_endpoint_returns_404_for_nonexistent_session(self, client):
        """Test that messages endpoint returns 404 for nonexistent session."""
        test_client, _ = client
        response = test_client.get("/api/v1/sessions/nonexistent/messages")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_messages_endpoint_returns_empty_list_for_new_session(self, client):
        """Test that messages endpoint returns empty list for new session."""
        test_client, app = client
        
        # Create a session
        session = await app.state.session_store.create("user1", "assistant1")
        
        response = test_client.get(f"/api/v1/sessions/{session.session_id}/messages")
        assert response.status_code == 200
        
        data = response.json()
        assert data["messages"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_messages_endpoint_returns_saved_messages(self, client):
        """Test that messages endpoint returns saved messages."""
        test_client, app = client
        
        # Create a session
        session = await app.state.session_store.create("user1", "assistant1")
        
        # Save some messages
        await app.state.message_store.save_message(
            session.session_id, "user", "Hello"
        )
        await app.state.message_store.save_message(
            session.session_id, "assistant", "Hi there!"
        )
        
        response = test_client.get(f"/api/v1/sessions/{session.session_id}/messages")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["total"] == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][1]["content"] == "Hi there!"
    
    @pytest.mark.asyncio
    async def test_messages_endpoint_pagination_limit(self, client):
        """Test that messages endpoint respects limit parameter."""
        test_client, app = client
        
        # Create a session
        session = await app.state.session_store.create("user1", "assistant1")
        
        # Save multiple messages
        for i in range(10):
            await app.state.message_store.save_message(
                session.session_id, "user", f"Message {i}"
            )
        
        response = test_client.get(
            f"/api/v1/sessions/{session.session_id}/messages?limit=5"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 5
        assert data["total"] == 10
        assert data["limit"] == 5
    
    @pytest.mark.asyncio
    async def test_messages_endpoint_pagination_offset(self, client):
        """Test that messages endpoint respects offset parameter."""
        test_client, app = client
        
        # Create a session
        session = await app.state.session_store.create("user1", "assistant1")
        
        # Save multiple messages
        for i in range(10):
            await app.state.message_store.save_message(
                session.session_id, "user", f"Message {i}"
            )
        
        response = test_client.get(
            f"/api/v1/sessions/{session.session_id}/messages?offset=5"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 5
        assert data["offset"] == 5
        # First message should be "Message 5" (0-indexed)
        assert data["messages"][0]["content"] == "Message 5"
    
    @pytest.mark.asyncio
    async def test_messages_ordered_by_creation_time(self, client):
        """Test that messages are ordered by creation time (oldest first)."""
        test_client, app = client
        
        # Create a session
        session = await app.state.session_store.create("user1", "assistant1")
        
        # Save messages
        await app.state.message_store.save_message(
            session.session_id, "user", "First"
        )
        await app.state.message_store.save_message(
            session.session_id, "assistant", "Second"
        )
        await app.state.message_store.save_message(
            session.session_id, "user", "Third"
        )
        
        response = test_client.get(f"/api/v1/sessions/{session.session_id}/messages")
        assert response.status_code == 200
        
        data = response.json()
        assert data["messages"][0]["content"] == "First"
        assert data["messages"][1]["content"] == "Second"
        assert data["messages"][2]["content"] == "Third"
    
    @pytest.mark.asyncio
    async def test_messages_response_contains_required_fields(self, client):
        """Test that message response contains all required fields."""
        test_client, app = client
        
        # Create a session
        session = await app.state.session_store.create("user1", "assistant1")
        
        # Save a message
        await app.state.message_store.save_message(
            session.session_id, "user", "Test message"
        )
        
        response = test_client.get(f"/api/v1/sessions/{session.session_id}/messages")
        assert response.status_code == 200
        
        data = response.json()
        message = data["messages"][0]
        
        assert "message_id" in message
        assert "session_id" in message
        assert "role" in message
        assert "content" in message
        assert "created_at" in message
        assert "metadata" in message


class TestMessagePaginationProperties:
    """Property-based tests for message pagination.
    
    **Feature: dataagent-development-specs, Property 46: 消息查询分页正确性**
    
    Note: These tests use the MemoryMessageStore directly to test pagination
    logic without HTTP overhead.
    """
    
    @pytest.mark.asyncio
    @settings(max_examples=50)
    @given(
        limit=st.integers(min_value=1, max_value=100),
        offset=st.integers(min_value=0, max_value=50),
    )
    async def test_pagination_returns_correct_count(self, limit: int, offset: int):
        """Test that pagination returns correct number of messages."""
        from dataagent_core.session import MemoryMessageStore
        
        message_store = MemoryMessageStore()
        session_id = "test-session"
        total_messages = 100
        
        for i in range(total_messages):
            await message_store.save_message(session_id, "user", f"Message {i}")
        
        messages = await message_store.get_messages(session_id, limit=limit, offset=offset)
        total = await message_store.count_messages(session_id)
        
        expected_count = min(limit, max(0, total_messages - offset))
        assert len(messages) == expected_count
        assert total == total_messages
