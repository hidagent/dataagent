"""Tests for Settings configuration."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from dataagent_core.config import Settings, SessionState, get_default_coding_instructions


class TestSettings:
    """Tests for Settings class."""

    def test_from_environment_loads_api_keys(self):
        """
        **Feature: dataagent-development-specs, Property 16: Settings 从环境变量加载**
        
        Test that Settings loads API keys from environment variables.
        """
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "TAVILY_API_KEY": "test-tavily-key",
        }, clear=False):
            settings = Settings.from_environment()
            
            assert settings.openai_api_key == "test-openai-key"
            assert settings.anthropic_api_key == "test-anthropic-key"
            assert settings.tavily_api_key == "test-tavily-key"

    def test_has_properties(self):
        """Test has_* properties work correctly."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
        }, clear=True):
            settings = Settings.from_environment()
            
            assert settings.has_openai is True
            assert settings.has_anthropic is False
            assert settings.has_tavily is False

    def test_ensure_agent_dir_creates_directory(self, tmp_path):
        """
        **Feature: dataagent-development-specs, Property 17: ensure_agent_dir 创建目录**
        
        Test that ensure_agent_dir creates the agent directory.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
            
            # Mock the home directory
            with patch.object(Path, 'home', return_value=tmp_path):
                agent_dir = settings.ensure_agent_dir("test-agent")
                
                assert agent_dir.exists()
                assert agent_dir.is_dir()
                assert agent_dir.name == "test-agent"

    def test_get_agent_dir_validates_name(self):
        """Test that get_agent_dir validates agent names."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
            
            # Valid names
            settings.get_agent_dir("my-agent")
            settings.get_agent_dir("agent_123")
            settings.get_agent_dir("Agent Name")
            
            # Invalid names
            with pytest.raises(ValueError):
                settings.get_agent_dir("")
            
            with pytest.raises(ValueError):
                settings.get_agent_dir("   ")

    def test_default_values_when_env_not_set(self):
        """
        **Feature: dataagent-development-specs, Property 18: 未设置环境变量时使用默认值**
        
        Test that Settings uses None for unset environment variables.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
            
            assert settings.openai_api_key is None
            assert settings.anthropic_api_key is None
            assert settings.google_api_key is None
            assert settings.tavily_api_key is None

    def test_user_deepagents_dir(self):
        """Test user_deepagents_dir property."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
            
            expected = Path.home() / ".deepagents"
            assert settings.user_deepagents_dir == expected


class TestSessionState:
    """Tests for SessionState class."""

    def test_initial_state(self):
        """Test initial session state."""
        state = SessionState(auto_approve=False)
        
        assert state.auto_approve is False
        assert state.thread_id is not None
        assert len(state.thread_id) > 0

    def test_toggle_auto_approve(self):
        """Test toggling auto_approve."""
        state = SessionState(auto_approve=False)
        
        result = state.toggle_auto_approve()
        assert result is True
        assert state.auto_approve is True
        
        result = state.toggle_auto_approve()
        assert result is False
        assert state.auto_approve is False

    def test_thread_id_is_unique(self):
        """Test that each session gets a unique thread_id."""
        state1 = SessionState()
        state2 = SessionState()
        
        assert state1.thread_id != state2.thread_id


class TestGetDefaultCodingInstructions:
    """Tests for get_default_coding_instructions function."""

    def test_returns_string(self):
        """Test that function returns a string."""
        result = get_default_coding_instructions()
        assert isinstance(result, str)
        assert len(result) > 0
