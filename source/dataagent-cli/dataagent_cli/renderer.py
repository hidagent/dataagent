"""Terminal renderer for DataAgent CLI."""

import re
import shutil
from pathlib import Path
from typing import AsyncIterator

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich import box
from rich.panel import Panel
from rich.text import Text

from dataagent_core.events import (
    ExecutionEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    TodoUpdateEvent,
    FileOperationEvent,
    ErrorEvent,
    DoneEvent,
)
from dataagent_cli.colors import COLORS, MAX_ARG_LENGTH


TOOL_ICONS = {
    "read_file": "📖",
    "write_file": "✏️",
    "edit_file": "✂️",
    "ls": "📁",
    "glob": "🔍",
    "grep": "🔎",
    "shell": "⚡",
    "execute": "🔧",
    "web_search": "🌐",
    "http_request": "🌍",
    "task": "🤖",
    "write_todos": "📋",
}


def truncate_value(value: str, max_length: int = MAX_ARG_LENGTH) -> str:
    """Truncate a string value if it exceeds max_length."""
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


def abbreviate_path(path_str: str, max_length: int = 60) -> str:
    """Abbreviate a file path intelligently."""
    try:
        path = Path(path_str)
        if len(path.parts) == 1:
            return path_str
        try:
            rel_path = path.relative_to(Path.cwd())
            rel_str = str(rel_path)
            if len(rel_str) < len(path_str) and len(rel_str) <= max_length:
                return rel_str
        except (ValueError, Exception):
            pass
        if len(path_str) <= max_length:
            return path_str
        return path.name
    except Exception:
        return truncate_value(path_str, max_length)


def format_tool_display(tool_name: str, tool_args: dict) -> str:
    """Format tool calls for display."""
    if tool_name in ("read_file", "write_file", "edit_file"):
        path_value = tool_args.get("file_path") or tool_args.get("path")
        if path_value is not None:
            path = abbreviate_path(str(path_value))
            return f"{tool_name}({path})"

    elif tool_name == "web_search":
        if "query" in tool_args:
            query = truncate_value(str(tool_args["query"]), 100)
            return f'{tool_name}("{query}")'

    elif tool_name == "grep":
        if "pattern" in tool_args:
            pattern = truncate_value(str(tool_args["pattern"]), 70)
            return f'{tool_name}("{pattern}")'

    elif tool_name == "shell":
        if "command" in tool_args:
            command = truncate_value(str(tool_args["command"]), 120)
            return f'{tool_name}("{command}")'

    elif tool_name == "ls":
        if tool_args.get("path"):
            path = abbreviate_path(str(tool_args["path"]))
            return f"{tool_name}({path})"
        return f"{tool_name}()"

    elif tool_name == "glob":
        if "pattern" in tool_args:
            pattern = truncate_value(str(tool_args["pattern"]), 80)
            return f'{tool_name}("{pattern}")'

    elif tool_name == "http_request":
        parts = []
        if "method" in tool_args:
            parts.append(str(tool_args["method"]).upper())
        if "url" in tool_args:
            url = truncate_value(str(tool_args["url"]), 80)
            parts.append(url)
        if parts:
            return f"{tool_name}({' '.join(parts)})"

    elif tool_name == "fetch_url":
        if "url" in tool_args:
            url = truncate_value(str(tool_args["url"]), 80)
            return f'{tool_name}("{url}")'

    elif tool_name == "task":
        if "description" in tool_args:
            desc = truncate_value(str(tool_args["description"]), 100)
            return f'{tool_name}("{desc}")'

    elif tool_name == "write_todos":
        if "todos" in tool_args and isinstance(tool_args["todos"], list):
            count = len(tool_args["todos"])
            return f"{tool_name}({count} items)"

    args_str = ", ".join(f"{k}={truncate_value(str(v), 50)}" for k, v in tool_args.items())
    return f"{tool_name}({args_str})"


