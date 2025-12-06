"""Unit tests for event serialization."""

import json
import pytest
from dataagent_core.events import (
    ExecutionEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    HITLRequestEvent,
    TodoUpdateEvent,
    FileOperationEvent,
    ErrorEvent,
    DoneEvent,
)


class TestTextEventSerialization:
    """Tests for TextEvent serialization."""

    def test_to_dict_contains_required_fields(self, sample_text_event):
        """Test that to_dict contains event_type and timestamp."""
        result = sample_text_event.to_dict()
        assert "event_type" in result
        assert "timestamp" in result
        assert result["event_type"] == "text"

    def test_to_dict_contains_content_and_is_final(self, sample_text_event):
        """Test that to_dict contains content and is_final fields."""
        result = sample_text_event.to_dict()
        assert "content" in result
        assert "is_final" in result
        assert result["content"] == "Hello, world!"
        assert result["is_final"] is True

    def test_to_dict_is_json_serializable(self, sample_text_event):
        """Test that to_dict result can be serialized to JSON."""
        result = sample_text_event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed == result


class TestToolCallEventSerialization:
    """Tests for ToolCallEvent serialization."""

    def test_to_dict_contains_required_fields(self, sample_tool_call_event):
        """Test that to_dict contains all required fields."""
        result = sample_tool_call_event.to_dict()
        assert result["event_type"] == "tool_call"
        assert "timestamp" in result
        assert result["tool_name"] == "read_file"
        assert result["tool_args"] == {"file_path": "/test/file.txt"}
        assert result["tool_call_id"] == "call_123"

    def test_to_dict_is_json_serializable(self, sample_tool_call_event):
        """Test that to_dict result can be serialized to JSON."""
        result = sample_tool_call_event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestToolResultEventSerialization:
    """Tests for ToolResultEvent serialization."""

    def test_to_dict_contains_required_fields(self, sample_tool_result_event):
        """Test that to_dict contains all required fields."""
        result = sample_tool_result_event.to_dict()
        assert result["event_type"] == "tool_result"
        assert "timestamp" in result
        assert result["tool_call_id"] == "call_123"
        assert result["result"] == "File content here"
        assert result["status"] == "success"

    def test_to_dict_is_json_serializable(self, sample_tool_result_event):
        """Test that to_dict result can be serialized to JSON."""
        result = sample_tool_result_event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestErrorEventSerialization:
    """Tests for ErrorEvent serialization."""

    def test_to_dict_contains_required_fields(self, sample_error_event):
        """Test that to_dict contains all required fields."""
        result = sample_error_event.to_dict()
        assert result["event_type"] == "error"
        assert "timestamp" in result
        assert result["error"] == "Test error"
        assert result["recoverable"] is True

    def test_to_dict_is_json_serializable(self, sample_error_event):
        """Test that to_dict result can be serialized to JSON."""
        result = sample_error_event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestDoneEventSerialization:
    """Tests for DoneEvent serialization."""

    def test_to_dict_contains_required_fields(self, sample_done_event):
        """Test that to_dict contains all required fields."""
        result = sample_done_event.to_dict()
        assert result["event_type"] == "done"
        assert "timestamp" in result
        assert result["cancelled"] is False

    def test_to_dict_is_json_serializable(self, sample_done_event):
        """Test that to_dict result can be serialized to JSON."""
        result = sample_done_event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestFileOperationEventSerialization:
    """Tests for FileOperationEvent serialization."""

    def test_to_dict_contains_required_fields(self):
        """Test that to_dict contains all required fields."""
        event = FileOperationEvent(
            operation="write_file",
            file_path="/test/output.txt",
            metrics={"lines_written": 10, "lines_added": 10, "lines_removed": 0},
            diff="+line1\n+line2",
            status="success",
        )
        result = event.to_dict()
        assert result["event_type"] == "file_operation"
        assert "timestamp" in result
        assert result["operation"] == "write_file"
        assert result["file_path"] == "/test/output.txt"
        assert result["metrics"]["lines_written"] == 10
        assert result["status"] == "success"

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict result can be serialized to JSON."""
        event = FileOperationEvent(
            operation="read_file",
            file_path="/test/input.txt",
            metrics={"lines_read": 5},
            status="success",
        )
        result = event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestTodoUpdateEventSerialization:
    """Tests for TodoUpdateEvent serialization."""

    def test_to_dict_contains_required_fields(self):
        """Test that to_dict contains all required fields."""
        event = TodoUpdateEvent(
            todos=[
                {"content": "Task 1", "status": "completed"},
                {"content": "Task 2", "status": "pending"},
            ]
        )
        result = event.to_dict()
        assert result["event_type"] == "todo_update"
        assert "timestamp" in result
        assert len(result["todos"]) == 2

    def test_to_dict_is_json_serializable(self):
        """Test that to_dict result can be serialized to JSON."""
        event = TodoUpdateEvent(todos=[{"content": "Task", "status": "pending"}])
        result = event.to_dict()
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
