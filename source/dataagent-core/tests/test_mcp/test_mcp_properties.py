"""Property-based tests for MCP configuration management.

Feature: cli-mcp-management

These tests validate the correctness properties defined in the design document
for the CLI MCP management feature.
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st, assume

from dataagent_core.mcp.config import MCPServerConfig, MCPConfig
from dataagent_core.mcp.loader import MCPConfigLoader


# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for valid server names (non-empty, no special chars)
server_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=1,
    max_size=30,
).filter(lambda x: x.strip() and not x.startswith("-"))

# Strategy for commands
command_strategy = st.sampled_from(["uvx", "npx", "python", "node", "cargo"])

# Strategy for URLs
url_strategy = st.sampled_from([
    "https://api.example.com/mcp",
    "http://localhost:8080/mcp",
    "https://mcp.service.io/v1",
    None,
])

# Strategy for transport types
transport_strategy = st.sampled_from(["sse", "streamable_http"])

# Strategy for args lists
args_strategy = st.lists(
    st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
    min_size=0,
    max_size=5,
)

# Strategy for env dicts
env_strategy = st.dictionaries(
    keys=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=1, max_size=10),
    values=st.text(min_size=1, max_size=20),
    max_size=3,
)


@st.composite
def mcp_server_config_strategy(draw):
    """Generate random MCPServerConfig instances."""
    name = draw(server_name_strategy)
    url = draw(url_strategy)
    
    if url:
        # HTTP-based server
        return MCPServerConfig(
            name=name,
            url=url,
            transport=draw(transport_strategy),
            disabled=draw(st.booleans()),
            auto_approve=draw(st.lists(st.text(min_size=1, max_size=15), max_size=3)),
        )
    else:
        # Stdio-based server
        return MCPServerConfig(
            name=name,
            command=draw(command_strategy),
            args=draw(args_strategy),
            env=draw(env_strategy),
            disabled=draw(st.booleans()),
            auto_approve=draw(st.lists(st.text(min_size=1, max_size=15), max_size=3)),
        )


@st.composite
def mcp_config_strategy(draw, min_servers=0, max_servers=5):
    """Generate random MCPConfig instances."""
    num_servers = draw(st.integers(min_value=min_servers, max_value=max_servers))
    servers = {}
    
    for i in range(num_servers):
        server = draw(mcp_server_config_strategy())
        # Ensure unique names by appending index
        server.name = f"{server.name}_{i}"
        servers[server.name] = server
    
    return MCPConfig(servers=servers)


# =============================================================================
# Property 1: Configuration Round-Trip
# Feature: cli-mcp-management, Property 1: Configuration Round-Trip
# Validates: Requirements 8.4
# =============================================================================

class TestConfigurationRoundTrip:
    """Property 1: Configuration Round-Trip
    
    For any valid MCPConfig object, serializing to JSON and then deserializing
    SHALL produce an equivalent configuration object.
    """

    @given(config=mcp_config_strategy())
    @settings(max_examples=100)
    def test_config_round_trip(self, config: MCPConfig):
        """Property 1: Round-trip serialization preserves configuration."""
        # Serialize to dict (JSON format)
        json_data = config.to_dict()
        
        # Deserialize back
        restored = MCPConfig.from_dict(json_data)
        
        # Verify equivalence
        assert len(restored.servers) == len(config.servers)
        for name, server in config.servers.items():
            assert name in restored.servers
            restored_server = restored.servers[name]
            assert restored_server.name == server.name
            assert restored_server.command == server.command
            assert restored_server.url == server.url
            assert restored_server.args == server.args
            assert restored_server.disabled == server.disabled

    @given(config=mcp_config_strategy())
    @settings(max_examples=100)
    def test_config_file_round_trip(self, config: MCPConfig):
        """Property 1: Round-trip through JSON file preserves configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mcp.json"
            
            # Save to file
            config.to_json_file(path)
            
            # Load from file
            restored = MCPConfig.from_json_file(path)
            
            # Verify equivalence
            assert len(restored.servers) == len(config.servers)
            for name in config.servers:
                assert name in restored.servers


# =============================================================================
# Property 2: Add Server Increases Count
# Feature: cli-mcp-management, Property 2: Add Server Increases Count
# Validates: Requirements 2.4
# =============================================================================

