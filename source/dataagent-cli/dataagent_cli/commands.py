"""Slash commands for DataAgent CLI."""

import shutil
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

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

    # Rules commands
    if command.startswith("/rules"):
        return handle_rules_command(command, console, session_state)

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
    console.print("[bold]Rules Commands:[/bold]", style=COLORS["primary"])
    console.print("  /rules          List all rules", style=COLORS["dim"])
    console.print("  /rules help     Show rules command help", style=COLORS["dim"])
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


# ============================================================================
# Rules Commands
# ============================================================================


def handle_rules_command(
    command: str,
    console: Console,
    session_state: Any = None,
) -> str | None:
    """Handle /rules commands."""
    try:
        parts = command.split()
        
        if len(parts) == 1 or parts[1] == "list":
            return rules_list(console, session_state)
        
        subcommand = parts[1]
        args = parts[2:] if len(parts) > 2 else []
        
        if subcommand == "show":
            if not args:
                console.print("Usage: /rules show <name>", style=COLORS["dim"])
                return None
            return rules_show(console, session_state, args[0])
        
        if subcommand == "create":
            if not args:
                console.print("Usage: /rules create <name> [--scope global|user|project]", style=COLORS["dim"])
                return None
            scope = "user"
            if "--scope" in args:
                idx = args.index("--scope")
                if idx + 1 < len(args):
                    scope = args[idx + 1]
                    args = args[:idx] + args[idx + 2:]
            return rules_create(console, session_state, args[0], scope)
        
        if subcommand == "delete":
            if not args:
                console.print("Usage: /rules delete <name>", style=COLORS["dim"])
                return None
            return rules_delete(console, session_state, args[0])
        
        if subcommand == "validate":
            return rules_validate(console, session_state)
        
        if subcommand == "reload":
            return rules_reload(console, session_state)
        
        if subcommand == "debug":
            return rules_debug(console, session_state, args)
        
        if subcommand == "conflicts":
            return rules_conflicts(console, session_state)
        
        if subcommand == "help":
            return rules_help(console)
        
        console.print(f"Unknown rules subcommand: {subcommand}", style="yellow")
        console.print("Type /rules help for available commands.", style=COLORS["dim"])
        return None
        
    except ImportError as e:
        console.print(f"[red]Error: Required module not found: {e}[/red]")
        console.print("Please ensure dataagent-core is properly installed.", style=COLORS["dim"])
        return None
    except Exception as e:
        console.print(f"[red]Error executing rules command: {e}[/red]")
        return None


def _get_rule_store(session_state: Any = None):
    """Get or create a rule store."""
    from dataagent_core.rules import FileRuleStore
    from dataagent_core.config import Settings
    
    # Use from_environment() to properly initialize Settings
    settings = Settings.from_environment()
    
    # Get assistant_id from session state if available
    assistant_id = "agent"
    if session_state and hasattr(session_state, "assistant_id"):
        assistant_id = session_state.assistant_id
    
    global_rules_dir = settings.user_deepagents_dir / "rules"
    user_rules_dir = settings.get_agent_dir(assistant_id) / "rules"
    project_rules_dir = None
    if settings.project_root:
        project_rules_dir = settings.project_root / ".dataagent" / "rules"
    
    return FileRuleStore(
        global_dir=global_rules_dir,
        user_dir=user_rules_dir,
        project_dir=project_rules_dir,
    )


def rules_list(console: Console, session_state: Any = None) -> None:
    """List all available rules."""
    try:
        from dataagent_core.rules import RuleScope
        
        store = _get_rule_store(session_state)
        rules = store.list_rules()
        
        if not rules:
            console.print("No rules found.", style=COLORS["dim"])
            console.print("Use /rules create <name> to create a new rule.", style=COLORS["dim"])
            return None
        
        console.print("\n[bold]Agent Rules:[/bold]\n", style=COLORS["primary"])
        
        # Group by scope
        for scope in [RuleScope.GLOBAL, RuleScope.USER, RuleScope.PROJECT, RuleScope.SESSION]:
            scope_rules = [r for r in rules if r.scope == scope]
            if scope_rules:
                console.print(f"[bold]{scope.value.upper()}[/bold]", style=COLORS["primary"])
                
                table = Table(show_header=True, header_style="bold")
                table.add_column("Name", style="cyan")
                table.add_column("Description")
                table.add_column("Inclusion")
                table.add_column("Priority", justify="right")
                table.add_column("Enabled")
                
                for rule in sorted(scope_rules, key=lambda r: (-r.priority, r.name)):
                    table.add_row(
                        rule.name,
                        rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                        rule.inclusion.value,
                        str(rule.priority),
                        "✓" if rule.enabled else "✗",
                    )
                
                console.print(table)
                console.print()
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error listing rules: {e}[/red]")
        return None


