"""Skills middleware for loading and exposing agent skills."""

import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime


MAX_SKILL_FILE_SIZE = 10 * 1024 * 1024


class SkillMetadata(TypedDict):
    """Metadata for a skill."""
    name: str
    description: str
    path: str
    source: str


class SkillsState(AgentState):
    """State for the skills middleware."""
    skills_metadata: NotRequired[list[SkillMetadata]]


class SkillsStateUpdate(TypedDict):
    """State update for the skills middleware."""
    skills_metadata: list[SkillMetadata]


SKILLS_SYSTEM_PROMPT = """

## Skills System

You have access to a skills library that provides specialized capabilities and domain knowledge.

{skills_locations}

**Available Skills:**

{skills_list}

**How to Use Skills (Progressive Disclosure):**

Skills follow a **progressive disclosure** pattern - you know they exist (name + description above), but you only read the full instructions when needed:

1. **Recognize when a skill applies**: Check if the user's task matches any skill's description
2. **Read the skill's full instructions**: The skill list above shows the exact path to use with read_file
3. **Follow the skill's instructions**: SKILL.md contains step-by-step workflows, best practices, and examples
4. **Access supporting files**: Skills may include Python scripts, configs, or reference docs - use absolute paths

**When to Use Skills:**
- When the user's request matches a skill's domain (e.g., "research X" → web-research skill)
- When you need specialized knowledge or structured workflows
- When a skill provides proven patterns for complex tasks
"""


