"""Slash commands for DataAgent CLI."""

import shutil
from pathlib import Path

from rich.console import Console

from dataagent_core.config import Settings
from dataagent_cli.colors import COLORS, COMMANDS, DATAAGENT_ASCII


def handle_slash_command(
    user_input: str,
    console: Console,
    session_state=None,
    token_tracker=None,
    mcp_loader=None,
) -> str | None:
    """Handle slash commands. Returns 'exit' to exit, None otherwise."""
    command = user_input.lower().strip()

    if command in ("/quit", "/exit"):
        return "exit"

    if command == "/clear":
        console.clear()
        if token_tracker:
            token_tracker.reset()
        if session_state:
            import uuid
            session_state.thread_id = str(uuid.uuid4())
        console.print("Screen cleared and conversation reset.", style=COLORS["dim"])
        console.print()
        return None

    if command == "/help":
        show_interactive_help(console)
        return None

    if command == "/tokens":
        if token_tracker:
            token_tracker.display_session()
        else:
            console.print("Token tracking not available.", style=COLORS["dim"])
        return None

    if command == "/mcp reload":
        if mcp_loader:
            import asyncio
            try:
                mcp_loader.reload_config()
                tools = asyncio.get_event_loop().run_until_complete(mcp_loader.get_tools())
                console.print(f"MCP config reloaded. {len(tools)} tools available.", style=COLORS["primary"])
            except Exception as e:
                console.print(f"[red]Failed to reload MCP config: {e}[/red]")
        else:
            console.print("MCP not configured.", style=COLORS["dim"])
        return None

    if command == "/mcp":
        if mcp_loader:
            config = mcp_loader.load_config()
            servers = config.get_enabled_servers()
            if servers:
                console.print("\n[bold]MCP Servers:[/bold]", style=COLORS["primary"])
                for name, server in servers.items():
                    console.print(f"  • {name}: {server.command} {' '.join(server.args)}", style=COLORS["dim"])
                console.print()
            else:
                console.print("No MCP servers configured.", style=COLORS["dim"])
        else:
            console.print("MCP not configured.", style=COLORS["dim"])
        return None

    console.print(f"Unknown command: {command}", style="yellow")
    console.print("Type /help for available commands.", style=COLORS["dim"])
    return None


def show_interactive_help(console: Console) -> None:
    """Show available commands during interactive session."""
    console.print()
    console.print("[bold]Interactive Commands:[/bold]", style=COLORS["primary"])
    console.print()

    for cmd, desc in COMMANDS.items():
        console.print(f"  /{cmd:<12} {desc}", style=COLORS["dim"])

    console.print()
    console.print("[bold]MCP Commands:[/bold]", style=COLORS["primary"])
    console.print("  /mcp            Show configured MCP servers", style=COLORS["dim"])
    console.print("  /mcp reload     Reload MCP configuration", style=COLORS["dim"])
    console.print()
    console.print("[bold]Editing Features:[/bold]", style=COLORS["primary"])
    console.print("  Enter           Submit your message", style=COLORS["dim"])
    console.print("  Alt+Enter       Insert newline (Option+Enter on Mac)", style=COLORS["dim"])
    console.print("  Ctrl+E          Open in external editor", style=COLORS["dim"])
    console.print("  Ctrl+T          Toggle auto-approve mode", style=COLORS["dim"])
    console.print("  Arrow keys      Navigate input", style=COLORS["dim"])
    console.print("  Ctrl+C          Cancel input or interrupt agent", style=COLORS["dim"])
    console.print()
    console.print("[bold]Special Features:[/bold]", style=COLORS["primary"])
    console.print("  @filename       Type @ to auto-complete files", style=COLORS["dim"])
    console.print("  /command        Type / to see available commands", style=COLORS["dim"])
    console.print("  !command        Type ! to run bash commands", style=COLORS["dim"])
    console.print()