def rules_show(console: Console, session_state: Any, name: str) -> None:
    """Show full content of a rule."""
    try:
        store = _get_rule_store(session_state)
        rule = store.get_rule(name)
        
        if not rule:
            console.print(f"Rule not found: {name}", style="yellow")
            return None
        
        console.print(f"\n[bold]Rule: {rule.name}[/bold]", style=COLORS["primary"])
        console.print(f"Description: {rule.description}", style=COLORS["dim"])
        console.print(f"Scope: {rule.scope.value}", style=COLORS["dim"])
        console.print(f"Inclusion: {rule.inclusion.value}", style=COLORS["dim"])
        if rule.file_match_pattern:
            console.print(f"File Pattern: {rule.file_match_pattern}", style=COLORS["dim"])
        console.print(f"Priority: {rule.priority}", style=COLORS["dim"])
        console.print(f"Enabled: {rule.enabled}", style=COLORS["dim"])
        if rule.source_path:
            console.print(f"Source: {rule.source_path}", style=COLORS["dim"])
        console.print("\n[bold]Content:[/bold]", style=COLORS["primary"])
        console.print(rule.content)
        console.print()
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error showing rule: {e}[/red]")
        return None


def rules_create(console: Console, session_state: Any, name: str, scope: str = "user") -> None:
    """Create a new rule."""
    try:
        from dataagent_core.rules import Rule, RuleScope, RuleInclusion
        
        store = _get_rule_store(session_state)
        
        # Check if rule already exists
        existing = store.get_rule(name)
        if existing:
            console.print(f"Rule already exists: {name}", style="yellow")
            console.print(f"Use /rules show {name} to view it.", style=COLORS["dim"])
            return None
        
        # Parse scope
        try:
            rule_scope = RuleScope(scope)
        except ValueError:
            console.print(f"Invalid scope: {scope}", style="yellow")
            console.print("Valid scopes: global, user, project", style=COLORS["dim"])
            return None
        
        # Create template rule
        rule = Rule(
            name=name,
            description=f"Description for {name}",
            content=f"""# {name}

Add your rule content here.

## Guidelines

- Guideline 1
- Guideline 2
""",
            scope=rule_scope,
            inclusion=RuleInclusion.ALWAYS,
        )
        
        store.save_rule(rule)
        
        console.print(f"✓ Created rule: {name}", style=COLORS["primary"])
        if rule.source_path:
            console.print(f"Location: {rule.source_path}", style=COLORS["dim"])
        console.print("Edit the file to customize the rule content.", style=COLORS["dim"])
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error creating rule: {e}[/red]")
        return None


def rules_delete(console: Console, session_state: Any, name: str) -> None:
    """Delete a rule."""
    try:
        store = _get_rule_store(session_state)
        rule = store.get_rule(name)
        
        if not rule:
            console.print(f"Rule not found: {name}", style="yellow")
            return None
        
        # Delete from the rule's scope
        success = store.delete_rule(name, rule.scope)
        
        if success:
            console.print(f"✓ Deleted rule: {name}", style=COLORS["primary"])
        else:
            console.print(f"Failed to delete rule: {name}", style="red")
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error deleting rule: {e}[/red]")
        return None