class TestAddServerIncreasesCount:
    """Property 2: Add Server Increases Count
    
    For any valid MCPConfig and any new server name not already in the config,
    adding a server SHALL increase the server count by exactly one.
    """

    @given(
        config=mcp_config_strategy(max_servers=3),
        new_server=mcp_server_config_strategy(),
    )
    @settings(max_examples=100)
    def test_add_server_increases_count(self, config: MCPConfig, new_server: MCPServerConfig):
        """Property 2: Adding a new server increases count by 1."""
        # Ensure the new server name is unique
        new_server.name = f"new_unique_server_{len(config.servers)}"
        assume(new_server.name not in config.servers)
        
        initial_count = len(config.servers)
        
        # Add server
        config.add_server(new_server)
        
        # Verify count increased by 1
        assert len(config.servers) == initial_count + 1
        assert new_server.name in config.servers

    @given(config=mcp_config_strategy(max_servers=3))
    @settings(max_examples=100)
    def test_add_server_via_loader(self, config: MCPConfig):
        """Property 2: Adding via MCPConfigLoader increases count by 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            initial_count = len(loader.load_config().servers)
            
            # Create new server with unique name
            new_server = MCPServerConfig(
                name=f"loader_test_server_{initial_count}",
                command="uvx",
                args=["test"],
            )
            
            # Add via loader
            result = loader.add_server(new_server)
            
            # Verify
            assert result is True
            assert len(loader.load_config().servers) == initial_count + 1


# =============================================================================
# Property 3: Remove Server Decreases Count
# Feature: cli-mcp-management, Property 3: Remove Server Decreases Count
# Validates: Requirements 3.3
# =============================================================================

class TestRemoveServerDecreasesCount:
    """Property 3: Remove Server Decreases Count
    
    For any MCPConfig containing at least one server, removing an existing server
    SHALL decrease the server count by exactly one.
    """

    @given(config=mcp_config_strategy(min_servers=1, max_servers=5))
    @settings(max_examples=100)
    def test_remove_server_decreases_count(self, config: MCPConfig):
        """Property 3: Removing an existing server decreases count by 1."""
        assume(len(config.servers) > 0)
        
        initial_count = len(config.servers)
        server_to_remove = list(config.servers.keys())[0]
        
        # Remove server
        result = config.remove_server(server_to_remove)
        
        # Verify
        assert result is True
        assert len(config.servers) == initial_count - 1
        assert server_to_remove not in config.servers

    @given(config=mcp_config_strategy(min_servers=1, max_servers=5))
    @settings(max_examples=100)
    def test_remove_server_via_loader(self, config: MCPConfig):
        """Property 3: Removing via MCPConfigLoader decreases count by 1."""
        assume(len(config.servers) > 0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            initial_count = len(loader.load_config().servers)
            server_to_remove = list(loader.load_config().servers.keys())[0]
            
            # Remove via loader
            result = loader.remove_server(server_to_remove)
            
            # Verify
            assert result is True
            # Reload to verify persistence
            loader.reload_config()
            assert len(loader.load_config().servers) == initial_count - 1


# =============================================================================
# Property 4: Enable/Disable Toggle
# Feature: cli-mcp-management, Property 4: Enable/Disable Toggle
# Validates: Requirements 4.1, 4.2
# =============================================================================

class TestEnableDisableToggle:
    """Property 4: Enable/Disable Toggle
    
    For any MCPConfig and any existing server, enabling then disabling
    (or vice versa) SHALL result in the server having the final state specified.
    """

    @given(config=mcp_config_strategy(min_servers=1, max_servers=3))
    @settings(max_examples=100)
    def test_enable_sets_disabled_false(self, config: MCPConfig):
        """Property 4: Enabling a server sets disabled to False."""
        assume(len(config.servers) > 0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            
            # Start with disabled server
            server_name = list(config.servers.keys())[0]
            config.servers[server_name].disabled = True
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Enable
            result = loader.set_server_disabled(server_name, False)
            
            # Verify
            assert result is True
            server = loader.get_server(server_name)
            assert server.disabled is False

    @given(config=mcp_config_strategy(min_servers=1, max_servers=3))
    @settings(max_examples=100)
    def test_disable_sets_disabled_true(self, config: MCPConfig):
        """Property 4: Disabling a server sets disabled to True."""
        assume(len(config.servers) > 0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            
            # Start with enabled server
            server_name = list(config.servers.keys())[0]
            config.servers[server_name].disabled = False
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Disable
            result = loader.set_server_disabled(server_name, True)
            
            # Verify
            assert result is True
            server = loader.get_server(server_name)
            assert server.disabled is True

    @given(
        config=mcp_config_strategy(min_servers=1, max_servers=3),
        operations=st.lists(st.booleans(), min_size=1, max_size=10),
    )
    @settings(max_examples=100)
    def test_toggle_sequence_final_state(self, config: MCPConfig, operations: list[bool]):
        """Property 4: Final state matches last operation in sequence."""
        assume(len(config.servers) > 0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            server_name = list(config.servers.keys())[0]
            
            # Apply sequence of enable/disable operations
            for disabled in operations:
                loader.set_server_disabled(server_name, disabled)
            
            # Final state should match last operation
            expected_disabled = operations[-1]
            server = loader.get_server(server_name)
            assert server.disabled == expected_disabled


# =============================================================================
# Property 5: Server Name Uniqueness
# Feature: cli-mcp-management, Property 5: Server Name Uniqueness
# Validates: Requirements 2.3
# =============================================================================

class TestServerNameUniqueness:
    """Property 5: Server Name Uniqueness
    
    For any MCPConfig, all server names SHALL be unique (no duplicates).
    """

    @given(config=mcp_config_strategy(max_servers=5))
    @settings(max_examples=100)
    def test_no_duplicate_names(self, config: MCPConfig):
        """Property 5: All server names are unique."""
        names = list(config.servers.keys())
        assert len(names) == len(set(names))

    @given(config=mcp_config_strategy(min_servers=1, max_servers=3))
    @settings(max_examples=100)
    def test_add_duplicate_fails(self, config: MCPConfig):
        """Property 5: Adding duplicate name via loader fails."""
        assume(len(config.servers) > 0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            existing_name = list(config.servers.keys())[0]
            
            # Try to add server with existing name
            duplicate_server = MCPServerConfig(
                name=existing_name,
                command="uvx",
                args=["duplicate"],
            )
            
            result = loader.add_server(duplicate_server)
            
            # Should fail
            assert result is False
            # Count should not change
            assert len(loader.load_config().servers) == len(config.servers)


# =============================================================================
# Property 6: Update Preserves Other Servers
# Feature: cli-mcp-management, Property 6: Update Preserves Other Servers
# Validates: Requirements 8.3
# =============================================================================

class TestUpdatePreservesOtherServers:
    """Property 6: Update Preserves Other Servers
    
    For any MCPConfig with multiple servers, updating one server SHALL not
    modify any other server's configuration.
    """

    @given(config=mcp_config_strategy(min_servers=2, max_servers=5))
    @settings(max_examples=100)
    def test_update_does_not_affect_others(self, config: MCPConfig):
        """Property 6: Updating one server preserves others."""
        assume(len(config.servers) >= 2)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Get all server names
            server_names = list(config.servers.keys())
            target_name = server_names[0]
            other_names = server_names[1:]
            
            # Capture state of other servers before update
            other_servers_before = {
                name: loader.get_server(name).to_dict()
                for name in other_names
            }
            
            # Update target server
            loader.update_server(target_name, command="updated_command")
            
            # Verify other servers unchanged
            for name in other_names:
                server_after = loader.get_server(name).to_dict()
                assert server_after == other_servers_before[name]

    @given(config=mcp_config_strategy(min_servers=2, max_servers=5))
    @settings(max_examples=100)
    def test_remove_does_not_affect_others(self, config: MCPConfig):
        """Property 6: Removing one server preserves others."""
        assume(len(config.servers) >= 2)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config.to_json_file(config_path)
            
            loader = MCPConfigLoader(config_path=config_path)
            
            # Get all server names
            server_names = list(config.servers.keys())
            target_name = server_names[0]
            other_names = server_names[1:]
            
            # Capture state of other servers before removal
            other_servers_before = {
                name: loader.get_server(name).to_dict()
                for name in other_names
            }
            
            # Remove target server
            loader.remove_server(target_name)
            
            # Verify other servers unchanged
            for name in other_names:
                server_after = loader.get_server(name).to_dict()
                assert server_after == other_servers_before[name]