def render_todo_list(console: Console, todos: list[dict]) -> None:
    """Render todo list as a rich Panel with checkboxes."""
    if not todos:
        return

    lines = []
    for todo in todos:
        status = todo.get("status", "pending")
        content = todo.get("content", "")

        if status == "completed":
            icon = "☑"
            style = "green"
        elif status == "in_progress":
            icon = "⏳"
            style = "yellow"
        else:
            icon = "☐"
            style = "dim"

        lines.append(f"[{style}]{icon} {content}[/{style}]")

    panel = Panel(
        "\n".join(lines),
        title="[bold]Task List[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def format_diff_rich(diff_lines: list[str]) -> str:
    """Format diff lines with line numbers and colors."""
    if not diff_lines:
        return "[dim]No changes detected[/dim]"

    term_width = shutil.get_terminal_size().columns

    max_line = max(
        (
            int(m.group(i))
            for line in diff_lines
            if (m := re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line))
            for i in (1, 2)
        ),
        default=0,
    )
    width = max(3, len(str(max_line)))

    formatted_lines = []
    old_num = new_num = 0

    addition_color = "white on dark_green"
    deletion_color = "white on dark_red"
    context_color = "dim"

    for line in diff_lines:
        if line.strip() == "...":
            formatted_lines.append(f"[{context_color}]...[/{context_color}]")
        elif line.startswith(("---", "+++")):
            continue
        elif m := re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line):
            old_num, new_num = int(m.group(1)), int(m.group(2))
        elif line.startswith("-"):
            code = escape(line[1:])
            formatted_lines.append(f"[dim]{old_num:>{width}}[/dim] [{deletion_color}]-  {code}[/{deletion_color}]")
            old_num += 1
        elif line.startswith("+"):
            code = escape(line[1:])
            formatted_lines.append(f"[dim]{new_num:>{width}}[/dim] [{addition_color}]+  {code}[/{addition_color}]")
            new_num += 1
        elif line.startswith(" "):
            code = escape(line[1:])
            formatted_lines.append(f"[dim]{old_num:>{width}}[/dim] [{context_color}]   {code}[/{context_color}]")
            old_num += 1
            new_num += 1

    return "\n".join(formatted_lines)


def render_diff_block(console: Console, diff: str, title: str) -> None:
    """Render a diff string with line numbers and colors."""
    try:
        diff_lines = diff.splitlines()
        formatted_diff = format_diff_rich(diff_lines)
        console.print()
        console.print(f"[bold {COLORS['primary']}]═══ {title} ═══[/bold {COLORS['primary']}]")
        console.print(formatted_diff)
        console.print()
    except (ValueError, AttributeError, IndexError, OSError):
        console.print()
        console.print(f"[bold {COLORS['primary']}]{title}[/bold {COLORS['primary']}]")
        console.print(diff)
        console.print()


def render_file_operation(console: Console, event: FileOperationEvent) -> None:
    """Render a file operation event."""
    label_lookup = {
        "read_file": "Read",
        "write_file": "Write",
        "edit_file": "Update",
    }
    label = label_lookup.get(event.operation, event.operation)
    header = Text()
    header.append("⏺ ", style=COLORS["tool"])
    header.append(f"{label}({event.file_path})", style=f"bold {COLORS['tool']}")
    console.print(header)

    def _print_detail(message: str, *, style: str = COLORS["dim"]) -> None:
        detail = Text()
        detail.append("  ⎿  ", style=style)
        detail.append(message, style=style)
        console.print(detail)

    if event.status == "error":
        _print_detail("Error executing file operation", style="red")
        return

    metrics = event.metrics
    if event.operation == "read_file":
        lines = metrics.get("lines_read", 0)
        _print_detail(f"Read {lines} line{'s' if lines != 1 else ''}")
    else:
        added = metrics.get("lines_added", 0)
        removed = metrics.get("lines_removed", 0)
        lines = metrics.get("lines_written", 0)
        if event.operation == "write_file":
            detail = f"Wrote {lines} line{'s' if lines != 1 else ''}"
        else:
            detail = f"Edited {lines} total line{'s' if lines != 1 else ''}"
        if added or removed:
            detail = f"{detail} (+{added} / -{removed})"
        _print_detail(detail)

    if event.diff:
        render_diff_block(console, event.diff, f"Diff {event.file_path}")