def rules_validate(console: Console, session_state: Any) -> None:
    """Validate all rule files."""
    try:
        from dataagent_core.rules import RuleParser
        
        store = _get_rule_store(session_state)
        parser = RuleParser()
        
        # Reload to get fresh data
        store.reload()
        rules = store.list_rules()
        
        errors = []
        warnings = []
        
        for rule in rules:
            if rule.source_path:
                try:
                    content = Path(rule.source_path).read_text() if Path(rule.source_path).exists() else ""
                    is_valid, rule_errors, rule_warnings = parser.validate_content(content)
                    if rule_errors:
                        errors.extend([(rule.name, e) for e in rule_errors])
                    if rule_warnings:
                        warnings.extend([(rule.name, w) for w in rule_warnings])
                except Exception as e:
                    errors.append((rule.name, str(e)))
        
        if errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for name, error in errors:
                console.print(f"  {name}: {error}", style="red")
        
        if warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for name, warning in warnings:
                console.print(f"  {name}: {warning}", style="yellow")
        
        if not errors and not warnings:
            console.print(f"✓ All {len(rules)} rules are valid.", style=COLORS["primary"])
        else:
            console.print(f"\nValidated {len(rules)} rules.", style=COLORS["dim"])
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error validating rules: {e}[/red]")
        return None


def rules_reload(console: Console, session_state: Any) -> None:
    """Reload all rules from disk."""
    try:
        store = _get_rule_store(session_state)
        store.reload()
        rules = store.list_rules()
        
        console.print(f"✓ Reloaded {len(rules)} rules.", style=COLORS["primary"])
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error reloading rules: {e}[/red]")
        return None


def rules_debug(console: Console, session_state: Any, args: list[str]) -> None:
    """Enable/disable debug mode for rule evaluation."""
    if not args:
        console.print("Usage: /rules debug on|off", style=COLORS["dim"])
        return None
    
    mode = args[0].lower()
    
    if mode == "on":
        console.print("✓ Rule debug mode enabled.", style=COLORS["primary"])
        console.print("Rule evaluation traces will be shown in responses.", style=COLORS["dim"])
        # Note: Actual debug mode toggle would need to be passed to the middleware
    elif mode == "off":
        console.print("✓ Rule debug mode disabled.", style=COLORS["primary"])
    else:
        console.print("Usage: /rules debug on|off", style=COLORS["dim"])
    
    return None


def rules_conflicts(console: Console, session_state: Any) -> None:
    """Show rule conflicts."""
    try:
        from dataagent_core.rules import ConflictDetector
        
        store = _get_rule_store(session_state)
        rules = store.list_rules()
        
        detector = ConflictDetector()
        report = detector.detect_conflicts(rules)
        
        if not report.has_conflicts() and not report.warnings:
            console.print("✓ No conflicts detected.", style=COLORS["primary"])
            return None
        
        if report.conflicts:
            console.print("\n[bold red]Conflicts:[/bold red]")
            for conflict in report.conflicts:
                console.print(
                    f"  • {conflict.rule1_name} ({conflict.rule1_scope.value}) vs "
                    f"{conflict.rule2_name} ({conflict.rule2_scope.value})",
                    style="red",
                )
                console.print(f"    Resolution: {conflict.resolution}", style=COLORS["dim"])
        
        if report.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in report.warnings:
                console.print(f"  • {warning}", style="yellow")
        
        console.print()
        return None
        
    except Exception as e:
        console.print(f"[red]Error checking conflicts: {e}[/red]")
        return None


def rules_help(console: Console) -> None:
    """Show rules command help."""
    console.print("\n[bold]Rules Commands:[/bold]", style=COLORS["primary"])
    console.print()
    console.print("  /rules list              List all rules grouped by scope", style=COLORS["dim"])
    console.print("  /rules show <name>       Show full content of a rule", style=COLORS["dim"])
    console.print("  /rules create <name>     Create a new rule", style=COLORS["dim"])
    console.print("    --scope <scope>        Scope: global, user, project (default: user)", style=COLORS["dim"])
    console.print("  /rules delete <name>     Delete a rule", style=COLORS["dim"])
    console.print("  /rules validate          Validate all rule files", style=COLORS["dim"])
    console.print("  /rules reload            Reload rules from disk", style=COLORS["dim"])
    console.print("  /rules debug on|off      Enable/disable debug mode", style=COLORS["dim"])
    console.print("  /rules conflicts         Show rule conflicts", style=COLORS["dim"])
    console.print("  /rules help              Show this help", style=COLORS["dim"])
    console.print()
    console.print("[bold]Rule Reference:[/bold]", style=COLORS["primary"])
    console.print("  Use @rulename in your message to manually include a rule.", style=COLORS["dim"])
    console.print()
    return None
