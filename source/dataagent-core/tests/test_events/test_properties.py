"""Property-based tests for event system.

These tests use Hypothesis to verify properties that should hold
across all valid inputs.
"""

import json
import pytest
from hypothesis import given, settings, strategies as st

from dataagent_core.events import (
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    HITLRequestEvent,
    TodoUpdateEvent,
    FileOperationEvent,
    ErrorEvent,
    DoneEvent,
)


# Strategies for generating test data
text_content = st.text(min_size=0, max_size=1000)
tool_names = st.sampled_from(["read_file", "write_file", "edit_file", "shell", "web_search"])
file_paths = st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P")))
tool_call_ids = st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
status_values = st.sampled_from(["success", "error"])


class TestTextEventProperties:
    """Property tests for TextEvent."""

    @settings(max_examples=100)
    @given(content=text_content, is_final=st.booleans())
    def test_text_event_contains_required_fields(self, content: str, is_final: bool):
        """
        **Feature: dataagent-development-specs, Property 4: TextEvent 包含必需字段**
        
        For any text content, TextEvent must contain content and is_final fields.
        """
        event = TextEvent(content=content, is_final=is_final)
        result = event.to_dict()
        
        assert "content" in result
        assert "is_final" in result
        assert result["content"] == content
        assert result["is_final"] == is_final

    @settings(max_examples=100)
    @given(content=text_content, is_final=st.booleans())
    def test_text_event_has_base_fields(self, content: str, is_final: bool):
        """
        **Feature: dataagent-development-specs, Property 2: 事件必须包含基础字段**
        
        For any TextEvent, serialization must include event_type and timestamp.
        """
        event = TextEvent(content=content, is_final=is_final)
        result = event.to_dict()
        
        assert "event_type" in result
        assert "timestamp" in result
        assert result["event_type"] == "text"
        assert isinstance(result["timestamp"], float)

    @settings(max_examples=100)
    @given(content=text_content, is_final=st.booleans())
    def test_text_event_json_serializable(self, content: str, is_final: bool):
        """
        **Feature: dataagent-development-specs, Property 3: 事件序列化结果是有效 JSON**
        
        For any TextEvent, to_dict() result must be valid JSON.
        """
        event = TextEvent(content=content, is_final=is_final)
        result = event.to_dict()
        
        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        
        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["content"] == content
        assert parsed["is_final"] == is_final


class TestToolCallEventProperties:
    """Property tests for ToolCallEvent."""

    @settings(max_examples=100)
    @given(
        tool_name=tool_names,
        tool_call_id=tool_call_ids,
    )
    def test_tool_call_event_contains_required_fields(self, tool_name: str, tool_call_id: str):
        """
        **Feature: dataagent-development-specs, Property 5: ToolCallEvent 包含必需字段**
        
        For any tool call, ToolCallEvent must contain tool_name, tool_args, tool_call_id.
        """
        tool_args = {"path": "/test/file.txt"}
        event = ToolCallEvent(
            tool_name=tool_name,
            tool_args=tool_args,
            tool_call_id=tool_call_id,
        )
        result = event.to_dict()
        
        assert "tool_name" in result
        assert "tool_args" in result
        assert "tool_call_id" in result
        assert result["tool_name"] == tool_name
        assert result["tool_args"] == tool_args
        assert result["tool_call_id"] == tool_call_id

    @settings(max_examples=100)
    @given(tool_name=tool_names, tool_call_id=tool_call_ids)
    def test_tool_call_event_json_serializable(self, tool_name: str, tool_call_id: str):
        """
        **Feature: dataagent-development-specs, Property 3: 事件序列化结果是有效 JSON**
        """
        event = ToolCallEvent(
            tool_name=tool_name,
            tool_args={"key": "value"},
            tool_call_id=tool_call_id,
        )
        result = event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestToolResultEventProperties:
    """Property tests for ToolResultEvent."""

    @settings(max_examples=100)
    @given(
        tool_call_id=tool_call_ids,
        result_content=text_content,
        status=status_values,
    )
    def test_tool_result_event_contains_required_fields(
        self, tool_call_id: str, result_content: str, status: str
    ):
        """
        **Feature: dataagent-development-specs, Property 6: ToolResultEvent 包含必需字段**
        
        For any tool result, ToolResultEvent must contain tool_call_id, result, status.
        """
        event = ToolResultEvent(
            tool_call_id=tool_call_id,
            result=result_content,
            status=status,
        )
        result = event.to_dict()
        
        assert "tool_call_id" in result
        assert "result" in result
        assert "status" in result
        assert result["tool_call_id"] == tool_call_id
        assert result["result"] == result_content
        assert result["status"] == status


