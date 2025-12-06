"""DataAgent Core - Core library for DataAgent platform."""

from dataagent_core.config import Settings, SessionState
from dataagent_core.engine import AgentFactory, AgentExecutor, AgentConfig
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
from dataagent_core.hitl import HITLHandler, ActionRequest, Decision
from dataagent_core.session import (
    Session,
    SessionStore,
    MemorySessionStore,
    SessionManager,
)
from dataagent_core.mcp import (
    MCPServerConfig,
    MCPConfig,
    MCPConfigLoader,
    MCPConnectionManager,
    MCPConfigStore,
    MemoryMCPConfigStore,
)

__all__ = [
    # Config
    "Settings",
    "SessionState",
    # Engine
    "AgentFactory",
    "AgentExecutor",
    "AgentConfig",
    # Events
    "ExecutionEvent",
    "TextEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "HITLRequestEvent",
    "TodoUpdateEvent",
    "FileOperationEvent",
    "ErrorEvent",
    "DoneEvent",
    # HITL
    "HITLHandler",
    "ActionRequest",
    "Decision",
    # Session
    "Session",
    "SessionStore",
    "MemorySessionStore",
    "SessionManager",
    # MCP
    "MCPServerConfig",
    "MCPConfig",
    "MCPConfigLoader",
    "MCPConnectionManager",
    "MCPConfigStore",
    "MemoryMCPConfigStore",
]
