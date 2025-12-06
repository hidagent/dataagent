"""Tests for MySQL session store.

Note: These tests use SQLite in-memory database as a substitute for MySQL
to avoid requiring a MySQL server for testing. The SQLAlchemy ORM layer
ensures compatibility.

**Feature: dataagent-development-specs, Property 42: MySQL 会话存储往返一致性**
**Feature: dataagent-development-specs, Property 44: 数据库连接池管理**
"""

import asyncio
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from dataagent_core.session.models import Base, SessionModel, MessageModel
from dataagent_core.session.state import Session


def async_session_factory(engine):
    """Create an async session factory."""
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create a database session for testing."""
    factory = async_session_factory(db_engine)
    
    async with factory() as session:
        yield session


class TestSessionModel:
    """Tests for SessionModel ORM."""
    
    @pytest.mark.asyncio
    async def test_create_session_model(self, db_session):
        """Test creating a session model."""
        session = SessionModel(
            session_id="test-session-1",
            user_id="user-1",
            assistant_id="assistant-1",
            state={"key": "value"},
            metadata_={"meta": "data"},
        )
        
        db_session.add(session)
        await db_session.commit()
        
        # Query back
        from sqlalchemy import select
        result = await db_session.execute(
            select(SessionModel).where(SessionModel.session_id == "test-session-1")
        )
        loaded = result.scalar_one()
        
        assert loaded.session_id == "test-session-1"
        assert loaded.user_id == "user-1"
        assert loaded.assistant_id == "assistant-1"
        assert loaded.state == {"key": "value"}
        assert loaded.metadata_ == {"meta": "data"}
    
    @pytest.mark.asyncio
    async def test_session_timestamps(self, db_session):
        """Test that session timestamps are set correctly."""
        session = SessionModel(
            session_id="test-session-2",
            user_id="user-1",
            assistant_id="assistant-1",
        )
        
        db_session.add(session)
        await db_session.commit()
        
        assert session.created_at is not None
        assert session.last_active is not None


class TestMessageModel:
    """Tests for MessageModel ORM."""
    
    @pytest.mark.asyncio
    async def test_create_message_model(self, db_session):
        """Test creating a message model."""
        # First create a session
        session = SessionModel(
            session_id="test-session-msg",
            user_id="user-1",
            assistant_id="assistant-1",
        )
        db_session.add(session)
        await db_session.commit()
        
        # Create a message
        message = MessageModel(
            message_id="msg-1",
            session_id="test-session-msg",
            role="user",
            content="Hello, world!",
            metadata_={"source": "test"},
        )
        
        db_session.add(message)
        await db_session.commit()
        
        # Query back
        from sqlalchemy import select
        result = await db_session.execute(
            select(MessageModel).where(MessageModel.message_id == "msg-1")
        )
        loaded = result.scalar_one()
        
        assert loaded.message_id == "msg-1"
        assert loaded.session_id == "test-session-msg"
        assert loaded.role == "user"
        assert loaded.content == "Hello, world!"
        assert loaded.metadata_ == {"source": "test"}
    
    @pytest.mark.asyncio
    async def test_message_cascade_delete(self, db_session):
        """Test that messages are deleted when session is deleted."""
        # Create session with messages
        session = SessionModel(
            session_id="test-session-cascade",
            user_id="user-1",
            assistant_id="assistant-1",
        )
        db_session.add(session)
        await db_session.commit()
        
        for i in range(3):
            message = MessageModel(
                message_id=f"msg-cascade-{i}",
                session_id="test-session-cascade",
                role="user",
                content=f"Message {i}",
            )
            db_session.add(message)
        await db_session.commit()
        
        # Delete session
        await db_session.delete(session)
        await db_session.commit()
        
        # Verify messages are deleted
        from sqlalchemy import select
        result = await db_session.execute(
            select(MessageModel).where(MessageModel.session_id == "test-session-cascade")
        )
        messages = result.scalars().all()
        assert len(messages) == 0


class TestSessionRoundTrip:
    """Property-based tests for session round-trip.
    
    **Feature: dataagent-development-specs, Property 42: MySQL 会话存储往返一致性**
    """
    
    @pytest.mark.asyncio
    @settings(max_examples=50)
    @given(
        user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        assistant_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    async def test_session_roundtrip(self, user_id: str, assistant_id: str):
        """Test that session data survives round-trip through database."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        try:
            # Create session
            original = Session.create(user_id=user_id, assistant_id=assistant_id)
            
            async with session_factory() as db:
                model = SessionModel(
                    session_id=original.session_id,
                    user_id=original.user_id,
                    assistant_id=original.assistant_id,
                    created_at=original.created_at,
                    last_active=original.last_active,
                    state=original.state,
                    metadata_=original.metadata,
                )
                db.add(model)
                await db.commit()
            
            # Read back
            async with session_factory() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(SessionModel).where(SessionModel.session_id == original.session_id)
                )
                loaded_model = result.scalar_one()
                
                loaded = Session(
                    session_id=loaded_model.session_id,
                    user_id=loaded_model.user_id,
                    assistant_id=loaded_model.assistant_id,
                    created_at=loaded_model.created_at,
                    last_active=loaded_model.last_active,
                    state=loaded_model.state or {},
                    metadata=loaded_model.metadata_ or {},
                )
            
            # Verify
            assert loaded.session_id == original.session_id
            assert loaded.user_id == original.user_id
            assert loaded.assistant_id == original.assistant_id
        finally:
            await engine.dispose()


class TestConcurrentAccess:
    """Tests for concurrent database access.
    
    **Feature: dataagent-development-specs, Property 44: 数据库连接池管理**
    """
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self, db_engine):
        """Test that concurrent session creation works correctly."""
        session_factory = sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def create_session(session_id: str):
            async with session_factory() as db:
                session = SessionModel(
                    session_id=session_id,
                    user_id="user-concurrent",
                    assistant_id="assistant-1",
                )
                db.add(session)
                await db.commit()
                return session_id
        
        # Create 10 sessions concurrently
        tasks = [create_session(f"concurrent-{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        
        # Verify all sessions exist
        async with session_factory() as db:
            from sqlalchemy import select, func
            result = await db.execute(
                select(func.count(SessionModel.session_id))
                .where(SessionModel.user_id == "user-concurrent")
            )
            count = result.scalar()
            assert count == 10
