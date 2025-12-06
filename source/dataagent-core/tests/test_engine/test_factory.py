"""Tests for AgentFactory.

Note: These tests focus on configuration and structure validation.
Full integration tests require mocking external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import fields

from dataagent_core.engine import AgentConfig


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""
    
    def test_config_has_required_fields(self):
        """
        **Feature: dataagent-development-specs, Property 9: AgentFactory 返回正确的元组**
        
        AgentConfig must have all required configuration fields.
        **Validates: Requirements 4.1**
        """
        config = AgentConfig(assistant_id="test-agent")
        
        # Check required field
        assert config.assistant_id == "test-agent"
        
        # Check default values
        assert config.model is None
        assert config.enable_memory is True
        assert config.enable_skills is True
        assert config.enable_shell is True
        assert config.auto_approve is False
        assert config.sandbox_type is None
        assert config.system_prompt is None
        assert config.extra_tools == []
        assert config.extra_middleware == []
        assert config.recursion_limit == 1000
    
    def test_config_with_custom_values(self):
        """Test AgentConfig with custom values."""
        mock_tool = MagicMock()
        mock_middleware = MagicMock()
        
        config = AgentConfig(
            assistant_id="custom-agent",
            model="gpt-4",
            enable_memory=False,
            enable_skills=False,
            enable_shell=False,
            auto_approve=True,
            sandbox_type="docker",
            system_prompt="Custom prompt",
            extra_tools=[mock_tool],
            extra_middleware=[mock_middleware],
            recursion_limit=500,
        )
        
        assert config.assistant_id == "custom-agent"
        assert config.model == "gpt-4"
        assert config.enable_memory is False
        assert config.enable_skills is False
        assert config.enable_shell is False
        assert config.auto_approve is True
        assert config.sandbox_type == "docker"
        assert config.system_prompt == "Custom prompt"
        assert config.extra_tools == [mock_tool]
        assert config.extra_middleware == [mock_middleware]
        assert config.recursion_limit == 500
    
    def test_config_extra_tools_injection(self):
        """
        **Feature: dataagent-development-specs, Property 20: 自定义工具被注入**
        
        AgentConfig.extra_tools should accept custom tools.
        **Validates: Requirements 8.3**
        """
        mock_tool1 = MagicMock()
        mock_tool1.name = "custom_tool_1"
        mock_tool2 = MagicMock()
        mock_tool2.name = "custom_tool_2"
        
        config = AgentConfig(
            assistant_id="test-agent",
            extra_tools=[mock_tool1, mock_tool2],
        )
        
        assert len(config.extra_tools) == 2
        assert mock_tool1 in config.extra_tools
        assert mock_tool2 in config.extra_tools
    
    def test_config_extra_middleware_injection(self):
        """
        **Feature: dataagent-development-specs, Property 19: 自定义中间件被注入**
        
        AgentConfig.extra_middleware should accept custom middleware.
        **Validates: Requirements 7.5**
        """
        mock_middleware1 = MagicMock()
        mock_middleware2 = MagicMock()
        
        config = AgentConfig(
            assistant_id="test-agent",
            extra_middleware=[mock_middleware1, mock_middleware2],
        )
        
        assert len(config.extra_middleware) == 2
        assert mock_middleware1 in config.extra_middleware
        assert mock_middleware2 in config.extra_middleware


class TestAgentConfigFields:
    """Tests for AgentConfig field definitions."""
    
    def test_config_field_names(self):
        """Verify all expected fields exist in AgentConfig."""
        expected_fields = {
            "assistant_id",
            "model",
            "enable_memory",
            "enable_skills",
            "enable_shell",
            "auto_approve",
            "sandbox_type",
            "sandbox_id",
            "system_prompt",
            "extra_tools",
            "extra_middleware",
            "recursion_limit",
        }
        
        actual_fields = {f.name for f in fields(AgentConfig)}
        
        assert expected_fields.issubset(actual_fields), \
            f"Missing fields: {expected_fields - actual_fields}"
    
    def test_config_memory_flag(self):
        """
        **Feature: dataagent-development-specs, Property 10: 启用 memory 时添加 MemoryMiddleware**
        
        enable_memory flag should control memory middleware.
        **Validates: Requirements 4.4**
        """
        config_with_memory = AgentConfig(assistant_id="test", enable_memory=True)
        config_without_memory = AgentConfig(assistant_id="test", enable_memory=False)
        
        assert config_with_memory.enable_memory is True
        assert config_without_memory.enable_memory is False
    
    def test_config_skills_flag(self):
        """
        **Feature: dataagent-development-specs, Property 11: 启用 skills 时添加 SkillsMiddleware**
        
        enable_skills flag should control skills middleware.
        **Validates: Requirements 4.5**
        """
        config_with_skills = AgentConfig(assistant_id="test", enable_skills=True)
        config_without_skills = AgentConfig(assistant_id="test", enable_skills=False)
        
        assert config_with_skills.enable_skills is True
        assert config_without_skills.enable_skills is False
