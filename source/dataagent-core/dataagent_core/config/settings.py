"""Configuration and settings for DataAgent Core."""

import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import dotenv
from langchain_core.language_models import BaseChatModel

dotenv.load_dotenv()


def _find_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for .git directory."""
    current = Path(start_path or Path.cwd()).resolve()
    for parent in [current, *list(current.parents)]:
        git_dir = parent / ".git"
        if git_dir.exists():
            return parent
    return None


@dataclass
class Settings:
    """Global settings for DataAgent Core."""

    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None
    tavily_api_key: str | None
    project_root: Path | None

    @classmethod
    def from_environment(cls, *, start_path: Path | None = None) -> "Settings":
        """Create settings by detecting the current environment."""
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            tavily_api_key=os.environ.get("TAVILY_API_KEY"),
            project_root=_find_project_root(start_path),
        )

    @property
    def has_openai(self) -> bool:
        return self.openai_api_key is not None

    @property
    def has_anthropic(self) -> bool:
        return self.anthropic_api_key is not None

    @property
    def has_google(self) -> bool:
        return self.google_api_key is not None

    @property
    def has_tavily(self) -> bool:
        return self.tavily_api_key is not None

    @property
    def has_project(self) -> bool:
        return self.project_root is not None

    @property
    def user_deepagents_dir(self) -> Path:
        return Path.home() / ".deepagents"

    @staticmethod
    def _is_valid_agent_name(agent_name: str) -> bool:
        if not agent_name or not agent_name.strip():
            return False
        return bool(re.match(r"^[a-zA-Z0-9_\-\s]+$", agent_name))

    def get_agent_dir(self, agent_name: str) -> Path:
        if not self._is_valid_agent_name(agent_name):
            raise ValueError(f"Invalid agent name: {agent_name!r}")
        return Path.home() / ".deepagents" / agent_name

    def ensure_agent_dir(self, agent_name: str) -> Path:
        agent_dir = self.get_agent_dir(agent_name)
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    def get_user_agent_md_path(self, agent_name: str) -> Path:
        return self.get_agent_dir(agent_name) / "agent.md"

    def get_project_agent_md_path(self) -> Path | None:
        if not self.project_root:
            return None
        return self.project_root / ".deepagents" / "agent.md"

    def get_user_skills_dir(self, agent_name: str) -> Path:
        return self.get_agent_dir(agent_name) / "skills"

    def ensure_user_skills_dir(self, agent_name: str) -> Path:
        skills_dir = self.get_user_skills_dir(agent_name)
        skills_dir.mkdir(parents=True, exist_ok=True)
        return skills_dir

    def get_project_skills_dir(self) -> Path | None:
        if not self.project_root:
            return None
        return self.project_root / ".deepagents" / "skills"

    def create_model(self, model_name: str | None = None) -> BaseChatModel:
        """Create a chat model based on available API keys."""
        if self.has_openai:
            from langchain_openai import ChatOpenAI
            name = model_name or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            return ChatOpenAI(model=name)

        if self.has_anthropic:
            from langchain_anthropic import ChatAnthropic
            name = model_name or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
            return ChatAnthropic(model_name=name, max_tokens=20_000)

        if self.has_google:
            from langchain_google_genai import ChatGoogleGenerativeAI
            name = model_name or os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
            return ChatGoogleGenerativeAI(model=name, temperature=0)

        raise RuntimeError(
            "No API key configured. Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY."
        )


class SessionState:
    """Holds mutable session state."""

    def __init__(self, auto_approve: bool = False) -> None:
        self.auto_approve = auto_approve
        self.thread_id = str(uuid.uuid4())

    def toggle_auto_approve(self) -> bool:
        self.auto_approve = not self.auto_approve
        return self.auto_approve


def get_default_coding_instructions() -> str:
    """Get the default coding agent instructions."""
    default_prompt_path = Path(__file__).parent / "default_agent_prompt.md"
    if default_prompt_path.exists():
        return default_prompt_path.read_text()
    return "You are a helpful AI assistant."