class TestErrorEventProperties:
    """Property tests for ErrorEvent."""

    @settings(max_examples=100)
    @given(error_msg=text_content, recoverable=st.booleans())
    def test_error_event_has_base_fields(self, error_msg: str, recoverable: bool):
        """
        **Feature: dataagent-development-specs, Property 2: 事件必须包含基础字段**
        """
        event = ErrorEvent(error=error_msg, recoverable=recoverable)
        result = event.to_dict()
        
        assert "event_type" in result
        assert "timestamp" in result
        assert result["event_type"] == "error"

    @settings(max_examples=100)
    @given(error_msg=text_content, recoverable=st.booleans())
    def test_error_event_json_serializable(self, error_msg: str, recoverable: bool):
        """
        **Feature: dataagent-development-specs, Property 3: 事件序列化结果是有效 JSON**
        """
        event = ErrorEvent(error=error_msg, recoverable=recoverable)
        result = event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestDoneEventProperties:
    """Property tests for DoneEvent."""

    @settings(max_examples=100)
    @given(cancelled=st.booleans())
    def test_done_event_has_base_fields(self, cancelled: bool):
        """
        **Feature: dataagent-development-specs, Property 2: 事件必须包含基础字段**
        """
        event = DoneEvent(cancelled=cancelled)
        result = event.to_dict()
        
        assert "event_type" in result
        assert "timestamp" in result
        assert result["event_type"] == "done"
        assert result["cancelled"] == cancelled

    @settings(max_examples=100)
    @given(cancelled=st.booleans())
    def test_done_event_json_serializable(self, cancelled: bool):
        """
        **Feature: dataagent-development-specs, Property 3: 事件序列化结果是有效 JSON**
        """
        event = DoneEvent(cancelled=cancelled)
        result = event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


from dataagent_core.events import from_dict


class TestEventSerializationRoundtrip:
    """Property tests for event serialization roundtrip (Property 1)."""

    @settings(max_examples=100)
    @given(content=text_content, is_final=st.booleans())
    def test_text_event_roundtrip(self, content: str, is_final: bool):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        
        For any TextEvent, to_dict() followed by from_dict() produces equivalent event.
        """
        original = TextEvent(content=content, is_final=is_final)
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, TextEvent)
        assert restored.content == original.content
        assert restored.is_final == original.is_final
        assert restored.event_type == original.event_type

    @settings(max_examples=100)
    @given(tool_name=tool_names, tool_call_id=tool_call_ids)
    def test_tool_call_event_roundtrip(self, tool_name: str, tool_call_id: str):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        tool_args = {"path": "/test/file.txt", "content": "hello"}
        original = ToolCallEvent(
            tool_name=tool_name,
            tool_args=tool_args,
            tool_call_id=tool_call_id,
        )
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, ToolCallEvent)
        assert restored.tool_name == original.tool_name
        assert restored.tool_args == original.tool_args
        assert restored.tool_call_id == original.tool_call_id

    @settings(max_examples=100)
    @given(tool_call_id=tool_call_ids, status=status_values)
    def test_tool_result_event_roundtrip(self, tool_call_id: str, status: str):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        original = ToolResultEvent(
            tool_call_id=tool_call_id,
            result="test result",
            status=status,
        )
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, ToolResultEvent)
        assert restored.tool_call_id == original.tool_call_id
        assert restored.result == original.result
        assert restored.status == original.status

    @settings(max_examples=100)
    @given(error_msg=text_content, recoverable=st.booleans())
    def test_error_event_roundtrip(self, error_msg: str, recoverable: bool):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        original = ErrorEvent(error=error_msg, recoverable=recoverable)
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, ErrorEvent)
        assert restored.error == original.error
        assert restored.recoverable == original.recoverable

    @settings(max_examples=100)
    @given(cancelled=st.booleans())
    def test_done_event_roundtrip(self, cancelled: bool):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        original = DoneEvent(cancelled=cancelled)
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, DoneEvent)
        assert restored.cancelled == original.cancelled

    def test_file_operation_event_roundtrip(self):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        original = FileOperationEvent(
            operation="write",
            file_path="/test/file.txt",
            metrics={"lines_written": 10},
            diff="+ new line",
            status="success",
        )
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, FileOperationEvent)
        assert restored.operation == original.operation
        assert restored.file_path == original.file_path
        assert restored.metrics == original.metrics
        assert restored.diff == original.diff
        assert restored.status == original.status

    def test_hitl_request_event_roundtrip(self):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        original = HITLRequestEvent(
            interrupt_id="int-123",
            action_requests=[{"name": "write_file", "args": {}}],
        )
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, HITLRequestEvent)
        assert restored.interrupt_id == original.interrupt_id
        assert restored.action_requests == original.action_requests

    def test_todo_update_event_roundtrip(self):
        """
        **Feature: dataagent-development-specs, Property 1: 事件序列化往返一致性**
        """
        original = TodoUpdateEvent(
            todos=[{"id": 1, "text": "Task 1", "done": False}],
        )
        serialized = original.to_dict()
        restored = from_dict(serialized)
        
        assert isinstance(restored, TodoUpdateEvent)
        assert restored.todos == original.todos


class TestFromDictErrors:
    """Tests for from_dict error handling."""

    def test_missing_event_type_raises(self):
        """from_dict should raise ValueError for missing event_type."""
        with pytest.raises(ValueError, match="Missing 'event_type'"):
            from_dict({})

    def test_unknown_event_type_raises(self):
        """from_dict should raise ValueError for unknown event_type."""
        with pytest.raises(ValueError, match="Unknown event type"):
            from_dict({"event_type": "unknown_type"})
