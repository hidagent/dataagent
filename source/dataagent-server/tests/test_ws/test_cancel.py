"""Tests for cancel functionality.

**Feature: dataagent-server, Property 40: 取消操作及时性**
**Feature: dataagent-server, Property 41: 取消后资源清理**
**Validates: Requirements 24.5, 24.6**
"""

import asyncio
import time

import pytest

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


class TestCancelTimeliness:
    """Tests for cancel operation timeliness.
    
    **Feature: dataagent-server, Property 40: 取消操作及时性**
    **Validates: Requirements 24.5**
    """
    
    @pytest.mark.asyncio
    async def test_cancel_responds_within_1_second(self):
        """Test that cancel operation responds within 1 second."""
        manager = ConnectionManager(max_connections=10)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start a long-running task
        async def long_task():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise
        
        await manager.start_task("session-1", long_task())
        
        # Measure cancel time
        start_time = time.time()
        result = await manager.cancel_task("session-1")
        end_time = time.time()
        
        assert result is True
        assert (end_time - start_time) < 1.0  # Should complete within 1 second
    
    @pytest.mark.asyncio
    async def test_multiple_cancels_all_fast(self):
        """Test that multiple cancel operations are all fast."""
        manager = ConnectionManager(max_connections=100)
        
        # Create many sessions with tasks
        for i in range(20):
            ws = MockWebSocket()
            await manager.connect(ws, f"session-{i}")
            
            async def long_task():
                try:
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    raise
            
            await manager.start_task(f"session-{i}", long_task())
        
        # Cancel all and measure time
        start_time = time.time()
        
        for i in range(20):
            await manager.cancel_task(f"session-{i}")
        
        end_time = time.time()
        
        # All cancels should complete within 1 second total
        assert (end_time - start_time) < 1.0


class TestCancelResourceCleanup:
    """Tests for resource cleanup after cancel.
    
    **Feature: dataagent-server, Property 41: 取消后资源清理**
    **Validates: Requirements 24.6**
    """
    
    @pytest.mark.asyncio
    async def test_cancel_removes_active_task(self):
        """Test that cancel removes the active task."""
        manager = ConnectionManager(max_connections=10)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        async def long_task():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise
        
        await manager.start_task("session-1", long_task())
        assert manager.has_active_task("session-1")
        
        await manager.cancel_task("session-1")
        
        # Task should be removed
        assert not manager.has_active_task("session-1")
    
    @pytest.mark.asyncio
    async def test_cancel_allows_new_task(self):
        """Test that after cancel, a new task can be started."""
        manager = ConnectionManager(max_connections=10)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # First task
        async def task1():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise
        
        await manager.start_task("session-1", task1())
        await manager.cancel_task("session-1")
        
        # Should be able to start new task
        async def task2():
            return "completed"
        
        new_task = await manager.start_task("session-1", task2())
        result = await new_task
        
        assert result == "completed"
    
    @pytest.mark.asyncio
    async def test_disconnect_after_cancel_cleans_all(self):
        """Test that disconnect after cancel cleans up everything."""
        manager = ConnectionManager(max_connections=10)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        async def long_task():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise
        
        await manager.start_task("session-1", long_task())
        await manager.cancel_task("session-1")
        await manager.disconnect("session-1")
        
        # Everything should be cleaned up
        assert not manager.has_connection("session-1")
        assert not manager.has_active_task("session-1")
        assert manager.connection_count == 0
    
    @pytest.mark.asyncio
    async def test_cancel_cleans_pending_decision(self):
        """Test that cancel also cleans up pending HITL decisions."""
        manager = ConnectionManager(max_connections=10)
        
        ws = MockWebSocket()
        await manager.connect(ws, "session-1")
        
        # Start waiting for decision
        async def wait_decision():
            return await manager.wait_for_decision("session-1", timeout=60)
        
        decision_task = asyncio.create_task(wait_decision())
        await asyncio.sleep(0.01)
        
        # Start and cancel a task
        async def long_task():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise
        
        await manager.start_task("session-1", long_task())
        await manager.cancel_task("session-1")
        
        # Disconnect should clean up the pending decision too
        await manager.disconnect("session-1")
        
        # Decision task should complete (with None due to cancellation)
        result = await decision_task
        assert result is None
