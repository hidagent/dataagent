"""Terminal UI - colors, console, rendering."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import box

COLORS = {
    "primary": "#10b981",
    "dim": "#6b7280",
    "user": "#ffffff",
    "agent": "#10b981",
    "thinking": "#34d399",
    "tool": "#fbbf24",
}

BANNER = """
 ██████╗   █████╗  ████████╗  █████╗
 ██╔══██╗ ██╔══██╗ ╚══██╔══╝ ██╔══██╗
 ██║  ██║ ███████║    ██║    ███████║
 ██║  ██║ ██╔══██║    ██║    ██╔══██║
 ██████╔╝ ██║  ██║    ██║    ██║  ██║
 ╚═════╝  ╚═╝  ╚═╝    ╚═╝    ╚═╝  ╚═╝
    █████╗   ██████╗  ███████╗ ███╗   ██╗ ████████╗
   ██╔══██╗ ██╔════╝  ██╔════╝ ████╗  ██║ ╚══██╔══╝
   ███████║ ██║  ███╗ █████╗   ██╔██╗ ██║    ██║
   ██╔══██║ ██║   ██║ ██╔══╝   ██║╚██╗██║    ██║
   ██║  ██║ ╚██████╔╝ ███████╗ ██║ ╚████║    ██║
   ╚═╝  ╚═╝  ╚═════╝  ╚══════╝ ╚═╝  ╚═══╝    ╚═╝
"""

console = Console(highlight=False)

TOOL_ICONS = {
    "read_file": "📖", "write_file": "✏️", "edit_file": "✂️",
    "ls": "📁", "glob": "🔍", "grep": "🔎", "shell": "⚡",
    "execute": "🔧", "web_search": "🌐", "http_request": "🌍",
    "task": "🤖", "write_todos": "📋",
}


def render_todo_list(todos: list[dict]) -> None:
    """Render todo list as a panel."""
    if not todos:
        return
    lines = []
    for todo in todos:
        status = todo.get("status", "pending")
        content = todo.get("content", "")
        if status == "completed":
            lines.append(f"[green]☑ {content}[/green]")
        elif status == "in_progress":
            lines.append(f"[yellow]⏳ {content}[/yellow]")
        else:
            lines.append(f"[dim]☐ {content}[/dim]")
    console.print(Panel("\n".join(lines), title="[bold]Task List[/bold]", border_style="cyan", box=box.ROUNDED))
