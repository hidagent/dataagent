"""Tests for message store implementations.

**Feature: dataagent-development-specs, Property 45: 消息历史记录完整性**
**Feature: dataagent-development-specs, Property 46: 消息查询分页正确性**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_core.session.message_store import Message, MessageStore
from dataagent_core.session.stores.memory_message import MemoryMessageStore


@pytest.fixture
def memory_store():
    """Create a memory message store for testing."""
    return MemoryMessageStore()


class TestMessage:
    """Tests for Message dataclass."""
    
    def test_create_message(self):
        """Test creating a message."""
        message = Message.create(
            session_id="session-1",
            role="user",
            content="Hello",
            metadata={"key": "value"},
        )
        
        assert message.session_id == "session-1"
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.metadata == {"key": "value"}
        assert message.message_id is not None
        assert message.created_at is not None
    
    def test_message_to_dict(self):
        """Test message serialization."""
        message = Message.create(
            session_id="session-1",
            role="assistant",
            content="Hi there!",
        )
        
        data = message.to_dict()
        
        assert data["session_id"] == "session-1"
        assert data["role"] == "assistant"
        assert data["content"] == "Hi there!"
        assert "message_id" in data
        assert "created_at" in data
        assert "metadata" in data


class TestMemoryMessageStore:
    """Tests for MemoryMessageStore."""
    
    @pytest.mark.asyncio
    async def test_save_message(self, memory_store):
        """Test saving a message."""
        message_id = await memory_store.save_message(
            session_id="session-1",
            role="user",
            content="Hello",
        )
        
        assert message_id is not None
    
    @pytest.mark.asyncio
    async def test_get_messages(self, memory_store):
        """Test getting messages."""
        await memory_store.save_message("session-1", "user", "Hello")
        await memory_store.save_message("session-1", "assistant", "Hi!")
        
        messages = await memory_store.get_messages("session-1")
        
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi!"
    
    @pytest.mark.asyncio
    async def test_get_messages_empty_session(self, memory_store):
        """Test getting messages from empty session."""
        messages = await memory_store.get_messages("nonexistent")
        assert messages == []
    
    @pytest.mark.asyncio
    async def test_delete_messages(self, memory_store):
        """Test deleting messages."""
        await memory_store.save_message("session-1", "user", "Hello")
        await memory_store.save_message("session-1", "assistant", "Hi!")
        
        count = await memory_store.delete_messages("session-1")
        
        assert count == 2
        
        messages = await memory_store.get_messages("session-1")
        assert messages == []
    
    @pytest.mark.asyncio
    async def test_count_messages(self, memory_store):
        """Test counting messages."""
        await memory_store.save_message("session-1", "user", "Hello")
        await memory_store.save_message("session-1", "assistant", "Hi!")
        await memory_store.save_message("session-1", "user", "How are you?")
        
        count = await memory_store.count_messages("session-1")
        
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_messages_ordered_by_time(self, memory_store):
        """Test that messages are ordered by creation time."""
        await memory_store.save_message("session-1", "user", "First")
        await memory_store.save_message("session-1", "assistant", "Second")
        await memory_store.save_message("session-1", "user", "Third")
        
        messages = await memory_store.get_messages("session-1")
        
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"
    
    @pytest.mark.asyncio
    async def test_messages_isolated_by_session(self, memory_store):
        """Test that messages are isolated by session."""
        await memory_store.save_message("session-1", "user", "Session 1 message")
        await memory_store.save_message("session-2", "user", "Session 2 message")
        
        messages_1 = await memory_store.get_messages("session-1")
        messages_2 = await memory_store.get_messages("session-2")
        
        assert len(messages_1) == 1
        assert len(messages_2) == 1
        assert messages_1[0].content == "Session 1 message"
        assert messages_2[0].content == "Session 2 message"


class TestMessagePagination:
    """Tests for message pagination.
    
    **Feature: dataagent-development-specs, Property 46: 消息查询分页正确性**
    """
    
    @pytest.mark.asyncio
    async def test_pagination_limit(self, memory_store):
        """Test pagination with limit."""
        for i in range(10):
            await memory_store.save_message("session-1", "user", f"Message {i}")
        
        messages = await memory_store.get_messages("session-1", limit=5)
        
        assert len(messages) == 5
        assert messages[0].content == "Message 0"
        assert messages[4].content == "Message 4"
    
    @pytest.mark.asyncio
    async def test_pagination_offset(self, memory_store):
        """Test pagination with offset."""
        for i in range(10):
            await memory_store.save_message("session-1", "user", f"Message {i}")
        
        messages = await memory_store.get_messages("session-1", offset=5)
        
        assert len(messages) == 5
        assert messages[0].content == "Message 5"
        assert messages[4].content == "Message 9"
    
    @pytest.mark.asyncio
    async def test_pagination_limit_and_offset(self, memory_store):
        """Test pagination with both limit and offset."""
        for i in range(10):
            await memory_store.save_message("session-1", "user", f"Message {i}")
        
        messages = await memory_store.get_messages("session-1", limit=3, offset=2)
        
        assert len(messages) == 3
        assert messages[0].content == "Message 2"
        assert messages[2].content == "Message 4"
    
    @pytest.mark.asyncio
    async def test_pagination_offset_beyond_total(self, memory_store):
        """Test pagination with offset beyond total messages."""
        for i in range(5):
            await memory_store.save_message("session-1", "user", f"Message {i}")
        
        messages = await memory_store.get_messages("session-1", offset=10)
        
        assert len(messages) == 0


class TestMessageStoreProperties:
    """Property-based tests for message store.
    
    **Feature: dataagent-development-specs, Property 45: 消息历史记录完整性**
    """
    
    @pytest.mark.asyncio
    @settings(max_examples=50)
    @given(
        role=st.sampled_from(["user", "assistant", "system"]),
        content=st.text(min_size=1, max_size=1000),
    )
    async def test_message_roundtrip(self, role: str, content: str):
        """Test that saved messages can be retrieved correctly."""
        store = MemoryMessageStore()
        
        message_id = await store.save_message(
            session_id="test-session",
            role=role,
            content=content,
        )
        
        messages = await store.get_messages("test-session")
        
        assert len(messages) == 1
        assert messages[0].message_id == message_id
        assert messages[0].role == role
        assert messages[0].content == content
    
    @pytest.mark.asyncio
    @settings(max_examples=50)
    @given(
        limit=st.integers(min_value=1, max_value=50),
        offset=st.integers(min_value=0, max_value=20),
    )
    async def test_pagination_correctness(self, limit: int, offset: int):
        """Test that pagination returns correct results."""
        store = MemoryMessageStore()
        total = 30
        
        for i in range(total):
            await store.save_message("test-session", "user", f"Message {i}")
        
        messages = await store.get_messages("test-session", limit=limit, offset=offset)
        
        expected_count = min(limit, max(0, total - offset))
        assert len(messages) == expected_count
        
        if expected_count > 0:
            assert messages[0].content == f"Message {offset}"
