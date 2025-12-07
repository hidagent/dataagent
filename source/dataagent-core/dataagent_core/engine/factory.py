"""Agent factory for creating configured agents."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.sandbox import SandboxBackendProtocol
from langchain.agents.middleware import InterruptOnConfig
from langchain.agents.middleware.types import AgentState, AgentMiddleware
from langchain.messages import ToolCall
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.pregel import Pregel
from langgraph.runtime import Runtime

from dataagent_core.config import Settings, get_default_coding_instructions
from dataagent_core.middleware import AgentMemoryMiddleware, SkillsMiddleware, ShellMiddleware, RulesMiddleware
from dataagent_core.tools import http_request, fetch_url, web_search


@dataclass
class AgentConfig:
    """Configuration for creating an agent."""
    assistant_id: str
    model: str | BaseChatModel | None = None
    enable_memory: bool = True
    enable_skills: bool = True
    enable_shell: bool = True
    enable_rules: bool = True  # Enable agent rules
    rules_debug_mode: bool = False  # Enable rules debug mode
    auto_approve: bool = False
    sandbox_type: str | None = None
    sandbox_id: str | None = None
    system_prompt: str | None = None
    user_context: dict[str, Any] | None = None  # User context for personalization
    extra_tools: list[BaseTool] = field(default_factory=list)
    extra_middleware: list[AgentMiddleware] = field(default_factory=list)
    recursion_limit: int = 1000


def _format_shell_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    command = args.get("command", "N/A")
    return f"Shell Command: {command}\nWorking Directory: {Path.cwd()}"


def _format_execute_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    command = args.get("command", "N/A")
    return f"Execute Command: {command}\nLocation: Remote Sandbox"


def _format_write_file_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    file_path = args.get("file_path", "unknown")
    content = args.get("content", "")
    action = "Overwrite" if Path(file_path).exists() else "Create"
    line_count = len(content.splitlines())
    return f"File: {file_path}\nAction: {action} file\nLines: {line_count}"


def _format_edit_file_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    file_path = args.get("file_path", "unknown")
    replace_all = bool(args.get("replace_all", False))
    return f"File: {file_path}\nAction: Replace text ({'all occurrences' if replace_all else 'single occurrence'})"


def _format_web_search_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    query = args.get("query", "unknown")
    max_results = args.get("max_results", 5)
    return f"Query: {query}\nMax results: {max_results}\n\n⚠️  This will use Tavily API credits"


def _format_fetch_url_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    url = args.get("url", "unknown")
    timeout = args.get("timeout", 30)
    return f"URL: {url}\nTimeout: {timeout}s\n\n⚠️  Will fetch and convert web content to markdown"


def _format_task_description(tool_call: ToolCall, _state: AgentState, _runtime: Runtime) -> str:
    args = tool_call["args"]
    description = args.get("description", "unknown")
    subagent_type = args.get("subagent_type", "unknown")
    description_preview = description[:500] + "..." if len(description) > 500 else description
    return (
        f"Subagent Type: {subagent_type}\n\n"
        f"Task Instructions:\n{'─' * 40}\n{description_preview}\n{'─' * 40}\n\n"
        f"⚠️  Subagent will have access to file operations and shell commands"
    )


def _build_interrupt_config() -> dict[str, InterruptOnConfig]:
    """Build HITL interrupt configuration."""
    return {
        "shell": {"allowed_decisions": ["approve", "reject"], "description": _format_shell_description},
        "execute": {"allowed_decisions": ["approve", "reject"], "description": _format_execute_description},
        "write_file": {"allowed_decisions": ["approve", "reject"], "description": _format_write_file_description},
        "edit_file": {"allowed_decisions": ["approve", "reject"], "description": _format_edit_file_description},
        "web_search": {"allowed_decisions": ["approve", "reject"], "description": _format_web_search_description},
        "fetch_url": {"allowed_decisions": ["approve", "reject"], "description": _format_fetch_url_description},
        "task": {"allowed_decisions": ["approve", "reject"], "description": _format_task_description},
    }


def get_system_prompt(assistant_id: str, sandbox_type: str | None = None) -> str:
    """Get the base system prompt for the agent."""
    agent_dir_path = f"~/.deepagents/{assistant_id}"

    if sandbox_type:
        working_dir = "/workspace"
        working_dir_section = f"""### Current Working Directory

You are operating in a **remote Linux sandbox** at `{working_dir}`.

All code execution and file operations happen in this sandbox environment.

**Important:**
- The CLI is running locally on the user's machine, but you execute code remotely
- Use `{working_dir}` as your working directory for all operations

"""
    else:
        cwd = Path.cwd()
        working_dir_section = f"""<env>
Working directory: {cwd}
</env>

### Current Working Directory

The filesystem backend is currently operating in: `{cwd}`

### File System and Paths

**IMPORTANT - Path Handling:**
- All file paths must be absolute paths (e.g., `{cwd}/file.txt`)
- Use the working directory from <env> to construct absolute paths
- Example: To create a file in your working directory, use `{cwd}/research_project/file.md`
- Never use relative paths - always construct full absolute paths

"""

    return (
        working_dir_section
        + f"""### Skills Directory

Your skills are stored at: `{agent_dir_path}/skills/`
Skills may contain scripts or supporting files. When executing skill scripts with bash, use the real filesystem path:
Example: `bash python {agent_dir_path}/skills/web-research/script.py`

### Human-in-the-Loop Tool Approval

