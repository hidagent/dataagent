"""Tests for concurrency and isolation.

**Feature: dataagent-server, Property 36: 并发连接隔离性**
**Validates: Requirements 23.4**
"""

import asyncio

import pytest

from dataagent_server.ws import ConnectionManager, WebSocketChatHandler


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, messages_to_receive: list[dict] | None = None):
        self.accepted = False
        self.sent_messages: list[dict] = []
        self._messages_to_receive = messages_to_receive or []
        self._receive_index = 0
        self._receive_event = asyncio.Event()
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: dict):
        self.sent_messages.append(data)
    
    async def receive_json(self) -> dict:
        if self._receive_index >= len(self._messages_to_receive):
            # Wait indefinitely (simulating open connection)
            await self._receive_event.wait()
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect(code=1000)
        
        msg = self._messages_to_receive[self._receive_index]
        self._receive_index += 1
        return msg
    
    def close_connection(self):
        """Signal to close the connection."""
        self._receive_event.set()


class TestConcurrencyIsolation:
    """Tests for concurrent connection isolation.
    
    **Feature: dataagent-server, Property 36: 并发连接隔离性**
    **Validates: Requirements 23.4**
    """
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions_isolated(self):
        """Test that concurrent sessions don't interfere with each other."""
        manager = ConnectionManager(max_connections=100)
        
        # Create multiple sessions
        sessions = {}
        for i in range(10):
            ws = MockWebSocket()
            await manager.connect(ws, f"session-{i}")
            sessions[f"session-{i}"] = ws
        
        # Send different messages to each session
        for i in range(10):
            await manager.send(f"session-{i}", {"session": i, "data": f"msg-{i}"})
        
        # Verify each session only received its own message
        for i in range(10):
            ws = sessions[f"session-{i}"]
            assert len(ws.sent_messages) == 1
            assert ws.sent_messages[0]["session"] == i
    
    @pytest.mark.asyncio
    async def test_one_session_disconnect_doesnt_affect_others(self):
        """Test that disconnecting one session doesn't affect others."""
        manager = ConnectionManager(max_connections=100)
        
        # Create sessions
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await manager.connect(ws1, "session-1")
        await manager.connect(ws2, "session-2")
        await manager.connect(ws3, "session-3")
        
        # Disconnect session-2
        await manager.disconnect("session-2")
        
        # Other sessions should still work
        assert manager.has_connection("session-1")
        assert not manager.has_connection("session-2")
        assert manager.has_connection("session-3")
        
        # Can still send to other sessions
        result1 = await manager.send("session-1", {"test": 1})
        result3 = await manager.send("session-3", {"test": 3})
        
        assert result1 is True
        assert result3 is True
    
    @pytest.mark.asyncio
    async def test_concurrent_task_cancellation_isolated(self):
        """Test that cancelling one task doesn't affect others."""
        manager = ConnectionManager(max_connections=100)
        
        # Create sessions with tasks
        tasks = {}
        
        async def task_for_session(session_id: str):
            try:
                await asyncio.sleep(10)
                return "completed"
            except asyncio.CancelledError:
                return "cancelled"
        
        for i in range(3):
            ws = MockWebSocket()
            await manager.connect(ws, f"session-{i}")
            tasks[f"session-{i}"] = await manager.start_task(
                f"session-{i}", 
                task_for_session(f"session-{i}")
            )
        
        # Cancel only session-1
        await manager.cancel_task("session-1")
        await asyncio.sleep(0.05)  # Give more time for cancellation
        
        # session-1 task should be done (cancelled), others should still be active
        assert tasks["session-1"].done()
        assert not tasks["session-0"].done()
        assert not tasks["session-2"].done()
        
        # Verify session-1 is no longer tracked as active
        assert not manager.has_active_task("session-1")
        assert manager.has_active_task("session-0")
        assert manager.has_active_task("session-2")
        
        # Cleanup
        await manager.cancel_task("session-0")
        await manager.cancel_task("session-2")
    
    @pytest.mark.asyncio
    async def test_concurrent_hitl_decisions_isolated(self):
        """Test that HITL decisions are isolated per session."""
        manager = ConnectionManager(max_connections=100)
        
        # Create sessions
        for i in range(3):
            ws = MockWebSocket()
            await manager.connect(ws, f"session-{i}")
        
        # Start waiting for decisions
        async def wait_for_decision(session_id: str):
            return await manager.wait_for_decision(session_id, timeout=5)
        
        tasks = {
            f"session-{i}": asyncio.create_task(wait_for_decision(f"session-{i}"))
            for i in range(3)
        }
        
        await asyncio.sleep(0.01)
        
        # Resolve only session-1
        manager.resolve_decision("session-1", {"type": "approve", "session": 1})
        
        result1 = await tasks["session-1"]
        assert result1["type"] == "approve"
        assert result1["session"] == 1
        
        # Others should still be waiting
        assert not tasks["session-0"].done()
        assert not tasks["session-2"].done()
        
        # Cancel remaining
        tasks["session-0"].cancel()
        tasks["session-2"].cancel()
        
        try:
            await tasks["session-0"]
        except asyncio.CancelledError:
            pass
        try:
            await tasks["session-2"]
        except asyncio.CancelledError:
            pass
