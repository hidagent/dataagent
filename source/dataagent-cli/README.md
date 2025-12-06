# DataAgent CLI

Command-line interface for DataAgent platform.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Start interactive session
dataagent

# Start with specific agent
dataagent --agent mybot

# Start with auto-approve mode
dataagent --auto-approve

# List all agents
dataagent list

# Reset an agent
dataagent reset --agent mybot
```

## Features

- Interactive chat with AI agent
- File operations with diff preview
- Shell command execution
- Web search and URL fetching
- Skills system for specialized workflows
- Human-in-the-loop approval for destructive operations
- Auto-approve mode for automated workflows
