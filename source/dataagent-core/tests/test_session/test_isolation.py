"""Tests for session isolation.

Property 51: 用户会话隔离
"""

import pytest

from dataagent_core.session import MemorySessionStore


class TestSessionIsolation:
    """Tests for user session isolation.
    
    Property 51: 用户会话隔离
    """

    @pytest.mark.asyncio
    async def test_list_by_user_returns_only_user_sessions(self):
        """Property 51: list_by_user 只返回指定用户的会话."""
        store = MemorySessionStore()
        
        # Create sessions for different users
        session1 = await store.create("user1", "assistant1")
        session2 = await store.create("user1", "assistant1")
        session3 = await store.create("user2", "assistant1")
        session4 = await store.create("user3", "assistant1")
        
        # List sessions for user1
        user1_sessions = await store.list_by_user("user1")
        
        # Should only contain user1's sessions
        assert len(user1_sessions) == 2
        session_ids = {s.session_id for s in user1_sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id not in session_ids
        assert session4.session_id not in session_ids

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_session(self):
        """Property 51: 用户不能访问其他用户的会话."""
        store = MemorySessionStore()
        
        # Create session for user1
        session1 = await store.create("user1", "assistant1")
        
        # user2's session list should not contain user1's session
        user2_sessions = await store.list_by_user("user2")
        assert len(user2_sessions) == 0

    @pytest.mark.asyncio
    async def test_delete_session_does_not_affect_other_users(self):
        """Property 51: 删除会话不影响其他用户."""
        store = MemorySessionStore()
        
        # Create sessions for different users
        session1 = await store.create("user1", "assistant1")
        session2 = await store.create("user2", "assistant1")
        
        # Delete user1's session
        await store.delete(session1.session_id)
        
        # user2's session should still exist
        user2_sessions = await store.list_by_user("user2")
        assert len(user2_sessions) == 1
        assert user2_sessions[0].session_id == session2.session_id

    @pytest.mark.asyncio
    async def test_list_by_assistant_includes_all_users(self):
        """Test list_by_assistant includes sessions from all users."""
        store = MemorySessionStore()
        
        # Create sessions for different users with same assistant
        await store.create("user1", "shared-assistant")
        await store.create("user2", "shared-assistant")
        await store.create("user3", "shared-assistant")
        await store.create("user1", "other-assistant")
        
        # List by assistant should include all users
        sessions = await store.list_by_assistant("shared-assistant")
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_cleanup_expired_respects_user_isolation(self):
        """Property 51: 清理过期会话保持用户隔离."""
        store = MemorySessionStore()
        
        # Create sessions
        session1 = await store.create("user1", "assistant1")
        session2 = await store.create("user2", "assistant1")
        
        # Manually expire session1 by setting old timestamp
        import time
        session1.last_active = time.time() - 10000
        await store.update(session1)
        
        # Cleanup with short timeout
        cleaned = await store.cleanup_expired(timeout_seconds=100)
        
        # Only session1 should be cleaned
        assert cleaned == 1
        
        # user2's session should still exist
        user2_sessions = await store.list_by_user("user2")
        assert len(user2_sessions) == 1

    @pytest.mark.asyncio
    async def test_empty_user_returns_empty_list(self):
        """Property 51: 没有会话的用户返回空列表."""
        store = MemorySessionStore()
        
        # Create sessions for other users
        await store.create("user1", "assistant1")
        await store.create("user2", "assistant1")
        
        # user3 has no sessions
        user3_sessions = await store.list_by_user("user3")
        assert user3_sessions == []

    @pytest.mark.asyncio
    async def test_session_user_id_immutable(self):
        """Property 51: 会话的 user_id 不可变."""
        store = MemorySessionStore()
        
        session = await store.create("user1", "assistant1")
        original_user_id = session.user_id
        
        # Even after update, user_id should remain the same
        session.state["key"] = "value"
        await store.update(session)
        
        retrieved = await store.get(session.session_id)
        assert retrieved.user_id == original_user_id
