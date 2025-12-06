"""Input handling for DataAgent CLI."""

import asyncio
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import (
    Completer,
    Completion,
    PathCompleter,
    merge_completers,
)
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from dataagent_core.config import SessionState
from dataagent_cli.colors import COLORS, COMMANDS

AT_MENTION_RE = re.compile(r"@(?P<path>(?:[^\s@]|(?<=\\)\s)*)$")
SLASH_COMMAND_RE = re.compile(r"^/(?P<command>[a-z]*)$")
EXIT_CONFIRM_WINDOW = 3.0


class FilePathCompleter(Completer):
    """Activate filesystem completion only when cursor is after '@'."""

    def __init__(self) -> None:
        self.path_completer = PathCompleter(
            expanduser=True,
            min_input_len=0,
            only_directories=False,
        )

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        m = AT_MENTION_RE.search(text)
        if not m:
            return

        path_fragment = m.group("path")
        unescaped_fragment = path_fragment.replace("\\ ", " ")
        unescaped_fragment = unescaped_fragment.removesuffix("\\")
        temp_doc = Document(text=unescaped_fragment, cursor_position=len(unescaped_fragment))

        for comp in self.path_completer.get_completions(temp_doc, complete_event):
            completed_path = Path(unescaped_fragment + comp.text).expanduser()
            completion_text = comp.text.replace(" ", "\\ ")
            if completed_path.is_dir() and not completion_text.endswith("/"):
                completion_text += "/"

            yield Completion(
                text=completion_text,
                start_position=comp.start_position,
                display=comp.display,
                display_meta=comp.display_meta,
            )


class CommandCompleter(Completer):
    """Activate command completion only when line starts with '/'."""

    def get_completions(self, document, _complete_event):
        text = document.text_before_cursor
        m = SLASH_COMMAND_RE.match(text)
        if not m:
            return

        command_fragment = m.group("command")

        for cmd_name, cmd_desc in COMMANDS.items():
            if cmd_name.startswith(command_fragment.lower()):
                yield Completion(
                    text=cmd_name,
                    start_position=-len(command_fragment),
                    display=cmd_name,
                    display_meta=cmd_desc,
                )


def parse_file_mentions(text: str, console=None) -> tuple[str, list[Path]]:
    """Extract @file mentions and return cleaned text with resolved file paths."""
    pattern = r"@((?:[^\s@]|(?<=\\)\s)+)"
    matches = re.findall(pattern, text)

    files = []
    for match in matches:
        clean_path = match.replace("\\ ", " ")
        path = Path(clean_path).expanduser()

        if not path.is_absolute():
            path = Path.cwd() / path

        try:
            path = path.resolve()
            if path.exists() and path.is_file():
                files.append(path)
            elif console:
                console.print(f"[yellow]Warning: File not found: {match}[/yellow]")
        except Exception as e:
            if console:
                console.print(f"[yellow]Warning: Invalid path {match}: {e}[/yellow]")

    return text, files


def get_bottom_toolbar(
    session_state: SessionState, session_ref: dict
) -> Callable[[], list[tuple[str, str]]]:
    """Return toolbar function that shows auto-approve status."""

    def toolbar() -> list[tuple[str, str]]:
        parts = []

        try:
            session = session_ref.get("session")
            if session:
                current_text = session.default_buffer.text
                if current_text.startswith("!"):
                    parts.append(("bg:#ff1493 fg:#ffffff bold", " BASH MODE "))
                    parts.append(("", " | "))
        except (AttributeError, TypeError):
            pass

        if session_state.auto_approve:
            base_msg = "auto-accept ON (CTRL+T to toggle)"
            base_class = "class:toolbar-green"
        else:
            base_msg = "manual accept (CTRL+T to toggle)"
            base_class = "class:toolbar-orange"

        parts.append((base_class, base_msg))

        hint_until = getattr(session_state, "exit_hint_until", None)
        if hint_until is not None:
            now = time.monotonic()
            if now < hint_until:
                parts.append(("", " | "))
                parts.append(("class:toolbar-exit", " Ctrl+C again to exit "))
            else:
                session_state.exit_hint_until = None

        return parts

    return toolbar


