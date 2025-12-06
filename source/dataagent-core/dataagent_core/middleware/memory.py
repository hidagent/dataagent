"""Agent memory middleware for loading long-term memory into system prompt."""

import contextlib
from collections.abc import Awaitable, Callable
from typing import NotRequired, TypedDict, cast

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime

from dataagent_core.config import Settings


class AgentMemoryState(AgentState):
    """State for the agent memory middleware."""
    user_memory: NotRequired[str]
    project_memory: NotRequired[str]


class AgentMemoryStateUpdate(TypedDict):
    """State update for the agent memory middleware."""
    user_memory: NotRequired[str]
    project_memory: NotRequired[str]


LONGTERM_MEMORY_SYSTEM_PROMPT = """

## Long-term Memory

Your long-term memory is stored in files on the filesystem and persists across sessions.

**User Memory Location**: `{agent_dir_absolute}` (displays as `{agent_dir_display}`)
**Project Memory Location**: {project_memory_info}

Your system prompt is loaded from TWO sources at startup:
1. **User agent.md**: `{agent_dir_absolute}/agent.md` - Your personal preferences across all projects
2. **Project agent.md**: Loaded from project root if available - Project-specific instructions

**When to CHECK/READ memories (CRITICAL - do this FIRST):**
- **At the start of ANY new session**: Check both user and project memories
- **BEFORE answering questions**: If asked "what do you know about X?" or "how do I do Y?", check project memories FIRST
- **When user asks you to do something**: Check if you have project-specific guides or examples

**When to update memories:**
- **IMMEDIATELY when the user describes your role or how you should behave**
- **IMMEDIATELY when the user gives feedback on your work**
- When the user explicitly asks you to remember something
- When patterns or preferences emerge

## File Operations:

**User memory:**
```
ls {agent_dir_absolute}
read_file '{agent_dir_absolute}/agent.md'
edit_file '{agent_dir_absolute}/agent.md' ...
```

**Project memory:**
```
ls {project_deepagents_dir}
read_file '{project_deepagents_dir}/agent.md'
edit_file '{project_deepagents_dir}/agent.md' ...
```
"""


DEFAULT_MEMORY_SNIPPET = """<user_memory>
{user_memory}
</user_memory>

<project_memory>
{project_memory}
</project_memory>"""


class AgentMemoryMiddleware(AgentMiddleware):
    """Middleware for loading agent-specific long-term memory.
    
    Supports user isolation in multi-tenant mode by including user_id
    in the memory storage path.
    """

    state_schema = AgentMemoryState

    def __init__(
        self,
        *,
        settings: Settings,
        assistant_id: str,
        user_id: str | None = None,
        system_prompt_template: str | None = None,
    ) -> None:
        """Initialize memory middleware.
        
        Args:
            settings: Core settings instance.
            assistant_id: The assistant identifier.
            user_id: Optional user ID for multi-tenant isolation.
                     If provided, memory is stored in user-specific path.
            system_prompt_template: Custom template for memory section.
        """
        self.settings = settings
        self.assistant_id = assistant_id
        self.user_id = user_id
        
        # Build agent directory path with optional user isolation
        if user_id:
            # Multi-tenant mode: ~/.deepagents/users/{user_id}/{assistant_id}
            self.agent_dir = settings.user_deepagents_dir / "users" / user_id / assistant_id
            self.agent_dir_display = f"~/.deepagents/users/{user_id}/{assistant_id}"
        else:
            # Single-tenant mode: ~/.deepagents/{assistant_id}
            self.agent_dir = settings.get_agent_dir(assistant_id)
            self.agent_dir_display = f"~/.deepagents/{assistant_id}"
        
        self.agent_dir_absolute = str(self.agent_dir)
        self.project_root = settings.project_root
        self.system_prompt_template = system_prompt_template or DEFAULT_MEMORY_SNIPPET

    def get_user_memory_path(self) -> "Path":
        """Get the path to user memory file.
        
        Returns:
            Path to user's agent.md file.
        """
        from pathlib import Path
        return self.agent_dir / "agent.md"
    
    def ensure_memory_dir(self) -> None:
        """Ensure the memory directory exists."""
        self.agent_dir.mkdir(parents=True, exist_ok=True)
    
    def clear_memory(self) -> bool:
        """Clear user memory.
        
        Returns:
            True if memory was cleared, False if not found.
        """
        import shutil
        if self.agent_dir.exists():
            shutil.rmtree(self.agent_dir)
            return True
        return False

    def before_agent(
        self,
        state: AgentMemoryState,
        runtime: Runtime,
    ) -> AgentMemoryStateUpdate:
        """Load agent memory from file before agent execution."""
        result: AgentMemoryStateUpdate = {}

        if "user_memory" not in state:
            # Use the user-isolated path
            user_path = self.get_user_memory_path()
            if user_path.exists():
                with contextlib.suppress(OSError, UnicodeDecodeError):
                    result["user_memory"] = user_path.read_text()

        if "project_memory" not in state:
            project_path = self.settings.get_project_agent_md_path()
            if project_path and project_path.exists():
                with contextlib.suppress(OSError, UnicodeDecodeError):
                    result["project_memory"] = project_path.read_text()

        return result

    def _build_system_prompt(self, request: ModelRequest) -> str:
        """Build the complete system prompt with memory sections."""
        state = cast("AgentMemoryState", request.state)
        user_memory = state.get("user_memory")
        project_memory = state.get("project_memory")
        base_system_prompt = request.system_prompt

        if self.project_root and project_memory:
            project_memory_info = f"`{self.project_root}` (detected)"
        elif self.project_root:
            project_memory_info = f"`{self.project_root}` (no agent.md found)"
        else:
            project_memory_info = "None (not in a git project)"

        if self.project_root:
            project_deepagents_dir = str(self.project_root / ".deepagents")
        else:
            project_deepagents_dir = "[project-root]/.deepagents (not in a project)"

        memory_section = self.system_prompt_template.format(
            user_memory=user_memory if user_memory else "(No user agent.md)",
            project_memory=project_memory if project_memory else "(No project agent.md)",
        )

        system_prompt = memory_section

        if base_system_prompt:
            system_prompt += "\n\n" + base_system_prompt

        system_prompt += "\n\n" + LONGTERM_MEMORY_SYSTEM_PROMPT.format(
            agent_dir_absolute=self.agent_dir_absolute,
            agent_dir_display=self.agent_dir_display,
            project_memory_info=project_memory_info,
            project_deepagents_dir=project_deepagents_dir,
        )

        return system_prompt

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        system_prompt = self._build_system_prompt(request)
        return handler(request.override(system_prompt=system_prompt))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        system_prompt = self._build_system_prompt(request)
        return await handler(request.override(system_prompt=system_prompt))
