"""Main entry point for DataAgent CLI."""

import argparse
import asyncio
import os
import sys
import warnings
from pathlib import Path

# Suppress transformers warning about PyTorch/TensorFlow
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
warnings.filterwarnings("ignore", message=".*PyTorch.*TensorFlow.*Flax.*")

from rich.console import Console

from dataagent_core.config import Settings, SessionState
from dataagent_core.engine import AgentFactory, AgentExecutor, AgentConfig
from dataagent_core.mcp import MCPConfigLoader

from dataagent_cli.colors import COLORS, DATAAGENT_ASCII
from dataagent_cli.renderer import TerminalRenderer
from dataagent_cli.hitl import TerminalHITLHandler
from dataagent_cli.input import create_prompt_session, parse_file_mentions
from dataagent_cli.commands import (
    handle_slash_command,
    show_help,
    list_agents,
    reset_agent,
    execute_bash_command,
)


console = Console(highlight=False, force_terminal=True)


class TokenTracker:
    """Track token usage across the conversation."""

    def __init__(self) -> None:
        self.baseline_context = 0
        self.current_context = 0
        self.last_output = 0

    def set_baseline(self, tokens: int) -> None:
        self.baseline_context = tokens
        self.current_context = tokens

    def reset(self) -> None:
        self.current_context = self.baseline_context
        self.last_output = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.current_context = input_tokens
        self.last_output = output_tokens

    def display_session(self) -> None:
        console.print("\n[bold]Token Usage:[/bold]", style=COLORS["primary"])
        if self.baseline_context > 0:
            console.print(
                f"  Baseline: {self.baseline_context:,} tokens [dim](system + agent.md)[/dim]",
                style=COLORS["dim"],
            )
        console.print(f"  Total: {self.current_context:,} tokens", style="bold " + COLORS["dim"])
        console.print()


async def main_loop(
    settings: Settings,
    config: AgentConfig,
    session_state: SessionState,
    mcp_loader: MCPConfigLoader | None = None,
) -> None:
    """Main interactive loop."""
    # Load MCP tools if configured
    if mcp_loader:
        try:
            mcp_tools = await mcp_loader.get_tools()
            if mcp_tools:
                config.extra_tools = list(config.extra_tools or []) + mcp_tools
                console.print(
                    f"[dim]Loaded {len(mcp_tools)} MCP tools[/dim]"
                )
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load MCP tools: {e}[/yellow]")
    
    # Create agent factory and agent
    factory = AgentFactory(settings)
    agent, backend = factory.create_agent(config)

    # Create HITL handler
    hitl_handler = None
    if not config.auto_approve:
        hitl_handler = TerminalHITLHandler(console, assistant_id=config.assistant_id)

    # Create executor and renderer
    executor = AgentExecutor(agent, backend, hitl_handler, config.assistant_id)
    renderer = TerminalRenderer(console)
    token_tracker = TokenTracker()

    # Create prompt session
    prompt_session = create_prompt_session(session_state)

    # Show welcome message
    if not getattr(session_state, "no_splash", False):
        console.print(DATAAGENT_ASCII, style=f"bold {COLORS['primary']}")
        console.print()

    console.print("Ready to work! What would you like to do?", style=COLORS["agent"])
    console.print()

    while True:
        try:
            user_input = await prompt_session.prompt_async()
            user_input = user_input.strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            result = handle_slash_command(
                user_input, console, session_state, token_tracker
            )
            if result == "exit":
                break
            continue

        # Bash commands
        if user_input.startswith("!"):
            execute_bash_command(user_input, console)
            continue

        # Exit commands
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        # Parse file mentions
        prompt_text, mentioned_files = parse_file_mentions(user_input, console)

        if mentioned_files:
            context_parts = [prompt_text, "\n\n## Referenced Files\n"]
            for file_path in mentioned_files:
                try:
                    content = file_path.read_text()
                    if len(content) > 50000:
                        content = content[:50000] + "\n... (file truncated)"
                    context_parts.append(
                        f"\n### {file_path.name}\nPath: `{file_path}`\n```\n{content}\n```"
                    )
                except Exception as e:
                    context_parts.append(f"\n### {file_path.name}\n[Error reading file: {e}]")
            final_input = "\n".join(context_parts)
        else:
            final_input = prompt_text

        # Execute task
        try:
            events = executor.execute(final_input, session_state.thread_id)
            await renderer.render_events(events)
        except asyncio.CancelledError:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            console.print("Ready for next command.\n", style="dim")
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            console.print("Ready for next command.\n", style="dim")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DataAgent CLI - AI-powered data assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["list", "reset", "help"],
        help="Command to run (list, reset, help)",
    )

    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier (default: agent)",
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting",
    )

    parser.add_argument(
        "--sandbox",
        choices=["modal", "runloop", "daytona", "none"],
        default="none",
        help="Remote sandbox for execution",
    )

    parser.add_argument(
        "--sandbox-id",
        help="Reuse existing sandbox",
    )

    parser.add_argument(
        "--target",
        help="Source agent for reset command",
    )

    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Don't show splash screen",
    )

    parser.add_argument(
        "--mcp-config",
        type=Path,
        help="Path to MCP configuration file (default: ~/.deepagents/{agent}/mcp.json)",
    )

    return parser.parse_args()


def cli_main() -> None:
    """CLI entry point."""
    args = parse_args()

    # Initialize settings
    settings = Settings.from_environment()

    # Handle commands
    if args.command == "help":
        show_help(console)
        return

    if args.command == "list":
        list_agents(console, settings)
        return

    if args.command == "reset":
        reset_agent(console, settings, args.agent, args.target)
        return

    # Check for API keys
    if not (settings.has_openai or settings.has_anthropic or settings.has_google):
        console.print("[bold red]Error:[/bold red] No API key configured.")
        console.print("\nPlease set one of the following environment variables:")
        console.print("  - OPENAI_API_KEY     (for OpenAI models)")
        console.print("  - ANTHROPIC_API_KEY  (for Claude models)")
        console.print("  - GOOGLE_API_KEY     (for Google Gemini models)")
        console.print("\nExample:")
        console.print("  export OPENAI_API_KEY=your_api_key_here")
        sys.exit(1)

    # Create session state
    session_state = SessionState(auto_approve=args.auto_approve)
    session_state.no_splash = args.no_splash

    # Create agent config
    config = AgentConfig(
        assistant_id=args.agent,
        auto_approve=args.auto_approve,
        sandbox_type=args.sandbox if args.sandbox != "none" else None,
        sandbox_id=args.sandbox_id,
    )

    # Create MCP loader
    mcp_loader = MCPConfigLoader(
        assistant_id=args.agent,
        config_path=args.mcp_config,
        project_root=settings.project_root,
    )

    # Run main loop
    try:
        asyncio.run(main_loop(settings, config, session_state, mcp_loader))
    except KeyboardInterrupt:
        console.print("\nGoodbye!", style=COLORS["primary"])


if __name__ == "__main__":
    cli_main()
