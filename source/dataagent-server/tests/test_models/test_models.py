"""Tests for Pydantic models.

**Feature: dataagent-server, Property 33: Pydantic 模型字段完整性**
**Validates: Requirements 21.2, 21.3, 21.4, 21.5**
"""

from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from dataagent_server.models import (
    CancelResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    SessionInfo,
    WebSocketMessage,
)


class TestChatRequestModel:
    """Tests for ChatRequest model.
    
    **Validates: Requirements 21.2**
    """
    
    def test_required_message_field(self):
        """Test that message field is required."""
        with pytest.raises(ValidationError):
            ChatRequest()
    
    def test_optional_session_id(self):
        """Test that session_id is optional."""
        request = ChatRequest(message="hello")
        assert request.session_id is None
    
    def test_optional_assistant_id(self):
        """Test that assistant_id is optional."""
        request = ChatRequest(message="hello")
        assert request.assistant_id is None
    
    @settings(max_examples=100)
    @given(
        message=st.text(min_size=1),
        session_id=st.text() | st.none(),
        assistant_id=st.text() | st.none(),
    )
    def test_chat_request_accepts_valid_values(
        self,
        message: str,
        session_id: str | None,
        assistant_id: str | None,
    ):
        """Test ChatRequest accepts valid values."""
        request = ChatRequest(
            message=message,
            session_id=session_id,
            assistant_id=assistant_id,
        )
        assert request.message == message
        assert request.session_id == session_id
        assert request.assistant_id == assistant_id


class TestChatResponseModel:
    """Tests for ChatResponse model.
    
    **Validates: Requirements 21.3**
    """
    
    def test_required_session_id(self):
        """Test that session_id is required."""
        with pytest.raises(ValidationError):
            ChatResponse(events=[])
    
    def test_events_default_empty(self):
        """Test that events defaults to empty list."""
        response = ChatResponse(session_id="test")
        assert response.events == []
    
    @settings(max_examples=100)
    @given(
        session_id=st.text(min_size=1),
        events=st.lists(st.fixed_dictionaries({"type": st.text()}), max_size=10),
    )
    def test_chat_response_accepts_valid_values(
        self,
        session_id: str,
        events: list[dict],
    ):
        """Test ChatResponse accepts valid values."""
        response = ChatResponse(session_id=session_id, events=events)
        assert response.session_id == session_id
        assert response.events == events


class TestSessionInfoModel:
    """Tests for SessionInfo model.
    
    **Validates: Requirements 21.4**
    """
    
    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            SessionInfo()
    
    def test_accepts_valid_session_info(self):
        """Test SessionInfo accepts valid values."""
        now = datetime.now()
        info = SessionInfo(
            session_id="sess-123",
            user_id="user-456",
            assistant_id="asst-789",
            created_at=now,
            last_active=now,
        )
        assert info.session_id == "sess-123"
        assert info.user_id == "user-456"
        assert info.assistant_id == "asst-789"
        assert info.created_at == now
        assert info.last_active == now


class TestErrorResponseModel:
    """Tests for ErrorResponse model.
    
    **Validates: Requirements 21.5**
    """
    
    def test_required_error_code(self):
        """Test that error_code is required."""
        with pytest.raises(ValidationError):
            ErrorResponse(message="error")
    
    def test_required_message(self):
        """Test that message is required."""
        with pytest.raises(ValidationError):
            ErrorResponse(error_code="ERR")
    
    def test_optional_details(self):
        """Test that details is optional."""
        response = ErrorResponse(error_code="ERR", message="error")
        assert response.details is None
    
    @settings(max_examples=100)
    @given(
        error_code=st.text(min_size=1, max_size=50),
        message=st.text(min_size=1),
    )
    def test_error_response_accepts_valid_values(
        self,
        error_code: str,
        message: str,
    ):
        """Test ErrorResponse accepts valid values."""
        response = ErrorResponse(error_code=error_code, message=message)
        assert response.error_code == error_code
        assert response.message == message


class TestWebSocketMessageModel:
    """Tests for WebSocketMessage model.
    
    **Validates: Requirements 21.6**
    """
    
    def test_required_type(self):
        """Test that type is required."""
        with pytest.raises(ValidationError):
            WebSocketMessage(payload={})
    
    def test_payload_default_empty(self):
        """Test that payload defaults to empty dict."""
        msg = WebSocketMessage(type="chat")
        assert msg.payload == {}
    
    @settings(max_examples=100)
    @given(
        msg_type=st.sampled_from(["chat", "hitl_decision", "cancel", "ping"]),
        payload=st.fixed_dictionaries({"data": st.text()}),
    )
    def test_websocket_message_accepts_valid_values(
        self,
        msg_type: str,
        payload: dict,
    ):
        """Test WebSocketMessage accepts valid values."""
        msg = WebSocketMessage(type=msg_type, payload=payload)
        assert msg.type == msg_type
        assert msg.payload == payload


class TestHealthResponseModel:
    """Tests for HealthResponse model.
    
    **Validates: Requirements 22.4**
    """
    
    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            HealthResponse()
    
    def test_accepts_valid_health_response(self):
        """Test HealthResponse accepts valid values."""
        response = HealthResponse(
            status="ok",
            version="0.1.0",
            uptime=123.45,
        )
        assert response.status == "ok"
        assert response.version == "0.1.0"
        assert response.uptime == 123.45
