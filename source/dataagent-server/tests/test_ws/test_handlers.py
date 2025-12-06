"""Tests for WebSocket handlers.

**Feature: dataagent-server, Property 26: WebSocket 消息格式验证**
**Feature: dataagent-server, Property 27: 服务端事件推送格式**
**Feature: dataagent-server, Property 39: 取消消息响应**
**Validates: Requirements 17.3, 17.4, 17.5, 24.2, 24.3**
"""

import asyncio
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_server.ws import ConnectionManager, WebSocketChatHandler


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, messages_to_receive: list[dict] | None = None):
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.sent_messages: list[dict] = []
        self._messages_to_receive = messages_to_receive or []
        self._receive_index = 0
    
    async def accept(self):
        self.accepted = True
    
    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True
        self.close_code = code
        self.close_reason = reason
    
    async def send_json(self, data: dict):
        self.sent_messages.append(data)
    
    async def receive_json(self) -> dict:
        if self._receive_index >= len(self._messages_to_receive):
            # Simulate disconnect
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect(code=1000)
        
        msg = self._messages_to_receive[self._receive_index]
        self._receive_index += 1
        return msg


class TestWebSocketMessageValidation:
    """Tests for WebSocket message validation.
    
    **Feature: dataagent-server, Property 26: WebSocket 消息格式验证**
    **Validates: Requirements 17.3**
    """
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager(max_connections=10)
    
    @pytest.fixture
    def handler(self, manager):
        return WebSocketChatHandler(manager)
    
    @pytest.mark.asyncio
    async def test_valid_message_format(self, handler, manager):
        """Test valid message with type and payload is accepted."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "ping", "payload": {}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        # Should have received connected and pong messages
        assert len(ws.sent_messages) >= 2
        assert ws.sent_messages[0]["event_type"] == "connected"
        assert ws.sent_messages[1]["event_type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_missing_type_field(self, handler, manager):
        """Test message without type field is rejected."""
        ws = MockWebSocket(messages_to_receive=[
            {"payload": {}},  # Missing type
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        # Should have error message
        error_msgs = [m for m in ws.sent_messages if m.get("event_type") == "error"]
        assert len(error_msgs) >= 1
        assert "type" in error_msgs[0]["data"]["message"].lower() or "payload" in error_msgs[0]["data"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_missing_payload_field(self, handler, manager):
        """Test message without payload field is rejected."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "chat"},  # Missing payload
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        # Should have error message
        error_msgs = [m for m in ws.sent_messages if m.get("event_type") == "error"]
        assert len(error_msgs) >= 1


class TestServerEventFormat:
    """Tests for server event format.
    
    **Feature: dataagent-server, Property 27: 服务端事件推送格式**
    **Validates: Requirements 17.4, 17.5**
    """
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager(max_connections=10)
    
    @pytest.fixture
    def handler(self, manager):
        return WebSocketChatHandler(manager)
    
    @pytest.mark.asyncio
    async def test_event_contains_event_type(self, handler, manager):
        """Test server events contain event_type field."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "ping", "payload": {}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        for msg in ws.sent_messages:
            assert "event_type" in msg
    
    @pytest.mark.asyncio
    async def test_event_contains_timestamp(self, handler, manager):
        """Test server events contain timestamp field."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "ping", "payload": {}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        for msg in ws.sent_messages:
            assert "timestamp" in msg
            assert isinstance(msg["timestamp"], (int, float))
    
    @pytest.mark.asyncio
    async def test_event_contains_data(self, handler, manager):
        """Test server events contain data field."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "ping", "payload": {}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        for msg in ws.sent_messages:
            assert "data" in msg


class TestCancelMessage:
    """Tests for cancel message handling.
    
    **Feature: dataagent-server, Property 39: 取消消息响应**
    **Validates: Requirements 24.2, 24.3**
    """
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager(max_connections=10)
    
    @pytest.fixture
    def handler(self, manager):
        return WebSocketChatHandler(manager)
    
    @pytest.mark.asyncio
    async def test_cancel_sends_done_event(self, handler, manager):
        """Test cancel message sends DoneEvent with cancelled=True."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "cancel", "payload": {}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        # Find done event
        done_msgs = [m for m in ws.sent_messages if m.get("event_type") == "done"]
        assert len(done_msgs) >= 1
        assert done_msgs[0]["data"]["cancelled"] is True
    
    @pytest.mark.asyncio
    async def test_cancel_with_active_task(self, handler, manager):
        """Test cancel with active task cancels it."""
        # First connect
        ws1 = MockWebSocket()
        await manager.connect(ws1, "session-1")
        
        # Start a task
        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise
        
        task = await manager.start_task("session-1", long_task())
        
        # Now handle cancel
        ws2 = MockWebSocket(messages_to_receive=[
            {"type": "cancel", "payload": {}},
        ])
        # Manually set the connection to our new mock
        manager._connections["session-1"] = ws2
        
        await handler._handle_cancel("session-1")
        
        # Wait a bit for cancellation to propagate
        await asyncio.sleep(0.01)
        
        # Task should be cancelled
        assert task.cancelled() or task.done()
        
        # Done event should be sent
        done_msgs = [m for m in ws2.sent_messages if m.get("event_type") == "done"]
        assert len(done_msgs) >= 1
        assert done_msgs[0]["data"]["cancelled"] is True


class TestChatMessage:
    """Tests for chat message handling."""
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager(max_connections=10)
    
    @pytest.fixture
    def handler(self, manager):
        return WebSocketChatHandler(manager)
    
    @pytest.mark.asyncio
    async def test_chat_sends_response(self, handler, manager):
        """Test chat message sends response."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "chat", "payload": {"message": "hello"}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        # Should have text and done events
        text_msgs = [m for m in ws.sent_messages if m.get("event_type") == "text"]
        done_msgs = [m for m in ws.sent_messages if m.get("event_type") == "done"]
        
        assert len(text_msgs) >= 1
        assert len(done_msgs) >= 1
    
    @pytest.mark.asyncio
    async def test_empty_chat_message_rejected(self, handler, manager):
        """Test empty chat message is rejected."""
        ws = MockWebSocket(messages_to_receive=[
            {"type": "chat", "payload": {"message": ""}},
        ])
        
        await handler.handle_connection(ws, "session-1")
        
        # Should have error message
        error_msgs = [m for m in ws.sent_messages if m.get("event_type") == "error"]
        assert len(error_msgs) >= 1
