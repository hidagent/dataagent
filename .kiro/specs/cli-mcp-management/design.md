# Design Document: CLI MCP Management

## Overview

This design extends the DataAgent CLI to provide complete MCP server management capabilities through slash commands. The implementation leverages the existing `MCPConfigLoader` and `MCPConfig` classes from `dataagent-core`, adding new command handlers in the CLI module.

## Architecture

The CLI MCP management follows the existing command pattern in `commands.py`:

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Main Loop                          │
│                     (main.py)                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Command Handler                            │
│              handle_slash_command()                         │
│                  (commands.py)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                MCP Command Handler                          │
│              handle_mcp_command()                           │
│                  (commands.py)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┬───────────┬───────────┐
          ▼           ▼           ▼           ▼           ▼
     mcp_list    mcp_add    mcp_remove   mcp_test    mcp_help
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  MCPConfigLoader                            │
│              (dataagent_core.mcp)                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCPConfig                                │
│              (dataagent_core.mcp.config)                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### MCP Command Router

The main entry point for MCP commands, routing to specific handlers:

```python
def handle_mcp_command(
    command: str,
    console: Console,
    mcp_loader: MCPConfigLoader | None,
) -> str | None:
    """Route MCP subcommands to appropriate handlers."""
    parts = command.split()
    
    if len(parts) == 1 or parts[1] == "list":
        return mcp_list(console, mcp_loader)
    
    subcommand = parts[1]
    args = parts[2:] if len(parts) > 2 else []
    
    handlers = {
        "add": mcp_add,
        "remove": mcp_remove,
        "enable": mcp_enable,
        "disable": mcp_disable,
        "show": mcp_show,
        "test": mcp_test,
        "update": mcp_update,
        "reload": mcp_reload,
        "help": mcp_help,
    }
    
    handler = handlers.get(subcommand)
    if handler:
        return handler(console, mcp_loader, args)
    
    console.print(f"Unknown MCP command: {subcommand}", style="yellow")
    return None
```

### Command Handlers Interface

Each MCP command handler follows this signature:

```python
def mcp_<command>(
    console: Console,
    mcp_loader: MCPConfigLoader | None,
    args: list[str] = None,
) -> str | None:
    """Handle /mcp <command> [args].
    
    Args:
        console: Rich console for output
        mcp_loader: MCP configuration loader instance
        args: Command arguments
        
    Returns:
        None normally, "exit" to exit CLI
    """
```

### MCPConfigLoader Extensions

The existing `MCPConfigLoader` class needs minor extensions:

```python
class MCPConfigLoader:
    def save_config(self, config: MCPConfig) -> None:
        """Save configuration to the config file."""
        
    def add_server(self, server: MCPServerConfig) -> bool:
        """Add a server to configuration. Returns False if exists."""
        
    def remove_server(self, name: str) -> bool:
        """Remove a server from configuration. Returns False if not found."""
        
    def update_server(self, name: str, **kwargs) -> bool:
        """Update server configuration. Returns False if not found."""
        
    def get_server(self, name: str) -> MCPServerConfig | None:
        """Get a specific server configuration."""
```

## Data Models

### Command Argument Parsing

Arguments are parsed using a simple key-value pattern:

```python
@dataclass
class MCPAddArgs:
    name: str
    command: str | None = None
    url: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "sse"
    disabled: bool = False

def parse_mcp_add_args(args: list[str]) -> MCPAddArgs | None:
    """Parse /mcp add arguments.
    
    Examples:
        /mcp add myserver --command uvx --args mcp-server arg1 arg2
        /mcp add myserver --url https://example.com/mcp --transport sse
    """
```

### Configuration File Format

MCP configuration is stored in `~/.deepagents/{agent}/mcp.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx",
      "args": ["mcp-server-package"],
      "env": {"KEY": "value"},
      "disabled": false,
      "autoApprove": []
    },
    "http-server": {
      "url": "https://example.com/mcp",
      "transport": "sse",
      "headers": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Configuration Round-Trip

*For any* valid MCPConfig object, serializing to JSON and then deserializing SHALL produce an equivalent configuration object.

**Validates: Requirements 8.4**

### Property 2: Add Server Increases Count

*For any* valid MCPConfig and any new server name not already in the config, adding a server SHALL increase the server count by exactly one.

**Validates: Requirements 2.4**

### Property 3: Remove Server Decreases Count

*For any* MCPConfig containing at least one server, removing an existing server SHALL decrease the server count by exactly one.

**Validates: Requirements 3.3**

### Property 4: Enable/Disable Toggle

*For any* MCPConfig and any existing server, enabling then disabling (or vice versa) SHALL result in the server having the final state specified.

**Validates: Requirements 4.1, 4.2**

### Property 5: Server Name Uniqueness

*For any* MCPConfig, all server names SHALL be unique (no duplicates).

**Validates: Requirements 2.3**

### Property 6: Update Preserves Other Servers

*For any* MCPConfig with multiple servers, updating one server SHALL not modify any other server's configuration.

**Validates: Requirements 8.3**

## Error Handling

### Error Categories

1. **Configuration Errors**
   - Missing mcp.json file → Create new file
   - Invalid JSON format → Display parse error
   - Missing required fields → Display validation error

2. **Command Errors**
   - Missing required arguments → Display usage help
   - Invalid argument format → Display format error
   - Server not found → Display "server not found" message
   - Server already exists → Display "already exists" message

3. **Connection Errors**
   - Server disabled → Display warning
   - Connection timeout → Display timeout error
   - Connection refused → Display connection error

### Error Display Format

```python
def display_error(console: Console, message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")

def display_warning(console: Console, message: str) -> None:
    console.print(f"[yellow]Warning:[/yellow] {message}")

def display_success(console: Console, message: str) -> None:
    console.print(f"[green]✓[/green] {message}")
```

## Testing Strategy

### Unit Tests

Unit tests verify specific command behaviors:

- Test each command handler with valid inputs
- Test error handling for invalid inputs
- Test edge cases (empty config, missing file, etc.)

### Property-Based Tests

Property-based tests using `hypothesis` library:

1. **Round-trip test**: Generate random MCPConfig, serialize/deserialize, verify equality
2. **Add/remove test**: Generate random configs and operations, verify count invariants
3. **Update isolation test**: Generate configs with multiple servers, update one, verify others unchanged

### Test Configuration

```python
# pytest configuration for property tests
from hypothesis import settings, given
from hypothesis import strategies as st

@settings(max_examples=100)
@given(config=mcp_config_strategy())
def test_config_round_trip(config: MCPConfig):
    """Property 1: Round-trip serialization."""
    json_data = config.to_dict()
    restored = MCPConfig.from_dict(json_data)
    assert config == restored
```

### Test File Structure

```
dataagent/source/dataagent-cli/
├── dataagent_cli/
│   ├── commands.py          # MCP command handlers
│   └── ...
└── tests/
    ├── test_mcp_commands.py  # Unit tests
    └── test_mcp_properties.py # Property-based tests
```