def show_help(console: Console) -> None:
    """Show help information."""
    console.print()
    console.print(DATAAGENT_ASCII, style=f"bold {COLORS['primary']}")
    console.print()

    console.print("[bold]Usage:[/bold]", style=COLORS["primary"])
    console.print("  dataagent [OPTIONS]                           Start interactive session")
    console.print("  dataagent list                                List all available agents")
    console.print("  dataagent reset --agent AGENT                 Reset agent to default prompt")
    console.print("  dataagent reset --agent AGENT --target SOURCE Reset agent to copy of another agent")
    console.print("  dataagent help                                Show this help message")
    console.print()

    console.print("[bold]Options:[/bold]", style=COLORS["primary"])
    console.print("  --agent NAME                  Agent identifier (default: agent)")
    console.print("  --auto-approve                Auto-approve tool usage without prompting")
    console.print("  --sandbox TYPE                Remote sandbox for execution (modal, runloop, daytona)")
    console.print("  --sandbox-id ID               Reuse existing sandbox (skips creation/cleanup)")
    console.print("  --mcp-config PATH             Path to MCP configuration file")
    console.print()

    console.print("[bold]Examples:[/bold]", style=COLORS["primary"])
    console.print("  dataagent                              # Start with default agent", style=COLORS["dim"])
    console.print("  dataagent --agent mybot                # Start with agent named 'mybot'", style=COLORS["dim"])
    console.print("  dataagent --auto-approve               # Start with auto-approve enabled", style=COLORS["dim"])
    console.print("  dataagent --sandbox runloop            # Execute code in Runloop sandbox", style=COLORS["dim"])
    console.print("  dataagent --sandbox modal              # Execute code in Modal sandbox", style=COLORS["dim"])
    console.print("  dataagent --sandbox runloop --sandbox-id dbx_123  # Reuse existing sandbox", style=COLORS["dim"])
    console.print("  dataagent list                         # List all agents", style=COLORS["dim"])
    console.print("  dataagent reset --agent mybot          # Reset mybot to default", style=COLORS["dim"])
    console.print("  dataagent reset --agent mybot --target other # Reset mybot to copy of 'other' agent", style=COLORS["dim"])
    console.print()

    console.print("[bold]Long-term Memory:[/bold]", style=COLORS["primary"])
    console.print("  By default, long-term memory is ENABLED using agent name 'agent'.", style=COLORS["dim"])
    console.print("  Memory includes:", style=COLORS["dim"])
    console.print("  - Persistent agent.md file with your instructions", style=COLORS["dim"])
    console.print("  - /memories/ folder for storing context across sessions", style=COLORS["dim"])
    console.print()

    console.print("[bold]Agent Storage:[/bold]", style=COLORS["primary"])
    console.print("  Agents are stored in: ~/.deepagents/AGENT_NAME/", style=COLORS["dim"])
    console.print("  Each agent has an agent.md file containing its prompt", style=COLORS["dim"])
    console.print()

    console.print("[bold]MCP Configuration:[/bold]", style=COLORS["primary"])
    console.print("  MCP servers can be configured in: ~/.deepagents/{agent}/mcp.json", style=COLORS["dim"])
    console.print("  Or specify a custom path with --mcp-config", style=COLORS["dim"])
    console.print()

    console.print("[bold]Interactive Features:[/bold]", style=COLORS["primary"])
    console.print("  Enter           Submit your message", style=COLORS["dim"])
    console.print("  Alt+Enter       Insert newline for multi-line (Option+Enter or ESC then Enter)", style=COLORS["dim"])
    console.print("  Ctrl+J          Insert newline (alternative)", style=COLORS["dim"])
    console.print("  Ctrl+T          Toggle auto-approve mode", style=COLORS["dim"])
    console.print("  Arrow keys      Navigate input", style=COLORS["dim"])
    console.print("  @filename       Type @ to auto-complete files and inject content", style=COLORS["dim"])
    console.print("  /command        Type / to see available commands (auto-completes)", style=COLORS["dim"])
    console.print()

    console.print("[bold]Interactive Commands:[/bold]", style=COLORS["primary"])
    console.print("  /help           Show available commands and features", style=COLORS["dim"])
    console.print("  /clear          Clear screen and reset conversation", style=COLORS["dim"])
    console.print("  /tokens         Show token usage for current session", style=COLORS["dim"])
    console.print("  /mcp            Show configured MCP servers", style=COLORS["dim"])
    console.print("  /mcp reload     Reload MCP configuration", style=COLORS["dim"])
    console.print("  /quit, /exit    Exit the session", style=COLORS["dim"])
    console.print("  quit, exit, q   Exit the session (just type and press Enter)", style=COLORS["dim"])
    console.print()


def list_agents(console: Console, settings: Settings) -> None:
    """List all available agents."""
    agents_dir = settings.user_deepagents_dir

    if not agents_dir.exists() or not any(agents_dir.iterdir()):
        console.print("[yellow]No agents found.[/yellow]")
        console.print(
            "[dim]Agents will be created in ~/.deepagents/ when you first use them.[/dim]",
            style=COLORS["dim"],
        )
        return

    console.print("\n[bold]Available Agents:[/bold]\n", style=COLORS["primary"])

    for agent_path in sorted(agents_dir.iterdir()):
        if agent_path.is_dir():
            agent_name = agent_path.name
            agent_md = agent_path / "agent.md"

            if agent_md.exists():
                console.print(f"  • [bold]{agent_name}[/bold]", style=COLORS["primary"])
                console.print(f"    {agent_path}", style=COLORS["dim"])
            else:
                console.print(
                    f"  • [bold]{agent_name}[/bold] [dim](incomplete)[/dim]", style=COLORS["tool"]
                )
                console.print(f"    {agent_path}", style=COLORS["dim"])

    console.print()


def reset_agent(console: Console, settings: Settings, agent_name: str, source_agent: str | None = None) -> None:
    """Reset an agent to default or copy from another agent."""
    from dataagent_core.config import get_default_coding_instructions

    agents_dir = settings.user_deepagents_dir
    agent_dir = agents_dir / agent_name

    if source_agent:
        source_dir = agents_dir / source_agent
        source_md = source_dir / "agent.md"

        if not source_md.exists():
            console.print(
                f"[bold red]Error:[/bold red] Source agent '{source_agent}' not found "
                "or has no agent.md"
            )
            return

        source_content = source_md.read_text()
        action_desc = f"contents of agent '{source_agent}'"
    else:
        source_content = get_default_coding_instructions()
        action_desc = "default"

    if agent_dir.exists():
        shutil.rmtree(agent_dir)
        console.print(f"Removed existing agent directory: {agent_dir}", style=COLORS["tool"])

    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_md = agent_dir / "agent.md"
    agent_md.write_text(source_content)

    console.print(f"✓ Agent '{agent_name}' reset to {action_desc}", style=COLORS["primary"])
    console.print(f"Location: {agent_dir}\n", style=COLORS["dim"])


def execute_bash_command(user_input: str, console: Console) -> None:
    """Execute a bash command."""
    import subprocess

    command = user_input[1:].strip()
    if not command:
        console.print("Usage: !<command>", style=COLORS["dim"])
        return

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path.cwd(),
        )

        if result.stdout:
            console.print(result.stdout, markup=False)
        if result.stderr:
            console.print(result.stderr, style="red", markup=False)
        if result.returncode != 0:
            console.print(f"Exit code: {result.returncode}", style=COLORS["dim"])

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 60 seconds[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
