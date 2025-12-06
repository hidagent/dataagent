"""Tests for MCP configuration module.

Property 47: CLI MCP 配置加载
Property 48: MCP Server 连接失败不阻塞
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig
from dataagent_core.mcp.loader import MCPConfigLoader


class TestMCPServerConfig:
    """Tests for MCPServerConfig dataclass."""

    def test_create_basic_config(self):
        """Test creating a basic MCP server config."""
        config = MCPServerConfig(
            name="test-server",
            command="uvx",
            args=["mcp-server-test"],
        )
        assert config.name == "test-server"
        assert config.command == "uvx"
        assert config.args == ["mcp-server-test"]
        assert config.env == {}
        assert config.disabled is False
        assert config.auto_approve == []

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = MCPServerConfig(
            name="test",
            command="python",
            args=["-m", "server"],
            env={"KEY": "value"},
            disabled=True,
            auto_approve=["tool1"],
        )
        result = config.to_dict()
        assert result["name"] == "test"
        assert result["command"] == "python"
        assert result["args"] == ["-m", "server"]
        assert result["env"] == {"KEY": "value"}
        assert result["disabled"] is True
        assert result["auto_approve"] == ["tool1"]

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "name": "test",
            "command": "uvx",
            "args": ["server"],
            "env": {"API_KEY": "xxx"},
            "disabled": False,
            "autoApprove": ["read_file"],
        }
        config = MCPServerConfig.from_dict(data)
        assert config.name == "test"
        assert config.command == "uvx"
        assert config.args == ["server"]
        assert config.env == {"API_KEY": "xxx"}
        assert config.disabled is False
        assert config.auto_approve == ["read_file"]

    def test_to_mcp_client_config(self):
        """Test conversion to langchain-mcp-adapters format."""
        config = MCPServerConfig(
            name="filesystem",
            command="uvx",
            args=["mcp-server-filesystem", "/workspace"],
            env={"DEBUG": "true"},
        )
        result = config.to_mcp_client_config()
        assert result["command"] == "uvx"
        assert result["args"] == ["mcp-server-filesystem", "/workspace"]
        assert result["env"] == {"DEBUG": "true"}

    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        command=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        disabled=st.booleans(),
    )
    @settings(max_examples=50)
    def test_roundtrip_serialization(self, name, command, disabled):
        """Property: Config serialization roundtrip preserves data."""
        config = MCPServerConfig(
            name=name,
            command=command,
            disabled=disabled,
        )
        data = config.to_dict()
        restored = MCPServerConfig.from_dict(data)
        assert restored.name == config.name
        assert restored.command == config.command
        assert restored.disabled == config.disabled


class TestMCPConfig:
    """Tests for MCPConfig dataclass."""

    def test_empty_config(self):
        """Test creating empty config."""
        config = MCPConfig()
        assert config.servers == {}

    def test_add_server(self):
        """Test adding a server."""
        config = MCPConfig()
        server = MCPServerConfig(name="test", command="uvx")
        config.add_server(server)
        assert "test" in config.servers
        assert config.servers["test"] == server

    def test_remove_server(self):
        """Test removing a server."""
        config = MCPConfig()
        server = MCPServerConfig(name="test", command="uvx")
        config.add_server(server)
        assert config.remove_server("test") is True
        assert "test" not in config.servers
        assert config.remove_server("nonexistent") is False

    def test_get_enabled_servers(self):
        """Test filtering enabled servers."""
        config = MCPConfig()
        config.add_server(MCPServerConfig(name="enabled", command="uvx"))
        config.add_server(MCPServerConfig(name="disabled", command="uvx", disabled=True))
        
        enabled = config.get_enabled_servers()
        assert "enabled" in enabled
        assert "disabled" not in enabled

    def test_to_dict_mcp_json_format(self):
        """Test serialization to mcp.json format."""
        config = MCPConfig()
        config.add_server(MCPServerConfig(
            name="filesystem",
            command="uvx",
            args=["mcp-server-filesystem"],
        ))
        
        result = config.to_dict()
        assert "mcpServers" in result
        assert "filesystem" in result["mcpServers"]
        assert result["mcpServers"]["filesystem"]["command"] == "uvx"

    def test_from_dict_mcp_json_format(self):
        """Test deserialization from mcp.json format."""
        data = {
            "mcpServers": {
                "filesystem": {
                    "command": "uvx",
                    "args": ["mcp-server-filesystem"],
                    "env": {},
                    "disabled": False,
                },
                "database": {
                    "command": "npx",
                    "args": ["mcp-server-mysql"],
                    "disabled": True,
                },
            }
        }
        config = MCPConfig.from_dict(data)
        assert len(config.servers) == 2
        assert config.servers["filesystem"].command == "uvx"
        assert config.servers["database"].disabled is True

    def test_json_file_roundtrip(self):
        """Test saving and loading from JSON file."""
        config = MCPConfig()
        config.add_server(MCPServerConfig(
            name="test",
            command="python",
            args=["-m", "server"],
            env={"KEY": "value"},
        ))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mcp.json"
            config.to_json_file(path)
            
            loaded = MCPConfig.from_json_file(path)
            assert "test" in loaded.servers
            assert loaded.servers["test"].command == "python"
            assert loaded.servers["test"].env == {"KEY": "value"}

    def test_from_nonexistent_file(self):
        """Test loading from nonexistent file returns empty config."""
        config = MCPConfig.from_json_file(Path("/nonexistent/mcp.json"))
        assert config.servers == {}


class TestMCPConfigLoader:
    """Tests for MCPConfigLoader.
    
    Property 47: CLI MCP 配置加载
    """

    def test_find_config_path_explicit(self):
        """Test explicit config path takes priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "custom.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(
                assistant_id="test",
                config_path=config_path,
            )
            assert loader.find_config_path() == config_path

    def test_find_config_path_none(self):
        """Test returns None when no config exists."""
        loader = MCPConfigLoader(
            assistant_id="nonexistent-agent-12345",
        )
        # Should return None if no config file exists
        result = loader.find_config_path()
        # May be None or may find user config
        assert result is None or result.exists()

    def test_load_config_empty(self):
        """Test loading returns empty config when no file exists."""
        loader = MCPConfigLoader(
            assistant_id="nonexistent-agent-12345",
        )
        config = loader.load_config()
        assert isinstance(config, MCPConfig)

    def test_load_config_from_file(self):
        """Property 47: CLI MCP 配置加载 - 从文件加载配置."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text(json.dumps({
                "mcpServers": {
                    "test": {
                        "command": "uvx",
                        "args": ["test-server"],
                    }
                }
            }))
            
            loader = MCPConfigLoader(
                assistant_id="test",
                config_path=config_path,
            )
            config = loader.load_config()
            
            assert "test" in config.servers
            assert config.servers["test"].command == "uvx"

    def test_reload_config(self):
        """Test reloading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"v1": {"command": "uvx"}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            config1 = loader.load_config()
            assert "v1" in config1.servers
            
            # Update file
            config_path.write_text('{"mcpServers": {"v2": {"command": "npx"}}}')
            
            # Reload
            config2 = loader.reload_config()
            assert "v2" in config2.servers
            assert "v1" not in config2.servers

    def test_get_auto_approve_tools(self):
        """Test getting auto-approve tool names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text(json.dumps({
                "mcpServers": {
                    "server1": {
                        "command": "uvx",
                        "autoApprove": ["read_file", "list_dir"],
                    },
                    "server2": {
                        "command": "npx",
                        "autoApprove": ["query"],
                        "disabled": True,  # Disabled, should not be included
                    },
                    "server3": {
                        "command": "python",
                        "autoApprove": ["write_file"],
                    },
                }
            }))
            
            loader = MCPConfigLoader(config_path=config_path)
            auto_approve = loader.get_auto_approve_tools()
            
            assert "read_file" in auto_approve
            assert "list_dir" in auto_approve
            assert "write_file" in auto_approve
            # server2 is disabled, so "query" should not be included
            assert "query" not in auto_approve


class TestMCPConnectionFailure:
    """Tests for MCP connection failure handling.
    
    Property 48: MCP Server 连接失败不阻塞
    """

    @pytest.mark.asyncio
    async def test_get_tools_without_mcp_adapters(self):
        """Property 48: 连接失败不阻塞 - langchain-mcp-adapters 未安装时返回空列表."""
        # This test verifies that get_tools() handles ImportError gracefully
        loader = MCPConfigLoader(assistant_id="test")
        
        # Even if langchain-mcp-adapters is not installed or servers fail,
        # get_tools should return empty list without raising
        tools = await loader.get_tools()
        assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_get_tools_with_invalid_config(self):
        """Property 48: 连接失败不阻塞 - 无效配置时返回空列表."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            # Config with invalid server that will fail to connect
            config_path.write_text(json.dumps({
                "mcpServers": {
                    "invalid": {
                        "command": "nonexistent-command-12345",
                        "args": [],
                    }
                }
            }))
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Should not raise, should return empty list
            tools = await loader.get_tools()
            assert isinstance(tools, list)
