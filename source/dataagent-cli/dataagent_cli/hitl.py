"""Terminal HITL handler for DataAgent CLI."""

import sys
import termios
import tty

from rich import box
from rich.console import Console
from rich.panel import Panel

from dataagent_core.hitl import HITLHandler, ActionRequest, Decision
from dataagent_core.tools.file_tracker import compute_unified_diff
from dataagent_cli.colors import COLORS
from dataagent_cli.renderer import render_diff_block


def build_approval_preview(name: str, args: dict, assistant_id: str | None) -> dict | None:
    """Build preview info for HITL approval."""
    from pathlib import Path
    from dataagent_core.tools.file_tracker import resolve_physical_path, format_display_path

    path_str = str(args.get("file_path") or args.get("path") or "")
    display_path = format_display_path(path_str)
    physical_path = resolve_physical_path(path_str, assistant_id)

    if name == "write_file":
        content = str(args.get("content", ""))
        before = ""
        if physical_path and physical_path.exists():
            try:
                before = physical_path.read_text()
            except:
                pass
        diff = compute_unified_diff(before, content, display_path, max_lines=100)
        lines = len(content.splitlines())
        return {
            "title": f"Write {display_path}",
            "details": [
                f"File: {path_str}",
                f"Action: {'Overwrite' if before else 'Create'} file",
                f"Lines to write: {lines}",
            ],
            "diff": diff,
            "diff_title": f"Diff {display_path}",
        }

    if name == "edit_file":
        if physical_path is None or not physical_path.exists():
            return {
                "title": f"Update {display_path}",
                "details": [f"File: {path_str}", "Action: Replace text"],
                "error": "Unable to resolve file path.",
            }
        try:
            before = physical_path.read_text()
        except:
            return {
                "title": f"Update {display_path}",
                "details": [f"File: {path_str}", "Action: Replace text"],
                "error": "Unable to read current file contents.",
            }

        old_string = str(args.get("old_string", ""))
        new_string = str(args.get("new_string", ""))
        replace_all = bool(args.get("replace_all", False))

        if old_string not in before:
            return {
                "title": f"Update {display_path}",
                "details": [f"File: {path_str}", "Action: Replace text"],
                "error": "Old string not found in file.",
            }

        if replace_all:
            after = before.replace(old_string, new_string)
            occurrences = before.count(old_string)
        else:
            after = before.replace(old_string, new_string, 1)
            occurrences = 1

        diff = compute_unified_diff(before, after, display_path, max_lines=None)
        additions = deletions = 0
        if diff:
            additions = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
            deletions = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))

        return {
            "title": f"Update {display_path}",
            "details": [
                f"File: {path_str}",
                f"Action: Replace text ({'all occurrences' if replace_all else 'single occurrence'})",
                f"Occurrences matched: {occurrences}",
                f"Lines changed: +{additions} / -{deletions}",
            ],
            "diff": diff,
            "diff_title": f"Diff {display_path}",
        }

    return None


class TerminalHITLHandler(HITLHandler):
    """Terminal HITL handler using arrow key navigation."""

    def __init__(self, console: Console, assistant_id: str | None = None):
        self.console = console
        self.assistant_id = assistant_id

    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """Request user approval for an action."""
        description = action_request.get("description", "No description available")
        name = action_request["name"]
        args = action_request["args"]

        preview = build_approval_preview(name, args, self.assistant_id)

        body_lines = []
        if preview:
            body_lines.append(f"[bold]{preview['title']}[/bold]")
            body_lines.extend(preview.get("details", []))
            if preview.get("error"):
                body_lines.append(f"[red]{preview['error']}[/red]")
        else:
            body_lines.append(description)

        self.console.print(
            Panel(
                "[bold yellow]⚠️  Tool Action Requires Approval[/bold yellow]\n\n"
                + "\n".join(body_lines),
                border_style="yellow",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

        if preview and preview.get("diff") and not preview.get("error"):
            self.console.print()
            render_diff_block(self.console, preview["diff"], preview.get("diff_title", "Diff"))

        selected = self._prompt_selection()

        if selected == 0:
            return {"type": "approve", "message": None}
        elif selected == 1:
            return {"type": "reject", "message": "User rejected the command"}
        else:
            return {"type": "auto_approve_all", "message": None}

    def _prompt_selection(self) -> int:
        """Prompt user to select an option."""
        options = ["approve", "reject", "auto-accept all going forward"]
        selected = 0

        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)
                sys.stdout.write("\033[?25l")  # Hide cursor
                sys.stdout.flush()

                first_render = True

                while True:
                    if not first_render:
                        sys.stdout.write("\033[3A\r")

                    first_render = False

                    for i, option in enumerate(options):
                        sys.stdout.write("\r\033[K")

                        if i == selected:
                            if option == "approve":
                                sys.stdout.write("\033[1;32m☑ Approve\033[0m\n")
                            elif option == "reject":
                                sys.stdout.write("\033[1;31m☑ Reject\033[0m\n")
                            else:
                                sys.stdout.write("\033[1;34m☑ Auto-accept all going forward\033[0m\n")
                        elif option == "approve":
                            sys.stdout.write("\033[2m☐ Approve\033[0m\n")
                        elif option == "reject":
                            sys.stdout.write("\033[2m☐ Reject\033[0m\n")
                        else:
                            sys.stdout.write("\033[2m☐ Auto-accept all going forward\033[0m\n")

                    sys.stdout.flush()

                    char = sys.stdin.read(1)

                    if char == "\x1b":
                        next1 = sys.stdin.read(1)
                        next2 = sys.stdin.read(1)
                        if next1 == "[":
                            if next2 == "B":
                                selected = (selected + 1) % len(options)
                            elif next2 == "A":
                                selected = (selected - 1) % len(options)
                    elif char in {"\r", "\n"}:
                        sys.stdout.write("\r\n")
                        break
                    elif char == "\x03":
                        sys.stdout.write("\r\n")
                        raise KeyboardInterrupt
                    elif char.lower() == "a":
                        selected = 0
                        sys.stdout.write("\r\n")
                        break
                    elif char.lower() == "r":
                        selected = 1
                        sys.stdout.write("\r\n")
                        break

            finally:
                sys.stdout.write("\033[?25h")  # Show cursor
                sys.stdout.flush()
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        except (termios.error, AttributeError):
            self.console.print("  ☐ (A)pprove  (default)")
            self.console.print("  ☐ (R)eject")
            self.console.print("  ☐ (Auto)-accept all going forward")
            choice = input("\nChoice (A/R/Auto, default=Approve): ").strip().lower()
            if choice in {"r", "reject"}:
                selected = 1
            elif choice in {"auto", "auto-accept"}:
                selected = 2
            else:
                selected = 0

        return selected
