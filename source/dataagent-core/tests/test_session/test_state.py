"""Unit tests for Session state."""

import pytest
from datetime import datetime, timedelta
import time

from dataagent_core.session import Session


class TestSession:
    """Tests for Session dataclass."""
    
    def test_create_session_with_defaults(self):
        """Test creating a session with default values."""
        session = Session.create(user_id="user-1", assistant_id="assistant-1")
        
        assert session.user_id == "user-1"
        assert session.assistant_id == "assistant-1"
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.state == {}
        assert session.metadata == {}
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_active, datetime)
    
    def test_create_session_with_custom_id(self):
        """Test creating a session with custom session ID."""
        session = Session.create(
            user_id="user-1",
            assistant_id="assistant-1",
            session_id="custom-session-id",
        )
        
        assert session.session_id == "custom-session-id"
    
    def test_create_session_with_state_and_metadata(self):
        """Test creating a session with initial state and metadata."""
        state = {"key": "value"}
        metadata = {"source": "test"}
        
        session = Session.create(
            user_id="user-1",
            assistant_id="assistant-1",
            state=state,
            metadata=metadata,
        )
        
        assert session.state == state
        assert session.metadata == metadata
    
    def test_touch_updates_last_active(self):
        """Test that touch() updates last_active timestamp."""
        session = Session.create(user_id="user-1", assistant_id="assistant-1")
        original_last_active = session.last_active
        
        time.sleep(0.01)  # Small delay to ensure time difference
        session.touch()
        
        assert session.last_active > original_last_active
    
    def test_is_expired_returns_false_for_active_session(self):
        """Test that is_expired returns False for active session."""
        session = Session.create(user_id="user-1", assistant_id="assistant-1")
        
        assert session.is_expired(timeout_seconds=3600) is False
    
    def test_is_expired_returns_true_for_expired_session(self):
        """Test that is_expired returns True for expired session."""
        session = Session.create(user_id="user-1", assistant_id="assistant-1")
        # Manually set last_active to past
        session.last_active = datetime.now() - timedelta(seconds=100)
        
        assert session.is_expired(timeout_seconds=60) is True
    
    def test_to_dict_serialization(self):
        """Test session serialization to dictionary."""
        session = Session.create(
            user_id="user-1",
            assistant_id="assistant-1",
            session_id="test-session",
            state={"key": "value"},
            metadata={"source": "test"},
        )
        
        data = session.to_dict()
        
        assert data["session_id"] == "test-session"
        assert data["user_id"] == "user-1"
        assert data["assistant_id"] == "assistant-1"
        assert data["state"] == {"key": "value"}
        assert data["metadata"] == {"source": "test"}
        assert "created_at" in data
        assert "last_active" in data
    
    def test_from_dict_deserialization(self):
        """Test session deserialization from dictionary."""
        original = Session.create(
            user_id="user-1",
            assistant_id="assistant-1",
            session_id="test-session",
            state={"key": "value"},
            metadata={"source": "test"},
        )
        
        data = original.to_dict()
        restored = Session.from_dict(data)
        
        assert restored.session_id == original.session_id
        assert restored.user_id == original.user_id
        assert restored.assistant_id == original.assistant_id
        assert restored.state == original.state
        assert restored.metadata == original.metadata
    
    def test_serialization_roundtrip(self):
        """Test that serialization and deserialization are consistent."""
        session = Session.create(
            user_id="user-1",
            assistant_id="assistant-1",
            state={"nested": {"key": "value"}},
        )
        
        data = session.to_dict()
        restored = Session.from_dict(data)
        data2 = restored.to_dict()
        
        assert data == data2
