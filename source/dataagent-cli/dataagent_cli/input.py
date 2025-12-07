"""Input handling for DataAgent CLI."""

import asyncio
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.buffer import Buffer
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
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.styles import Style

from dataagent_core.config import SessionState
from dataagent_cli.colors import COLORS, COMMANDS

AT_MENTION_RE = re.compile(r"@(?P<path>(?:[^\s@]|(?<=\\)\s)*)$")
SLASH_COMMAND_RE = re.compile(r"^/(?P<command>[a-z]*)$")
EXIT_CONFIRM_WINDOW = 3.0

# Threshold for folding pasted text
PASTE_FOLD_THRESHOLD = 3  # Fold if more than 3 lines


class PastedTextManager:
    """Manage pasted text blocks with folding support."""

    def __init__(self) -> None:
        self.paste_counter = 0
        self.pasted_blocks: dict[int, str] = {}  # id -> original text
        self.expanded_blocks: set[int] = set()  # ids of expanded blocks

    def add_paste(self, text: str) -> tuple[int, str]:
        """Add a pasted text block and return (id, placeholder)."""
        self.paste_counter += 1
        paste_id = self.paste_counter
        self.pasted_blocks[paste_id] = text

        lines = text.split("\n")
        line_count = len(lines)
        extra_lines = line_count - 1

        # Create placeholder: [Pasted text #1 +208 lines]
        placeholder = f"[Pasted text #{paste_id} +{extra_lines} lines]"
        return paste_id, placeholder

    def get_original(self, paste_id: int) -> str | None:
        """Get original text for a paste id."""
        return self.pasted_blocks.get(paste_id)

    def toggle_expand(self, paste_id: int) -> None:
        """Toggle expansion state of a paste block."""
        if paste_id in self.expanded_blocks:
            self.expanded_blocks.discard(paste_id)
        else:
            self.expanded_blocks.add(paste_id)

    def is_expanded(self, paste_id: int) -> bool:
        """Check if a paste block is expanded."""
        return paste_id in self.expanded_blocks

    def expand_text(self, text: str) -> str:
        """Expand all paste placeholders in text to original content."""
        result = text
        pattern = r"\[Pasted text #(\d+) \+\d+ lines\]"

        for match in re.finditer(pattern, text):
            paste_id = int(match.group(1))
            original = self.get_original(paste_id)
            if original:
                result = result.replace(match.group(0), original)

        return result

    def clear(self) -> None:
        """Clear all paste data for new session."""
        self.pasted_blocks.clear()
        self.expanded_blocks.clear()


class PasteProcessor(Processor):
    """Processor to display pasted text with folding."""

    def __init__(self, paste_manager: PastedTextManager) -> None:
        self.paste_manager = paste_manager

    def apply_transformation(
        self, transformation_input: Any
    ) -> Transformation:
        """Apply visual transformation for paste placeholders."""
        # Just pass through - the actual folding is done at paste time
        return Transformation(transformation_input.fragments)


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
    session_state: SessionState, session_ref: dict[str, Any]
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
                # Check for paste placeholders
                elif "[Pasted text #" in current_text:
                    parts.append(("fg:#888888 italic", " (ctrl+o to expand) "))
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


class FoldingPromptSession:
    """Wrapper around PromptSession that handles paste folding."""

    def __init__(
        self,
        session: PromptSession,
        paste_manager: PastedTextManager,
    ) -> None:
        self.session = session
        self.paste_manager = paste_manager

    async def prompt_async(self) -> str:
        """Prompt for input and expand any folded paste blocks before returning."""
        result = await self.session.prompt_async()
        # Expand all paste placeholders to original content
        return self.paste_manager.expand_text(result)


def create_prompt_session(session_state: SessionState) -> FoldingPromptSession:
    """Create a configured PromptSession with all features including paste folding."""
    if "EDITOR" not in os.environ:
        os.environ["EDITOR"] = "nano"

    # Create paste manager for this session
    paste_manager = PastedTextManager()

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

    @kb.add("c-o")
    def _(event) -> None:
        """Toggle expand/collapse of pasted text under cursor."""
        buffer = event.current_buffer
        text = buffer.text
        cursor_pos = buffer.cursor_position

        # Find paste placeholder at or near cursor
        pattern = r"\[Pasted text #(\d+) \+\d+ lines\]"
        for match in re.finditer(pattern, text):
            start, end = match.span()
            if start <= cursor_pos <= end:
                paste_id = int(match.group(1))
                original = paste_manager.get_original(paste_id)
                if original:
                    # Replace placeholder with original text
                    new_text = text[:start] + original + text[end:]
                    buffer.text = new_text
                    buffer.cursor_position = start + len(original)
                    event.app.invalidate()
                return

    @kb.add("backspace")
    def _(event) -> None:
        """Handle backspace and retrigger completion."""
        buffer = event.current_buffer
        buffer.delete_before_cursor(count=1)
        text = buffer.document.text_before_cursor
        if AT_MENTION_RE.search(text) or SLASH_COMMAND_RE.match(text):
            buffer.start_completion(select_first=False)

    # Custom paste handler using bracketed paste
    @kb.add("c-v")
    def handle_paste(event) -> None:
        """Handle Ctrl+V paste with folding for multiline content."""
        app = event.app
        buffer = event.current_buffer

        # Get clipboard content
        try:
            data = app.clipboard.get_data()
            if data and data.text:
                pasted_text = data.text
                lines = pasted_text.split("\n")

                # If multiline and exceeds threshold, fold it
                if len(lines) > PASTE_FOLD_THRESHOLD:
                    paste_id, placeholder = paste_manager.add_paste(pasted_text)
                    buffer.insert_text(placeholder)
                else:
                    buffer.insert_text(pasted_text)
            else:
                # Fallback to default paste
                buffer.paste_clipboard_data(data)
        except Exception:
            # Fallback: just insert normally
            pass

    def on_text_insert(buffer: Buffer, text: str) -> str:
        """Handle text insertion, folding multiline pastes.
        
        This is called for bracketed paste (terminal paste) which is the
        most common way to paste in terminals.
        """
        lines = text.split("\n")
        if len(lines) > PASTE_FOLD_THRESHOLD:
            # This looks like a paste operation, fold it
            paste_id, placeholder = paste_manager.add_paste(text)
            return placeholder
        return text

    toolbar_style = Style.from_dict(
        {
            "bottom-toolbar": "noreverse",
            "toolbar-green": "bg:#10b981 #000000",
            "toolbar-orange": "bg:#f59e0b #000000",
            "toolbar-exit": "bg:#2563eb #ffffff",
            "paste-placeholder": "fg:#888888 italic",
        }
    )

    session_ref: dict[str, Any] = {}

    # Use "prompt" color which works on both light and dark backgrounds
    prompt_color = COLORS.get("prompt", COLORS["primary"])

    # Create buffer with custom on_text_insert handler
    from prompt_toolkit.filters import Always
    buffer = Buffer(
        on_text_insert=on_text_insert,
        multiline=Always(),
    )

    session = PromptSession(
        message=HTML(f'<style fg="{prompt_color}" bold="true">❯</style> '),
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
        enable_system_prompt=False,
    )

    # Replace the default buffer with our custom one
    session.default_buffer = buffer

    session_ref["session"] = session

    return FoldingPromptSession(session, paste_manager)
