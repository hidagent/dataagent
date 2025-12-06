"""Tests for WebSocket connection manager.

**Feature: dataagent-server, Property 28: WebSocket 连接断开资源清理**
**Feature: dataagent-server, Property 37: 连接管理器线程安全**
**Feature: dataagent-server, Property 38: 系统过载保护**
**Validates: Requirements 17.6, 23.5, 23.6**
"""

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_server.ws import ConnectionManager


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.messages: list[dict] = []
    
    async def accept(self):
        self.accepted = True
    
    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True
    
    async def send_json(self, data: dict):
        self.messages.append(data)
    
    async def receive_json(self) -> dict:
        return {"type": "ping", "payload": {}}


class TestConnectionManager:
    """Tests for ConnectionManager."""
    
    @pytest.fixture
    def manager(self):
        """Create connection manager."""
        return ConnectionManager(max_connections=5)
    
    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager):
        """Test connect accepts WebSocket."""
        ws = MockWebSocket()
        result = await manager.connect(ws, "session-1")
        assert result is True
        assert ws.accepted is True
        assert manager.has_connection("session-1")
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager):
        """Test disconnect removes connection.
        
        **Feature: dataagent-server, Property 28: WebSocket 连接断开资源清理**
        **Validates: Requirements 17.6**
        """
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        assert manager.has_connection("session-1")
        
        await manager.disconnect("session-1")
        assert not manager.has_connection("session-1")
    
    @pytest.mark.asyncio
    async def test_disconnect_cancels_pending_decision(self, manager):
        """Test disconnect cancels pending HITL decision.
        
        **Feature: dataagent-server, Property 28: WebSocket 连接断开资源清理**
        **Validates: Requirements 17.6**
        """
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start waiting for decision in background
        async def wait_decision():
            return await manager.wait_for_decision("session-1", timeout=10)
        
        task = asyncio.create_task(wait_decision())
        await asyncio.sleep(0.01)  # Let task start
        
        # Disconnect should cancel the wait
        await manager.disconnect("session-1")
        
        result = await task
        assert result is None  # Cancelled
    
    @pytest.mark.asyncio
    async def test_disconnect_cancels_active_task(self, manager):
        """Test disconnect cancels active task.
        
        **Feature: dataagent-server, Property 28: WebSocket 连接断开资源清理**
        **Validates: Requirements 17.6**
        """
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start a long-running task
        async def long_task():
            try:
                await asyncio.sleep(10)
                return "done"
            except asyncio.CancelledError:
                raise
        
        task = await manager.start_task("session-1", long_task())
        assert manager.has_active_task("session-1")
        
        # Disconnect should cancel the task
        await manager.disconnect("session-1")
        
        # Wait a bit for cancellation to propagate
        await asyncio.sleep(0.01)
        
        assert task.cancelled() or task.done()
    
    @pytest.mark.asyncio
    async def test_max_connections_limit(self, manager):
        """Test max connections limit.
        
        **Feature: dataagent-server, Property 38: 系统过载保护**
        **Validates: Requirements 23.6**
        """
        # Fill up connections
        for i in range(5):
            ws = MockWebSocket()
            result = await manager.connect(ws, f"session-{i}")
            assert result is True
        
        # Next connection should fail
        ws = MockWebSocket()
        result = await manager.connect(ws, "session-overflow")
        assert result is False
        assert ws.accepted is False
    
    @pytest.mark.asyncio
    async def test_is_at_capacity(self, manager):
        """Test is_at_capacity property."""
        assert not manager.is_at_capacity
        
        for i in range(5):
            ws = MockWebSocket()
            await manager.connect(ws, f"session-{i}")
        
        assert manager.is_at_capacity
    
    @pytest.mark.asyncio
    async def test_send_to_connected_session(self, manager):
        """Test sending message to connected session."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        result = await manager.send("session-1", {"test": "data"})
        assert result is True
        assert len(ws.messages) == 1
        assert ws.messages[0] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_send_to_disconnected_session(self, manager):
        """Test sending message to disconnected session."""
        result = await manager.send("nonexistent", {"test": "data"})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, manager):
        """Test cancelling active task."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        async def long_task():
            await asyncio.sleep(10)
        
        await manager.start_task("session-1", long_task())
        
        result = await manager.cancel_task("session-1")
        assert result is True
        assert not manager.has_active_task("session-1")
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, manager):
        """Test cancelling nonexistent task."""
        result = await manager.cancel_task("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resolve_decision(self, manager):
        """Test resolving HITL decision."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start waiting for decision
        async def wait_decision():
            return await manager.wait_for_decision("session-1", timeout=5)
        
        task = asyncio.create_task(wait_decision())
        await asyncio.sleep(0.01)
        
        # Resolve the decision
        decision = {"type": "approve", "message": "ok"}
        result = manager.resolve_decision("session-1", decision)
        assert result is True
        
        # Wait should return the decision
        received = await task
        assert received == decision
    
    @pytest.mark.asyncio
    async def test_wait_for_decision_timeout(self, manager):
        """Test HITL decision timeout."""
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        result = await manager.wait_for_decision("session-1", timeout=0.1)
        assert result is None


class TestConnectionManagerConcurrency:
    """Concurrency tests for ConnectionManager.
    
    **Feature: dataagent-server, Property 37: 连接管理器线程安全**
    **Validates: Requirements 23.5**
    """
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test concurrent connection operations."""
        manager = ConnectionManager(max_connections=100)
        
        async def connect_and_disconnect(session_id: str):
            ws = MockWebSocket()
            await manager.connect(ws, session_id)
            await asyncio.sleep(0.01)
            await manager.disconnect(session_id)
        
        # Run many concurrent operations
        tasks = [
            connect_and_disconnect(f"session-{i}")
            for i in range(50)
        ]
        await asyncio.gather(*tasks)
        
        # All should be disconnected
        assert manager.connection_count == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_sends(self):
        """Test concurrent send operations."""
        manager = ConnectionManager(max_connections=100)
        
        # Connect multiple sessions
        websockets = {}
        for i in range(10):
            ws = MockWebSocket()
            await manager.connect(ws, f"session-{i}")
            websockets[f"session-{i}"] = ws
        
        # Send to all concurrently
        async def send_message(session_id: str):
            for j in range(10):
                await manager.send(session_id, {"msg": j})
        
        tasks = [send_message(f"session-{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Each should have received 10 messages
        for ws in websockets.values():
            assert len(ws.messages) == 10
