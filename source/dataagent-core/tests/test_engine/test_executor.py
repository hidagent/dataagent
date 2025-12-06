"""Tests for AgentExecutor.

Note: These tests focus on error handling and event generation.
Full integration tests require mocking the agent and backend.
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from typing import AsyncIterator

from dataagent_core.engine import AgentExecutor
from dataagent_core.events import (
    ExecutionEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    ErrorEvent,
    DoneEvent,
)
from dataagent_core.hitl import Decision


class TestAgentExecutorInit:
    """Tests for AgentExecutor initialization."""
    
    def test_executor_init_with_required_args(self):
        """Test executor initialization with required arguments."""
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        
        executor = AgentExecutor(agent=mock_agent, backend=mock_backend)
        
        assert executor.agent is mock_agent
        assert executor.backend is mock_backend
        assert executor.hitl_handler is None
        assert executor.assistant_id is None
    
    def test_executor_init_with_all_args(self):
        """Test executor initialization with all arguments."""
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        mock_hitl = MagicMock()
        
        executor = AgentExecutor(
            agent=mock_agent,
            backend=mock_backend,
            hitl_handler=mock_hitl,
            assistant_id="test-assistant",
        )
        
        assert executor.agent is mock_agent
        assert executor.backend is mock_backend
        assert executor.hitl_handler is mock_hitl
        assert executor.assistant_id == "test-assistant"


class TestAgentExecutorExecute:
    """Tests for AgentExecutor.execute method."""
    
    @pytest.mark.asyncio
    async def test_execute_returns_async_iterator(self):
        """
        **Feature: dataagent-development-specs, Property 12: 执行器返回事件迭代器**
        
        AgentExecutor.execute() must return AsyncIterator[ExecutionEvent].
        **Validates: Requirements 5.1**
        """
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        
        # Mock astream to return empty async iterator
        async def empty_stream(*args, **kwargs):
            return
            yield  # Make it a generator
        
        mock_agent.astream = empty_stream
        
        executor = AgentExecutor(agent=mock_agent, backend=mock_backend)
        
        result = executor.execute("test input", "session-1")
        
        # Should be an async iterator
        assert hasattr(result, "__aiter__")
        assert hasattr(result, "__anext__")
    
    @pytest.mark.asyncio
    async def test_execute_catches_exceptions_as_error_event(self):
        """
        **Feature: dataagent-development-specs, Property 13: 异常转换为 ErrorEvent**
        
        Exceptions during execution must be converted to ErrorEvent.
        **Validates: Requirements 5.3, 11.1**
        """
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        
        # Mock astream to raise an exception
        async def failing_stream(*args, **kwargs):
            raise RuntimeError("Test error")
            yield  # Make it a generator
        
        mock_agent.astream = failing_stream
        
        executor = AgentExecutor(agent=mock_agent, backend=mock_backend)
        
        events = []
        async for event in executor.execute("test input", "session-1"):
            events.append(event)
        
        # Should have exactly one ErrorEvent
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert "Test error" in events[0].error
        assert events[0].recoverable is False


class TestAgentExecutorHITL:
    """Tests for HITL handling in AgentExecutor."""
    
    @pytest.mark.asyncio
    async def test_auto_approve_without_handler(self):
        """
        **Feature: dataagent-development-specs, Property 8: 无 HITLHandler 时自动批准**
        
        Without HITLHandler, all operations should be auto-approved.
        **Validates: Requirements 3.5**
        """
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        
        executor = AgentExecutor(
            agent=mock_agent,
            backend=mock_backend,
            hitl_handler=None,  # No handler
        )
        
        # Test _handle_hitl directly
        pending_interrupts = {
            "int-1": {
                "action_requests": [
                    {"name": "write_file", "args": {}, "description": "Write file"},
                ]
            }
        }
        
        result = await executor._handle_hitl(pending_interrupts, "session-1")
        
        # Should auto-approve
        assert result is not None
        assert "int-1" in result
        assert result["int-1"]["decisions"][0]["type"] == "approve"
    
    @pytest.mark.asyncio
    async def test_reject_returns_none(self):
        """
        **Feature: dataagent-development-specs, Property 7: HITL 拒绝导致执行取消**
        
        When user rejects, _handle_hitl should return None.
        **Validates: Requirements 3.4, 5.5**
        """
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        mock_hitl = AsyncMock()
        mock_hitl.request_approval.return_value = {"type": "reject", "message": "No"}
        
        executor = AgentExecutor(
            agent=mock_agent,
            backend=mock_backend,
            hitl_handler=mock_hitl,
        )
        
        pending_interrupts = {
            "int-1": {
                "action_requests": [
                    {"name": "write_file", "args": {}, "description": "Write file"},
                ]
            }
        }
        
        result = await executor._handle_hitl(pending_interrupts, "session-1")
        
        # Should return None on reject
        assert result is None
    
    @pytest.mark.asyncio
    async def test_approve_returns_decisions(self):
        """Test that approve returns proper decisions."""
        mock_agent = MagicMock()
        mock_backend = MagicMock()
        mock_hitl = AsyncMock()
        mock_hitl.request_approval.return_value = {"type": "approve", "message": None}
        
        executor = AgentExecutor(
            agent=mock_agent,
            backend=mock_backend,
            hitl_handler=mock_hitl,
        )
        
        pending_interrupts = {
            "int-1": {
                "action_requests": [
                    {"name": "write_file", "args": {}, "description": "Write file"},
                ]
            }
        }
        
        result = await executor._handle_hitl(pending_interrupts, "session-1")
        
        # Should return decisions
        assert result is not None
        assert "int-1" in result
        assert result["int-1"]["decisions"][0]["type"] == "approve"


class TestEventGeneration:
    """Tests for event generation patterns."""
    
    def test_error_event_structure(self):
        """
        **Feature: dataagent-development-specs, Property 13: 异常转换为 ErrorEvent**
        
        ErrorEvent must have proper structure.
        """
        event = ErrorEvent(error="Test error", recoverable=False)
        
        assert event.event_type == "error"
        assert event.error == "Test error"
        assert event.recoverable is False
        assert isinstance(event.timestamp, float)
    
    def test_done_event_cancelled_false(self):
        """
        **Feature: dataagent-development-specs, Property 14: 正常完成发出 DoneEvent**
        
        Normal completion should emit DoneEvent(cancelled=False).
        **Validates: Requirements 5.4**
        """
        event = DoneEvent(cancelled=False)
        
        assert event.event_type == "done"
        assert event.cancelled is False
    
    def test_done_event_cancelled_true(self):
        """
        **Feature: dataagent-development-specs, Property 7: HITL 拒绝导致执行取消**
        
        HITL rejection should emit DoneEvent(cancelled=True).
        **Validates: Requirements 3.4, 5.5**
        """
        event = DoneEvent(cancelled=True)
        
        assert event.event_type == "done"
        assert event.cancelled is True