Some tool calls require user approval before execution. When a tool call is rejected by the user:
1. Accept their decision immediately - do NOT retry the same command
2. Explain that you understand they rejected the action
3. Suggest an alternative approach or ask for clarification
4. Never attempt the exact same rejected command again

Respect the user's decisions and work with them collaboratively.

### Web Search Tool Usage

When you use the web_search tool:
1. The tool will return search results with titles, URLs, and content excerpts
2. You MUST read and process these results, then respond naturally to the user
3. NEVER show raw JSON or tool results directly to the user
4. Synthesize the information from multiple sources into a coherent answer
5. Cite your sources by mentioning page titles or URLs when relevant
6. If the search doesn't find what you need, explain what you found and ask clarifying questions

The user only sees your text responses - not tool results. Always provide a complete, natural language answer after using web_search.

### Todo List Management

When using the write_todos tool:
1. Keep the todo list MINIMAL - aim for 3-6 items maximum
2. Only create todos for complex, multi-step tasks that truly need tracking
3. Break down work into clear, actionable items without over-fragmenting
4. For simple tasks (1-2 steps), just do them directly without creating todos
5. When first creating a todo list for a task, ALWAYS ask the user if the plan looks good before starting work
   - Create the todos, let them render, then ask: "Does this plan look good?" or similar
   - Wait for the user's response before marking the first todo as in_progress
   - If they want changes, adjust the plan accordingly
6. Update todo status promptly as you complete each item

The todo list is a planning tool - use it judiciously to avoid overwhelming the user with excessive task tracking."""
    )


class AgentFactory:
    """Factory for creating configured agents."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def create_agent(
        self,
        config: AgentConfig,
        sandbox: SandboxBackendProtocol | None = None,
    ) -> tuple[Pregel, CompositeBackend]:
        """Create a configured agent."""
        # Resolve model
        if config.model is None:
            model = self.settings.create_model()
        elif isinstance(config.model, str):
            model = self.settings.create_model(config.model)
        else:
            model = config.model

        # Setup agent directory
        if config.enable_memory or config.enable_skills:
            agent_dir = self.settings.ensure_agent_dir(config.assistant_id)
            agent_md = agent_dir / "agent.md"
            if not agent_md.exists():
                agent_md.write_text(get_default_coding_instructions())

        # Skills directories
        skills_dir = None
        project_skills_dir = None
        if config.enable_skills:
            skills_dir = self.settings.ensure_user_skills_dir(config.assistant_id)
            project_skills_dir = self.settings.get_project_skills_dir()

        # Build middleware stack
        middleware = []

        if sandbox is None:
            # Local mode
            backend = CompositeBackend(default=FilesystemBackend(), routes={})

            if config.enable_memory:
                middleware.append(
                    AgentMemoryMiddleware(settings=self.settings, assistant_id=config.assistant_id)
                )

            if config.enable_skills:
                middleware.append(
                    SkillsMiddleware(
                        skills_dir=skills_dir,
                        assistant_id=config.assistant_id,
                        project_skills_dir=project_skills_dir,
                    )
                )

            if config.enable_shell:
                middleware.append(
                    ShellMiddleware(workspace_root=str(Path.cwd()), env=os.environ)
                )
        else:
            # Sandbox mode
            backend = CompositeBackend(default=sandbox, routes={})

            if config.enable_memory:
                middleware.append(
                    AgentMemoryMiddleware(settings=self.settings, assistant_id=config.assistant_id)
                )

            if config.enable_skills:
                middleware.append(
                    SkillsMiddleware(
                        skills_dir=skills_dir,
                        assistant_id=config.assistant_id,
                        project_skills_dir=project_skills_dir,
                    )
                )

        # Add rules middleware if enabled
        if config.enable_rules:
            from dataagent_core.rules import FileRuleStore
            
            # Setup rule store with global, user, and project directories
            global_rules_dir = self.settings.user_deepagents_dir / "rules"
            user_rules_dir = self.settings.get_agent_dir(config.assistant_id) / "rules"
            project_rules_dir = None
            if self.settings.project_root:
                project_rules_dir = self.settings.project_root / ".dataagent" / "rules"
            
            rule_store = FileRuleStore(
                global_dir=global_rules_dir,
                user_dir=user_rules_dir,
                project_dir=project_rules_dir,
            )
            middleware.append(
                RulesMiddleware(
                    store=rule_store,
                    debug_mode=config.rules_debug_mode,
                )
            )

        middleware.extend(config.extra_middleware)

        # Build tools
        tools = [http_request, fetch_url]
        if self.settings.has_tavily:
            tools.append(web_search)
        tools.extend(config.extra_tools)

        # System prompt
        system_prompt = config.system_prompt or get_system_prompt(
            config.assistant_id, config.sandbox_type
        )
        
        # Append user context to system prompt if provided
        if config.user_context:
            from dataagent_core.user import build_user_context_prompt
            user_context_section = build_user_context_prompt(config.user_context)
            if user_context_section:
                system_prompt = f"{system_prompt}\n\n{user_context_section}"

        # Interrupt config
        interrupt_on = {} if config.auto_approve else _build_interrupt_config()

        # Create agent
        agent = create_deep_agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            backend=backend,
            middleware=middleware,
            interrupt_on=interrupt_on,
            checkpointer=InMemorySaver(),
        ).with_config({"recursion_limit": config.recursion_limit})

        return agent, backend
