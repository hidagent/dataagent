"""Event system for DataAgent Core."""

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class ExecutionEvent:
    """Base class for execution events."""
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            **self._extra_fields(),
        }

    def _extra_fields(self) -> dict:
        return {}


@dataclass
class TextEvent(ExecutionEvent):
    """Text output event."""
    event_type: str = field(default="text", init=False)
    content: str = ""
    is_final: bool = False

    def _extra_fields(self) -> dict:
        return {"content": self.content, "is_final": self.is_final}


@dataclass
class ToolCallEvent(ExecutionEvent):
    """Tool call event."""
    event_type: str = field(default="tool_call", init=False)
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_call_id: str = ""

    def _extra_fields(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_call_id": self.tool_call_id,
        }


@dataclass
class ToolResultEvent(ExecutionEvent):
    """Tool result event."""
    event_type: str = field(default="tool_result", init=False)
    tool_call_id: str = ""
    result: Any = None
    status: str = "success"

    def _extra_fields(self) -> dict:
        return {
            "tool_call_id": self.tool_call_id,
            "result": self.result,
            "status": self.status,
        }


@dataclass
class HITLRequestEvent(ExecutionEvent):
    """HITL request event."""
    event_type: str = field(default="hitl_request", init=False)
    interrupt_id: str = ""
    action_requests: list = field(default_factory=list)

    def _extra_fields(self) -> dict:
        return {
            "interrupt_id": self.interrupt_id,
            "action_requests": self.action_requests,
        }


@dataclass
class TodoUpdateEvent(ExecutionEvent):
    """Todo update event."""
    event_type: str = field(default="todo_update", init=False)
    todos: list = field(default_factory=list)

    def _extra_fields(self) -> dict:
        return {"todos": self.todos}


@dataclass
class FileOperationEvent(ExecutionEvent):
    """File operation event."""
    event_type: str = field(default="file_operation", init=False)
    operation: str = ""
    file_path: str = ""
    metrics: dict = field(default_factory=dict)
    diff: str | None = None
    status: str = "success"

    def _extra_fields(self) -> dict:
        return {
            "operation": self.operation,
            "file_path": self.file_path,
            "metrics": self.metrics,
            "diff": self.diff,
            "status": self.status,
        }


@dataclass
class ErrorEvent(ExecutionEvent):
    """Error event."""
    event_type: str = field(default="error", init=False)
    error: str = ""
    recoverable: bool = True

    def _extra_fields(self) -> dict:
        return {"error": self.error, "recoverable": self.recoverable}


@dataclass
class DoneEvent(ExecutionEvent):
    """Done event."""
    event_type: str = field(default="done", init=False)
    token_usage: dict | None = None
    cancelled: bool = False

    def _extra_fields(self) -> dict:
        return {"token_usage": self.token_usage, "cancelled": self.cancelled}


# Event type registry for deserialization
_EVENT_TYPES: dict[str, type[ExecutionEvent]] = {}


def _register_event_type(cls: type[ExecutionEvent]) -> type[ExecutionEvent]:
    """Register an event type for deserialization."""
    # Get the default event_type from the class
    instance = cls.__new__(cls)
    instance.event_type = cls.__dataclass_fields__["event_type"].default
    _EVENT_TYPES[instance.event_type] = cls
    return cls


# Register all event types
_register_event_type(TextEvent)
_register_event_type(ToolCallEvent)
_register_event_type(ToolResultEvent)
_register_event_type(HITLRequestEvent)
_register_event_type(TodoUpdateEvent)
_register_event_type(FileOperationEvent)
_register_event_type(ErrorEvent)
_register_event_type(DoneEvent)


def from_dict(data: dict) -> ExecutionEvent:
    """Deserialize an event from a dictionary.
    
    Args:
        data: Dictionary containing event data with 'event_type' field.
        
    Returns:
        The deserialized ExecutionEvent instance.
        
    Raises:
        ValueError: If event_type is missing or unknown.
    """
    event_type = data.get("event_type")
    if not event_type:
        raise ValueError("Missing 'event_type' field in event data")
    
    cls = _EVENT_TYPES.get(event_type)
    if not cls:
        raise ValueError(f"Unknown event type: {event_type}")
    
    # Extract fields for the specific event class
    timestamp = data.get("timestamp", time.time())
    
    if event_type == "text":
        return TextEvent(
            content=data.get("content", ""),
            is_final=data.get("is_final", False),
            timestamp=timestamp,
        )
    elif event_type == "tool_call":
        return ToolCallEvent(
            tool_name=data.get("tool_name", ""),
            tool_args=data.get("tool_args", {}),
            tool_call_id=data.get("tool_call_id", ""),
            timestamp=timestamp,
        )
    elif event_type == "tool_result":
        return ToolResultEvent(
            tool_call_id=data.get("tool_call_id", ""),
            result=data.get("result"),
            status=data.get("status", "success"),
            timestamp=timestamp,
        )
    elif event_type == "hitl_request":
        return HITLRequestEvent(
            interrupt_id=data.get("interrupt_id", ""),
            action_requests=data.get("action_requests", []),
            timestamp=timestamp,
        )
    elif event_type == "todo_update":
        return TodoUpdateEvent(
            todos=data.get("todos", []),
            timestamp=timestamp,
        )
    elif event_type == "file_operation":
        return FileOperationEvent(
            operation=data.get("operation", ""),
            file_path=data.get("file_path", ""),
            metrics=data.get("metrics", {}),
            diff=data.get("diff"),
            status=data.get("status", "success"),
            timestamp=timestamp,
        )
    elif event_type == "error":
        return ErrorEvent(
            error=data.get("error", ""),
            recoverable=data.get("recoverable", True),
            timestamp=timestamp,
        )
    elif event_type == "done":
        return DoneEvent(
            token_usage=data.get("token_usage"),
            cancelled=data.get("cancelled", False),
            timestamp=timestamp,
        )
    
    raise ValueError(f"Unhandled event type: {event_type}")


__all__ = [
    "ExecutionEvent",
    "TextEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "HITLRequestEvent",
    "TodoUpdateEvent",
    "FileOperationEvent",
    "ErrorEvent",
    "DoneEvent",
    "from_dict",
]
