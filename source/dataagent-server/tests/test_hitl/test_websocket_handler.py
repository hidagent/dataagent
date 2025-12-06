"""Tests for WebSocket HITL handler.

**Feature: dataagent-server, Property 29: HITL 超时自动拒绝**
**Validates: Requirements 18.5**
"""

import asyncio

import pytest

from dataagent_server.hitl import WebSocketHITLHandler
from dataagent_server.ws import ConnectionManager


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.accepted = False
        self.sent_messages: list[dict] = []
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: dict):
        self.sent_messages.append(data)


class TestWebSocketHITLHandler:
    """Tests for WebSocketHITLHandler."""
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager(max_connections=10)
    
    @pytest.fixture
    def handler(self, manager):
        return WebSocketHITLHandler(manager, timeout=0.5)
    
    @pytest.mark.asyncio
    async def test_request_approval_sends_hitl_event(self, handler, manager):
        """Test request_approval sends HITL request event."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start approval request in background
        async def request():
            return await handler.request_approval(
                {"name": "test", "args": {}, "description": "test action"},
                "session-1",
            )
        
        task = asyncio.create_task(request())
        await asyncio.sleep(0.01)
        
        # Should have sent HITL request
        hitl_msgs = [m for m in ws.sent_messages if m.get("event_type") == "hitl_request"]
        assert len(hitl_msgs) >= 1
        assert "action_request" in hitl_msgs[0]["data"]
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_timeout_returns_reject(self, handler, manager):
        """Test timeout returns reject decision.
        
        **Feature: dataagent-server, Property 29: HITL 超时自动拒绝**
        **Validates: Requirements 18.5**
        """
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Request approval with short timeout
        result = await handler.request_approval(
            {"name": "test", "args": {}, "description": "test action"},
            "session-1",
        )
        
        # Should return reject due to timeout
        assert result["type"] == "reject"
        assert "timeout" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_approved_decision_returned(self, handler, manager):
        """Test approved decision is returned."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start approval request
        async def request():
            return await handler.request_approval(
                {"name": "test", "args": {}, "description": "test action"},
                "session-1",
            )
        
        task = asyncio.create_task(request())
        await asyncio.sleep(0.01)
        
        # Resolve with approve
        manager.resolve_decision("session-1", {"type": "approve", "message": "ok"})
        
        result = await task
        assert result["type"] == "approve"
        assert result["message"] == "ok"
    
    @pytest.mark.asyncio
    async def test_rejected_decision_returned(self, handler, manager):
        """Test rejected decision is returned."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start approval request
        async def request():
            return await handler.request_approval(
                {"name": "test", "args": {}, "description": "test action"},
                "session-1",
            )
        
        task = asyncio.create_task(request())
        await asyncio.sleep(0.01)
        
        # Resolve with reject
        manager.resolve_decision("session-1", {"type": "reject", "message": "denied"})
        
        result = await task
        assert result["type"] == "reject"
        assert result["message"] == "denied"


class TestHITLTimeoutProperty:
    """Property tests for HITL timeout.
    
    **Feature: dataagent-server, Property 29: HITL 超时自动拒绝**
    **Validates: Requirements 18.5**
    """
    
    @pytest.mark.asyncio
    async def test_timeout_always_rejects(self):
        """Test that timeout always results in rejection."""
        manager = ConnectionManager(max_connections=10)
        handler = WebSocketHITLHandler(manager, timeout=0.1)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Multiple timeout tests
        for i in range(3):
            result = await handler.request_approval(
                {"name": f"test-{i}", "args": {}, "description": "test"},
                "session-1",
            )
            assert result["type"] == "reject"
    
    @pytest.mark.asyncio
    async def test_disconnect_during_wait_returns_reject(self):
        """Test that disconnect during wait returns reject."""
        manager = ConnectionManager(max_connections=10)
        handler = WebSocketHITLHandler(manager, timeout=5)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start approval request
        async def request():
            return await handler.request_approval(
                {"name": "test", "args": {}, "description": "test"},
                "session-1",
            )
        
        task = asyncio.create_task(request())
        await asyncio.sleep(0.01)
        
        # Disconnect
        await manager.disconnect("session-1")
        
        result = await task
        assert result["type"] == "reject"
