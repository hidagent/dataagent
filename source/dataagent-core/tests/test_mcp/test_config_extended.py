"""Extended tests for MCP configuration module.

Tests for new features: transport, headers, URL-based servers.
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig


class TestMCPServerConfigTransport:
    """Tests for MCPServerConfig transport and headers support."""

    def test_default_transport_is_sse(self):
        """Test default transport is 'sse'."""
        config = MCPServerConfig(name="test", url="http://localhost:8080/mcp")
        assert config.transport == "sse"

    def test_streamable_http_transport(self):
        """Test streamable_http transport."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
        )
        assert config.transport == "streamable_http"

    def test_headers_support(self):
        """Test custom headers support."""
        headers = {
            "X-API-Key": "secret-key",
            "X-Custom-Header": "value",
        }
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            headers=headers,
        )
        assert config.headers == headers

    def test_to_mcp_client_config_with_sse(self):
        """Test conversion to MCP client config with SSE transport."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            transport="sse",
        )
        result = config.to_mcp_client_config()
        assert result["url"] == "http://localhost:8080/mcp"
        assert result["transport"] == "sse"
        assert "headers" not in result

    def test_to_mcp_client_config_with_streamable_http(self):
        """Test conversion to MCP client config with streamable_http transport."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
        )
        result = config.to_mcp_client_config()
        assert result["url"] == "http://localhost:8080/mcp"
        assert result["transport"] == "streamable_http"

    def test_to_mcp_client_config_with_headers(self):
        """Test conversion to MCP client config with headers."""
        headers = {"X-API-Key": "secret"}
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            headers=headers,
        )
        result = config.to_mcp_client_config()
        assert result["headers"] == headers

    def test_to_mcp_client_config_full(self):
        """Test full conversion with all URL options."""
        config = MCPServerConfig(
            name="test",
            url="http://10.21.19.93:9042/mcp",
            transport="streamable_http",
            headers={
                "X-User-Token": "token123",
                "X-Database-Host": "db.example.com",
            },
        )
        result = config.to_mcp_client_config()
        assert result == {
            "url": "http://10.21.19.93:9042/mcp",
            "transport": "streamable_http",
            "headers": {
                "X-User-Token": "token123",
                "X-Database-Host": "db.example.com",
            },
        }

    def test_to_mcp_client_config_stdio(self):
        """Test conversion for stdio transport (command-based)."""
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
        assert "url" not in result
        assert "transport" not in result

    def test_from_dict_with_transport(self):
        """Test deserialization with transport field."""
        data = {
            "name": "test",
            "url": "http://localhost:8080/mcp",
            "transport": "streamable_http",
        }
        config = MCPServerConfig.from_dict(data)
        assert config.transport == "streamable_http"

    def test_from_dict_with_headers(self):
        """Test deserialization with headers field."""
        data = {
            "name": "test",
            "url": "http://localhost:8080/mcp",
            "headers": {"X-API-Key": "secret"},
        }
        config = MCPServerConfig.from_dict(data)
        assert config.headers == {"X-API-Key": "secret"}

    def test_from_dict_default_transport(self):
        """Test default transport when not specified."""
        data = {
            "name": "test",
            "url": "http://localhost:8080/mcp",
        }
        config = MCPServerConfig.from_dict(data)
        assert config.transport == "sse"

    def test_to_dict_includes_all_fields(self):
        """Test serialization includes all fields."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
            headers={"X-Key": "value"},
            disabled=True,
        )
        result = config.to_dict()
        assert result["url"] == "http://localhost:8080/mcp"
        assert result["transport"] == "streamable_http"
        assert result["headers"] == {"X-Key": "value"}
        assert result["disabled"] is True

    @given(
        transport=st.sampled_from(["sse", "streamable_http"]),
        header_key=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() and x.isalnum()),
        header_value=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=30)
    def test_roundtrip_with_transport_and_headers(self, transport, header_key, header_value):
        """Property: Config with transport and headers roundtrips correctly."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            transport=transport,
            headers={header_key: header_value},
        )
        data = config.to_dict()
        restored = MCPServerConfig.from_dict(data)
        assert restored.transport == config.transport
        assert restored.headers == config.headers


class TestMCPConfigURLServers:
    """Tests for MCPConfig with URL-based servers."""

    def test_json_file_with_url_server(self):
        """Test saving and loading URL-based server config."""
        config = MCPConfig()
        config.add_server(MCPServerConfig(
            name="remote-mcp",
            url="http://10.21.19.93:9042/mcp",
            transport="streamable_http",
            headers={
                "X-User-Token": "token123",
                "X-Database": "mydb",
            },
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mcp.json"
            config.to_json_file(path)

            # Verify JSON content
            with open(path) as f:
                data = json.load(f)
            assert "mcpServers" in data
            assert "remote-mcp" in data["mcpServers"]

            # Load and verify
            loaded = MCPConfig.from_json_file(path)
            server = loaded.servers["remote-mcp"]
            assert server.url == "http://10.21.19.93:9042/mcp"

    def test_mixed_servers(self):
        """Test config with both command and URL-based servers."""
        config = MCPConfig()
        config.add_server(MCPServerConfig(
            name="local",
            command="uvx",
            args=["mcp-server-filesystem"],
        ))
        config.add_server(MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
            transport="streamable_http",
        ))

        assert len(config.servers) == 2
        assert config.servers["local"].command == "uvx"
        assert config.servers["remote"].url == "http://localhost:8080/mcp"

    def test_to_mcp_client_config_mixed(self):
        """Test conversion with mixed server types."""
        config = MCPConfig()
        config.add_server(MCPServerConfig(
            name="local",
            command="uvx",
            args=["server"],
        ))
        config.add_server(MCPServerConfig(
            name="remote",
            url="http://localhost:8080/mcp",
            transport="sse",
        ))

        result = config.to_mcp_client_config()
        assert result["local"]["command"] == "uvx"
        assert result["remote"]["url"] == "http://localhost:8080/mcp"
        assert result["remote"]["transport"] == "sse"


class TestMCPServerConfigValidation:
    """Tests for MCPServerConfig validation scenarios."""

    def test_empty_headers(self):
        """Test empty headers dict."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            headers={},
        )
        result = config.to_mcp_client_config()
        assert "headers" not in result  # Empty headers should not be included

    def test_url_without_transport(self):
        """Test URL server without explicit transport uses default."""
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
        )
        result = config.to_mcp_client_config()
        assert result["transport"] == "sse"

    def test_command_server_ignores_url_fields(self):
        """Test command-based server ignores URL-related fields."""
        config = MCPServerConfig(
            name="test",
            command="uvx",
            args=["server"],
            url=None,  # No URL
            transport="streamable_http",  # Should be ignored
            headers={"X-Key": "value"},  # Should be ignored
        )
        result = config.to_mcp_client_config()
        assert "url" not in result
        assert "transport" not in result
        assert "headers" not in result
        assert result["command"] == "uvx"

    def test_special_characters_in_headers(self):
        """Test headers with special characters."""
        headers = {
            "X-API-Key": "abc123!@#$%",
            "Authorization": "Bearer token.with.dots",
        }
        config = MCPServerConfig(
            name="test",
            url="http://localhost:8080/mcp",
            headers=headers,
        )
        assert config.headers == headers
        result = config.to_mcp_client_config()
        assert result["headers"] == headers