def _is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check if a path is safely contained within base_dir."""
    try:
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()
        resolved_path.relative_to(resolved_base)
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def _parse_skill_metadata(skill_md_path: Path, source: str) -> SkillMetadata | None:
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        file_size = skill_md_path.stat().st_size
        if file_size > MAX_SKILL_FILE_SIZE:
            return None

        content = skill_md_path.read_text(encoding="utf-8")

        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            return None

        frontmatter = match.group(1)
        metadata: dict[str, str] = {}
        for line in frontmatter.split("\n"):
            kv_match = re.match(r"^(\w+):\s*(.+)$", line.strip())
            if kv_match:
                key, value = kv_match.groups()
                metadata[key] = value.strip()

        if "name" not in metadata or "description" not in metadata:
            return None

        return SkillMetadata(
            name=metadata["name"],
            description=metadata["description"],
            path=str(skill_md_path),
            source=source,
        )

    except (OSError, UnicodeDecodeError):
        return None


def _list_skills_from_dir(skills_dir: Path, source: str) -> list[SkillMetadata]:
    """List all skills from a single skills directory."""
    skills_dir = skills_dir.expanduser()
    if not skills_dir.exists():
        return []

    try:
        resolved_base = skills_dir.resolve()
    except (OSError, RuntimeError):
        return []

    skills: list[SkillMetadata] = []

    for skill_dir in skills_dir.iterdir():
        if not _is_safe_path(skill_dir, resolved_base):
            continue

        if not skill_dir.is_dir():
            continue

        skill_md_path = skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            continue

        if not _is_safe_path(skill_md_path, resolved_base):
            continue

        metadata = _parse_skill_metadata(skill_md_path, source=source)
        if metadata:
            skills.append(metadata)

    return skills


def list_skills(
    *,
    user_skills_dir: Path | None = None,
    project_skills_dir: Path | None = None,
    builtin_skills_dir: Path | None = None,
) -> list[SkillMetadata]:
    """List skills from user, project, and/or builtin directories.
    
    Priority (higher overrides lower):
    1. Project skills (highest)
    2. User skills
    3. Builtin skills (lowest)
    """
    all_skills: dict[str, SkillMetadata] = {}

    # Load builtin skills first (lowest priority)
    if builtin_skills_dir:
        builtin_skills = _list_skills_from_dir(builtin_skills_dir, source="builtin")
        for skill in builtin_skills:
            all_skills[skill["name"]] = skill

    # Load user skills (overrides builtin)
    if user_skills_dir:
        user_skills = _list_skills_from_dir(user_skills_dir, source="user")
        for skill in user_skills:
            all_skills[skill["name"]] = skill

    # Load project skills (highest priority, overrides user and builtin)
    if project_skills_dir:
        project_skills = _list_skills_from_dir(project_skills_dir, source="project")
        for skill in project_skills:
            all_skills[skill["name"]] = skill

    return list(all_skills.values())


class SkillsMiddleware(AgentMiddleware):
    """Middleware for loading and exposing agent skills."""

    state_schema = SkillsState

    def __init__(
        self,
        *,
        skills_dir: str | Path,
        assistant_id: str,
        project_skills_dir: str | Path | None = None,
        builtin_skills_dir: str | Path | None = None,
    ) -> None:
        self.skills_dir = Path(skills_dir).expanduser()
        self.assistant_id = assistant_id
        self.project_skills_dir = (
            Path(project_skills_dir).expanduser() if project_skills_dir else None
        )
        self.builtin_skills_dir = (
            Path(builtin_skills_dir).expanduser() if builtin_skills_dir else None
        )
        self.user_skills_display = f"~/.deepagents/{assistant_id}/skills"
        self.system_prompt_template = SKILLS_SYSTEM_PROMPT

    def _format_skills_locations(self) -> str:
        locations = [f"**User Skills**: `{self.user_skills_display}`"]
        if self.project_skills_dir:
            locations.append(
                f"**Project Skills**: `{self.project_skills_dir}` (overrides user skills)"
            )
        if self.builtin_skills_dir:
            locations.append(
                f"**Built-in Skills**: System-provided skills"
            )
        return "\n".join(locations)

    def _format_skills_list(self, skills: list[SkillMetadata]) -> str:
        if not skills:
            return "(No skills available yet)"

        builtin_skills = [s for s in skills if s["source"] == "builtin"]
        user_skills = [s for s in skills if s["source"] == "user"]
        project_skills = [s for s in skills if s["source"] == "project"]

        lines = []

        if builtin_skills:
            lines.append("**Built-in Skills:**")
            for skill in builtin_skills:
                lines.append(f"- **{skill['name']}**: {skill['description']}")
                lines.append(f"  → Read `{skill['path']}` for full instructions")
            lines.append("")

        if user_skills:
            lines.append("**User Skills:**")
            for skill in user_skills:
                lines.append(f"- **{skill['name']}**: {skill['description']}")
                lines.append(f"  → Read `{skill['path']}` for full instructions")
            lines.append("")

        if project_skills:
            lines.append("**Project Skills:**")
            for skill in project_skills:
                lines.append(f"- **{skill['name']}**: {skill['description']}")
                lines.append(f"  → Read `{skill['path']}` for full instructions")

        return "\n".join(lines)

    def before_agent(self, state: SkillsState, runtime: Runtime) -> SkillsStateUpdate | None:
        skills = list_skills(
            user_skills_dir=self.skills_dir,
            project_skills_dir=self.project_skills_dir,
            builtin_skills_dir=self.builtin_skills_dir,
        )
        return SkillsStateUpdate(skills_metadata=skills)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        skills_metadata = request.state.get("skills_metadata", [])
        skills_locations = self._format_skills_locations()
        skills_list = self._format_skills_list(skills_metadata)

        skills_section = self.system_prompt_template.format(
            skills_locations=skills_locations,
            skills_list=skills_list,
        )

        if request.system_prompt:
            system_prompt = request.system_prompt + "\n\n" + skills_section
        else:
            system_prompt = skills_section

        return handler(request.override(system_prompt=system_prompt))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        state = cast("SkillsState", request.state)
        skills_metadata = state.get("skills_metadata", [])
        skills_locations = self._format_skills_locations()
        skills_list = self._format_skills_list(skills_metadata)

        skills_section = self.system_prompt_template.format(
            skills_locations=skills_locations,
            skills_list=skills_list,
        )

        if request.system_prompt:
            system_prompt = request.system_prompt + "\n\n" + skills_section
        else:
            system_prompt = skills_section

        return await handler(request.override(system_prompt=system_prompt))
