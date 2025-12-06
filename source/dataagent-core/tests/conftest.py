"""Pytest configuration and fixtures for DataAgent Core tests."""

import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from dataagent_core.config import Settings
    
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "TAVILY_API_KEY": "test-tavily-key",
    }):
        yield Settings.from_environment()


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create a temporary agent directory."""
    agent_dir = tmp_path / ".deepagents" / "test-agent"
    agent_dir.mkdir(parents=True)
    return agent_dir


@pytest.fixture
def sample_text_event():
    """Create a sample TextEvent."""
    from dataagent_core.events import TextEvent
    return TextEvent(content="Hello, world!", is_final=True)


@pytest.fixture
def sample_tool_call_event():
    """Create a sample ToolCallEvent."""
    from dataagent_core.events import ToolCallEvent
    return ToolCallEvent(
        tool_name="read_file",
        tool_args={"file_path": "/test/file.txt"},
        tool_call_id="call_123",
    )


@pytest.fixture
def sample_tool_result_event():
    """Create a sample ToolResultEvent."""
    from dataagent_core.events import ToolResultEvent
    return ToolResultEvent(
        tool_call_id="call_123",
        result="File content here",
        status="success",
    )


@pytest.fixture
def sample_error_event():
    """Create a sample ErrorEvent."""
    from dataagent_core.events import ErrorEvent
    return ErrorEvent(error="Test error", recoverable=True)


@pytest.fixture
def sample_done_event():
    """Create a sample DoneEvent."""
    from dataagent_core.events import DoneEvent
    return DoneEvent(cancelled=False)
