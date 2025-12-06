"""Property-based tests for session management."""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from dataagent_core.session import Session, MemorySessionStore, SessionManager


# Strategies for generating test data
user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
assistant_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
session_id_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
state_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
    max_size=5,
)
timeout_strategy = st.floats(min_value=1.0, max_value=86400.0)  # 1 second to 1 day


class TestSessionProperties:
    """Property-based tests for Session dataclass."""
    
    @settings(max_examples=100)
    @given(user_id=user_id_strategy, assistant_id=assistant_id_strategy)
    def test_session_create_generates_unique_ids(self, user_id: str, assistant_id: str):
        """
        **Feature: dataagent-development-specs, Property: Session IDs are unique**
        
        For any user_id and assistant_id, Session.create() generates unique session IDs.
        """
        session1 = Session.create(user_id=user_id, assistant_id=assistant_id)
        session2 = Session.create(user_id=user_id, assistant_id=assistant_id)
        
        assert session1.session_id != session2.session_id
    
    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        assistant_id=assistant_id_strategy,
        state=state_strategy,
    )
    def test_session_serialization_roundtrip(
        self, user_id: str, assistant_id: str, state: dict
    ):
        """
        **Feature: dataagent-development-specs, Property: Session serialization roundtrip**
        
        For any Session, to_dict() followed by from_dict() produces equivalent session.
        """
        session = Session.create(
            user_id=user_id,
            assistant_id=assistant_id,
            state=state,
        )
        
        data = session.to_dict()
        restored = Session.from_dict(data)
        
        assert restored.session_id == session.session_id
        assert restored.user_id == session.user_id
        assert restored.assistant_id == session.assistant_id
        assert restored.state == session.state
    
    @settings(max_examples=100)
    @given(timeout=timeout_strategy)
    def test_session_expiry_consistency(self, timeout: float):
        """
        **Feature: dataagent-development-specs, Property: Session expiry is consistent**
        
        A newly created session should not be expired for any reasonable timeout.
        """
        session = Session.create(user_id="user", assistant_id="assistant")
        
        # New session should not be expired
        assert session.is_expired(timeout) is False
    
    @settings(max_examples=100)
    @given(
        timeout=st.floats(min_value=1.0, max_value=100.0),
        elapsed=st.floats(min_value=0.0, max_value=200.0),
    )
    def test_session_expiry_logic(self, timeout: float, elapsed: float):
        """
        **Feature: dataagent-development-specs, Property: Session expiry logic is correct**
        
        Session is expired iff elapsed time > timeout.
        """
        session = Session.create(user_id="user", assistant_id="assistant")
        session.last_active = datetime.now() - timedelta(seconds=elapsed)
        
        is_expired = session.is_expired(timeout)
        
        # Allow small tolerance for timing
        if elapsed > timeout + 0.1:
            assert is_expired is True
        elif elapsed < timeout - 0.1:
            assert is_expired is False


class TestMemorySessionStoreProperties:
    """Property-based tests for MemorySessionStore."""
    
    @settings(max_examples=50)
    @given(user_id=user_id_strategy, assistant_id=assistant_id_strategy)
    @pytest.mark.asyncio
    async def test_store_create_and_get_consistency(
        self, user_id: str, assistant_id: str
    ):
        """
        **Feature: dataagent-development-specs, Property: Store create/get consistency**
        
        For any created session, get() returns the same session.
        """
        store = MemorySessionStore()
        
        created = await store.create(user_id=user_id, assistant_id=assistant_id)
        retrieved = await store.get(created.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.user_id == user_id
        assert retrieved.assistant_id == assistant_id
        
        await store.clear()
    
    @settings(max_examples=50)
    @given(session_id=session_id_strategy)
    @pytest.mark.asyncio
    async def test_store_get_nonexistent_returns_none(self, session_id: str):
        """
        **Feature: dataagent-development-specs, Property: Get nonexistent returns None**
        
        For any session_id not in store, get() returns None.
        """
        store = MemorySessionStore()
        
        result = await store.get(session_id)
        
        assert result is None
    
    @settings(max_examples=50)
    @given(user_id=user_id_strategy, assistant_id=assistant_id_strategy)
    @pytest.mark.asyncio
    async def test_store_delete_removes_session(
        self, user_id: str, assistant_id: str
    ):
        """
        **Feature: dataagent-development-specs, Property: Delete removes session**
        
        After delete(), get() returns None for that session.
        """
        store = MemorySessionStore()
        
        session = await store.create(user_id=user_id, assistant_id=assistant_id)
        await store.delete(session.session_id)
        
        assert await store.get(session.session_id) is None
        
        await store.clear()


class TestSessionManagerProperties:
    """Property-based tests for SessionManager."""
    
    @settings(max_examples=50)
    @given(
        timeout=st.floats(min_value=10.0, max_value=100.0),
        expired_count=st.integers(min_value=0, max_value=5),
        active_count=st.integers(min_value=0, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_only_expired(
        self, timeout: float, expired_count: int, active_count: int
    ):
        """
        **Feature: dataagent-development-specs, Property 21: 会话超时自动清理**
        
        For any set of sessions, cleanup_expired removes exactly the expired ones.
        **Validates: Requirements 13.4**
        """
        store = MemorySessionStore()
        manager = SessionManager(store=store, timeout_seconds=timeout, auto_cleanup=False)
        
        # Create expired sessions
        expired_ids = []
        for i in range(expired_count):
            session = await store.create(
                user_id=f"expired-user-{i}",
                assistant_id="assistant",
            )
            session.last_active = datetime.now() - timedelta(seconds=timeout + 10)
            await store.update(session)
            expired_ids.append(session.session_id)
        
        # Create active sessions
        active_ids = []
        for i in range(active_count):
            session = await store.create(
                user_id=f"active-user-{i}",
                assistant_id="assistant",
            )
            active_ids.append(session.session_id)
        
        # Run cleanup
        cleaned = await manager.cleanup_expired()
        
        # Verify results
        assert cleaned == expired_count
        
        # All expired sessions should be gone
        for sid in expired_ids:
            assert await store.get(sid) is None
        
        # All active sessions should remain
        for sid in active_ids:
            assert await store.get(sid) is not None
        
        await store.clear()
    
    @settings(max_examples=50)
    @given(user_id=user_id_strategy, assistant_id=assistant_id_strategy)
    @pytest.mark.asyncio
    async def test_get_or_create_idempotent_with_id(
        self, user_id: str, assistant_id: str
    ):
        """
        **Feature: dataagent-development-specs, Property: get_or_create is idempotent**
        
        Calling get_or_create with same session_id returns same session.
        """
        store = MemorySessionStore()
        manager = SessionManager(store=store, auto_cleanup=False)
        
        session1 = await manager.get_or_create_session(
            user_id=user_id,
            assistant_id=assistant_id,
        )
        
        session2 = await manager.get_or_create_session(
            user_id=user_id,
            assistant_id=assistant_id,
            session_id=session1.session_id,
        )
        
        assert session1.session_id == session2.session_id
        
        await store.clear()
