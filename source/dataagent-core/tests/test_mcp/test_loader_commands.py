"""Unit tests for MCPConfigLoader command methods.

Tests error handling and edge cases for the CLI MCP management feature.
"""

import json
import tempfile
from pathlib import Path

import pytest

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig
from dataagent_core.mcp.loader import MCPConfigLoader


class TestMCPConfigLoaderSave:
    """Tests for MCPConfigLoader save functionality."""

    def test_save_creates_file(self):
        """Test save_config creates file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            
            loader = MCPConfigLoader(config_path=config_path)
            config = MCPConfig()
            config.add_server(MCPServerConfig(name="test", command="uvx"))
            
            loader.save_config(config)
            
            assert config_path.exists()
            data = json.loads(config_path.read_text())
            assert "mcpServers" in data
            assert "test" in data["mcpServers"]

    def test_save_overwrites_existing(self):
        """Test save_config overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"old": {"command": "old"}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            config = MCPConfig()
            config.add_server(MCPServerConfig(name="new", command="new"))
            
            loader.save_config(config)
            
            data = json.loads(config_path.read_text())
            assert "new" in data["mcpServers"]
            assert "old" not in data["mcpServers"]


class TestMCPConfigLoaderAddServer:
    """Tests for MCPConfigLoader.add_server()."""

    def test_add_server_success(self):
        """Test adding a new server succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            server = MCPServerConfig(name="new", command="uvx", args=["test"])
            
            result = loader.add_server(server)
            
            assert result is True
            assert loader.get_server("new") is not None
            assert loader.get_server("new").command == "uvx"

    def test_add_server_duplicate_fails(self):
        """Test adding duplicate server name fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"existing": {"command": "uvx"}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            server = MCPServerConfig(name="existing", command="npx")
            
            result = loader.add_server(server)
            
            assert result is False
            # Original should be unchanged
            assert loader.get_server("existing").command == "uvx"

    def test_add_server_persists(self):
        """Test added server is persisted to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            server = MCPServerConfig(name="persistent", command="python")
            loader.add_server(server)
            
            # Create new loader to verify persistence
            loader2 = MCPConfigLoader(config_path=config_path)
            assert loader2.get_server("persistent") is not None


class TestMCPConfigLoaderRemoveServer:
    """Tests for MCPConfigLoader.remove_server()."""

    def test_remove_server_success(self):
        """Test removing existing server succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"target": {"command": "uvx"}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.remove_server("target")
            
            assert result is True
            assert loader.get_server("target") is None

    def test_remove_server_not_found(self):
        """Test removing non-existent server fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.remove_server("nonexistent")
            
            assert result is False

    def test_remove_server_persists(self):
        """Test removal is persisted to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"target": {"command": "uvx"}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            loader.remove_server("target")
            
            # Create new loader to verify persistence
            loader2 = MCPConfigLoader(config_path=config_path)
            assert loader2.get_server("target") is None


class TestMCPConfigLoaderUpdateServer:
    """Tests for MCPConfigLoader.update_server()."""

    def test_update_server_success(self):
        """Test updating existing server succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"target": {"command": "old"}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.update_server("target", command="new")
            
            assert result is True
            assert loader.get_server("target").command == "new"

    def test_update_server_not_found(self):
        """Test updating non-existent server fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.update_server("nonexistent", command="new")
            
            assert result is False

    def test_update_server_partial(self):
        """Test partial update only changes specified fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text(json.dumps({
                "mcpServers": {
                    "target": {
                        "command": "uvx",
                        "args": ["original"],
                        "disabled": False,
                    }
                }
            }))
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Only update command
            loader.update_server("target", command="npx")
            
            server = loader.get_server("target")
            assert server.command == "npx"
            assert server.args == ["original"]  # Unchanged
            assert server.disabled is False  # Unchanged


class TestMCPConfigLoaderGetServer:
    """Tests for MCPConfigLoader.get_server()."""

    def test_get_server_exists(self):
        """Test getting existing server returns config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"test": {"command": "uvx", "args": ["pkg"]}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            server = loader.get_server("test")
            
            assert server is not None
            assert server.name == "test"
            assert server.command == "uvx"
            assert server.args == ["pkg"]

    def test_get_server_not_found(self):
        """Test getting non-existent server returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            server = loader.get_server("nonexistent")
            
            assert server is None


class TestMCPConfigLoaderSetServerDisabled:
    """Tests for MCPConfigLoader.set_server_disabled()."""

    def test_enable_server(self):
        """Test enabling a disabled server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"test": {"command": "uvx", "disabled": true}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.set_server_disabled("test", False)
            
            assert result is True
            assert loader.get_server("test").disabled is False

    def test_disable_server(self):
        """Test disabling an enabled server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {"test": {"command": "uvx", "disabled": false}}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.set_server_disabled("test", True)
            
            assert result is True
            assert loader.get_server("test").disabled is True

    def test_set_disabled_not_found(self):
        """Test setting disabled on non-existent server fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.set_server_disabled("nonexistent", True)
            
            assert result is False


class TestMCPConfigLoaderGetOrCreateConfigPath:
    """Tests for MCPConfigLoader.get_or_create_config_path()."""

    def test_returns_existing_path(self):
        """Test returns existing config path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text('{"mcpServers": {}}')
            
            loader = MCPConfigLoader(config_path=config_path)
            
            result = loader.get_or_create_config_path()
            
            assert result == config_path

    def test_returns_user_path_when_no_config(self):
        """Test returns user config path when no config exists."""
        loader = MCPConfigLoader(assistant_id="test-agent")
        
        result = loader.get_or_create_config_path()
        
        expected = Path.home() / ".deepagents" / "test-agent" / "mcp.json"
        assert result == expected