def create_prompt_session(session_state: SessionState) -> PromptSession:
    """Create a configured PromptSession with all features."""
    if "EDITOR" not in os.environ:
        os.environ["EDITOR"] = "nano"

    kb = KeyBindings()

    @kb.add("c-c")
    def _(event) -> None:
        """Require double Ctrl+C within a short window to exit."""
        app = event.app
        now = time.monotonic()

        hint_until = getattr(session_state, "exit_hint_until", None)
        if hint_until is not None and now < hint_until:
            handle = getattr(session_state, "exit_hint_handle", None)
            if handle:
                handle.cancel()
                session_state.exit_hint_handle = None
            session_state.exit_hint_until = None
            app.invalidate()
            app.exit(exception=KeyboardInterrupt())
            return

        session_state.exit_hint_until = now + EXIT_CONFIRM_WINDOW

        handle = getattr(session_state, "exit_hint_handle", None)
        if handle:
            handle.cancel()

        loop = asyncio.get_running_loop()
        app_ref = app

        def clear_hint() -> None:
            hint_until = getattr(session_state, "exit_hint_until", None)
            if hint_until is not None and time.monotonic() >= hint_until:
                session_state.exit_hint_until = None
                session_state.exit_hint_handle = None
                app_ref.invalidate()

        session_state.exit_hint_handle = loop.call_later(EXIT_CONFIRM_WINDOW, clear_hint)
        app.invalidate()

    @kb.add("c-t")
    def _(event) -> None:
        """Toggle auto-approve mode."""
        session_state.toggle_auto_approve()
        event.app.invalidate()

    @kb.add("enter")
    def _(event) -> None:
        """Enter submits the input."""
        buffer = event.current_buffer

        if buffer.complete_state:
            current_completion = buffer.complete_state.current_completion
            if not current_completion and buffer.complete_state.completions:
                buffer.complete_next()
                buffer.apply_completion(buffer.complete_state.current_completion)
            elif current_completion:
                buffer.apply_completion(current_completion)
            else:
                buffer.complete_state = None
        elif buffer.text.strip():
            buffer.validate_and_handle()

    @kb.add("escape", "enter")
    def _(event) -> None:
        """Alt+Enter inserts a newline."""
        event.current_buffer.insert_text("\n")

    @kb.add("c-e")
    def _(event) -> None:
        """Open in external editor."""
        event.current_buffer.open_in_editor()

    @kb.add("backspace")
    def _(event) -> None:
        """Handle backspace and retrigger completion."""
        buffer = event.current_buffer
        buffer.delete_before_cursor(count=1)
        text = buffer.document.text_before_cursor
        if AT_MENTION_RE.search(text) or SLASH_COMMAND_RE.match(text):
            buffer.start_completion(select_first=False)

    toolbar_style = Style.from_dict(
        {
            "bottom-toolbar": "noreverse",
            "toolbar-green": "bg:#10b981 #000000",
            "toolbar-orange": "bg:#f59e0b #000000",
            "toolbar-exit": "bg:#2563eb #ffffff",
        }
    )

    session_ref = {}

    session = PromptSession(
        message=HTML(f'<style fg="{COLORS["user"]}">></style> '),
        multiline=True,
        key_bindings=kb,
        completer=merge_completers([CommandCompleter(), FilePathCompleter()]),
        editing_mode=EditingMode.EMACS,
        complete_while_typing=True,
        complete_in_thread=True,
        mouse_support=False,
        enable_open_in_editor=True,
        bottom_toolbar=get_bottom_toolbar(session_state, session_ref),
        style=toolbar_style,
        reserve_space_for_menu=7,
    )

    session_ref["session"] = session

    return session
