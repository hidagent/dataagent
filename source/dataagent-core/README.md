# DataAgent Core

Core library for DataAgent platform - provides agent creation, execution, event system, and session management.

## Installation

```bash
pip install -e .

# With test dependencies
pip install -e ".[test]"

# With sandbox support
pip install -e ".[sandbox]"
```

## Quick Start

```python
from dataagent_core import (
    Settings,
    AgentFactory,
    AgentExecutor,
    AgentConfig,
    SessionManager,
)

# Initialize settings from environment
settings = Settings.from_environment()

# Create agent
factory = AgentFactory(settings)
config = AgentConfig(assistant_id="my-agent")
agent, backend = factory.create_agent(config)

# Create executor and run
executor = AgentExecutor(agent, backend, assistant_id="my-agent")

async for event in executor.execute("Hello, world!", session_id="session-1"):
    print(event.to_dict())
```

## Session Management

```python
from dataagent_core import SessionManager, AgentConfig

# Create session manager
manager = SessionManager(timeout_seconds=3600)
await manager.start()

# Get or create session
session = await manager.get_or_create_session(
    user_id="user-1",
    assistant_id="my-agent",
)

# Get executor for session
config = AgentConfig(assistant_id="my-agent")
executor = manager.get_executor(session, config)

# Execute with session
async for event in executor.execute("Hello!", session_id=session.session_id):
    print(event.to_dict())

# Cleanup
await manager.stop()
```

## Event Types

All events inherit from `ExecutionEvent` and can be serialized with `to_dict()`:

- `TextEvent` - Text output from the agent
- `ToolCallEvent` - Tool invocation
- `ToolResultEvent` - Tool execution result
- `HITLRequestEvent` - Human-in-the-loop approval request
- `TodoUpdateEvent` - Task list updates
- `FileOperationEvent` - File read/write/edit operations
- `ErrorEvent` - Error information
- `DoneEvent` - Execution completion

## Components

- `config/` - Settings and configuration management
- `engine/` - Agent factory and executor
- `events/` - Event system for streaming execution
- `middleware/` - Memory, skills, and shell middleware
- `tools/` - Web tools (search, fetch, http) and file tracker
- `hitl/` - Human-in-the-loop protocol
- `session/` - Session management and storage

## Environment Variables

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GOOGLE_API_KEY` - Google API key
- `TAVILY_API_KEY` - Tavily search API key

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=dataagent_core --cov-report=html
```

## License

MIT