class TerminalRenderer:
    """Terminal event renderer."""

    def __init__(self, console: Console):
        self.console = console
        self._pending_text = ""
        self._has_responded = False
        self._spinner_active = False
        self._status = None

    async def render_events(self, events: AsyncIterator[ExecutionEvent]) -> None:
        """Render event stream to terminal."""
        self._start_spinner()

        try:
            async for event in events:
                await self._render_event(event)
        finally:
            self._stop_spinner()

    async def _render_event(self, event: ExecutionEvent) -> None:
        """Render a single event."""
        if isinstance(event, TextEvent):
            await self._render_text(event)
        elif isinstance(event, ToolCallEvent):
            await self._render_tool_call(event)
        elif isinstance(event, ToolResultEvent):
            await self._render_tool_result(event)
        elif isinstance(event, TodoUpdateEvent):
            await self._render_todo_update(event)
        elif isinstance(event, FileOperationEvent):
            await self._render_file_operation(event)
        elif isinstance(event, ErrorEvent):
            await self._render_error(event)
        elif isinstance(event, DoneEvent):
            await self._render_done(event)

    async def _render_text(self, event: TextEvent) -> None:
        """Render text event."""
        self._pending_text += event.content

        if event.is_final:
            self._flush_text()

    def _flush_text(self) -> None:
        """Flush accumulated text."""
        if not self._pending_text.strip():
            return

        self._stop_spinner()

        if not self._has_responded:
            self.console.print("●", style=COLORS["agent"], markup=False, end=" ")
            self._has_responded = True

        markdown = Markdown(self._pending_text.rstrip())
        self.console.print(markdown, style=COLORS["agent"])
        self._pending_text = ""

    async def _render_tool_call(self, event: ToolCallEvent) -> None:
        """Render tool call event."""
        self._flush_text()
        self._stop_spinner()

        if self._has_responded:
            self.console.print()

        icon = TOOL_ICONS.get(event.tool_name, "🔧")
        display_str = format_tool_display(event.tool_name, event.tool_args)
        self.console.print(f"  {icon} {display_str}", style=f"dim {COLORS['tool']}", markup=False)

        self._start_spinner(f"Executing {display_str}...")

    async def _render_tool_result(self, event: ToolResultEvent) -> None:
        """Render tool result event."""
        if event.status == "error":
            self._stop_spinner()
            result = str(event.result) if event.result else ""
            if result:
                self.console.print()
                self.console.print(result, style="red", markup=False)
                self.console.print()

        self._start_spinner("Agent is thinking...")

    async def _render_todo_update(self, event: TodoUpdateEvent) -> None:
        """Render todo update event."""
        self._stop_spinner()
        self.console.print()
        render_todo_list(self.console, event.todos)
        self.console.print()

    async def _render_file_operation(self, event: FileOperationEvent) -> None:
        """Render file operation event."""
        self._stop_spinner()
        self.console.print()
        render_file_operation(self.console, event)
        self.console.print()
        self._start_spinner("Agent is thinking...")

    async def _render_error(self, event: ErrorEvent) -> None:
        """Render error event."""
        self._stop_spinner()
        self.console.print(f"[red]Error: {event.error}[/red]")

    async def _render_done(self, event: DoneEvent) -> None:
        """Render done event."""
        self._stop_spinner()
        if self._has_responded:
            self.console.print()

    def _start_spinner(self, message: str = "Agent is thinking...") -> None:
        """Start spinner."""
        if not self._spinner_active:
            self._status = self.console.status(
                f"[bold {COLORS['thinking']}]{message}",
                spinner="dots",
            )
            self._status.start()
            self._spinner_active = True
        elif self._status:
            self._status.update(f"[bold {COLORS['thinking']}]{message}")

    def _stop_spinner(self) -> None:
        """Stop spinner."""
        if self._spinner_active and self._status:
            self._status.stop()
            self._spinner_active = False
