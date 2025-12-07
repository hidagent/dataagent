"""Data models for Agent Rules.

This module defines the core data structures for the rules system:
- Rule: The main rule model with all configuration options
- RuleScope: Enum for rule scope levels (global, user, project, session)
- RuleInclusion: Enum for rule inclusion modes (always, fileMatch, manual)
- RuleMatch: Result of matching a rule against context
- RuleEvaluationTrace: Trace information for debugging rule evaluation
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RuleScope(Enum):
    """Rule scope levels.
    
    Defines the hierarchy of rule scopes, from lowest to highest priority:
    - GLOBAL: System-wide rules (~/.dataagent/rules/)
    - USER: User-specific rules (~/.dataagent/users/{user_id}/rules/)
    - PROJECT: Project-specific rules ({project_root}/.dataagent/rules/)
    - SESSION: Session-specific rules (runtime only)
    """
    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"
    SESSION = "session"


class RuleInclusion(Enum):
    """Rule inclusion modes.
    
    Defines when a rule should be included in the system prompt:
    - ALWAYS: Always include the rule
    - FILE_MATCH: Include when files match the specified pattern
    - MANUAL: Include only when explicitly referenced by user
    """
    ALWAYS = "always"
    FILE_MATCH = "fileMatch"
    MANUAL = "manual"


@dataclass
class Rule:
    """Agent rule model.
    
    Represents a single rule that guides agent behavior. Rules are stored
    as Markdown files with YAML frontmatter containing metadata.
    
    Attributes:
        name: Unique identifier for the rule
        description: Human-readable description of what the rule does
        content: The rule content in Markdown format
        scope: The scope level of this rule
        inclusion: When this rule should be included
        file_match_pattern: Glob pattern for FILE_MATCH inclusion mode
        priority: Priority within scope (1-100, higher = more important)
        override: Whether to override lower-priority rules with same name
        enabled: Whether the rule is active
        source_path: Path to the source file (if loaded from file)
        created_at: When the rule was created
        updated_at: When the rule was last modified
        metadata: Additional metadata from frontmatter
    """
    name: str
    description: str
    content: str
    scope: RuleScope
    inclusion: RuleInclusion = RuleInclusion.ALWAYS
    file_match_pattern: str | None = None
    priority: int = 50
    override: bool = False
    enabled: bool = True
    source_path: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate rule after initialization."""
        if not self.name:
            raise ValueError("Rule name cannot be empty")
        if not self.description:
            raise ValueError("Rule description cannot be empty")
        if not 1 <= self.priority <= 100:
            raise ValueError(f"Priority must be between 1 and 100, got {self.priority}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize rule to dictionary.
        
        Returns:
            Dictionary representation of the rule suitable for JSON serialization.
        """
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "scope": self.scope.value,
            "inclusion": self.inclusion.value,
            "file_match_pattern": self.file_match_pattern,
            "priority": self.priority,
            "override": self.override,
            "enabled": self.enabled,
            "source_path": self.source_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rule":
        """Deserialize rule from dictionary.
        
        Args:
            data: Dictionary containing rule data.
            
        Returns:
            Rule instance reconstructed from the dictionary.
            
        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.
        """
        return cls(
            name=data["name"],
            description=data["description"],
            content=data["content"],
            scope=RuleScope(data["scope"]),
            inclusion=RuleInclusion(data.get("inclusion", "always")),
            file_match_pattern=data.get("file_match_pattern"),
            priority=data.get("priority", 50),
            override=data.get("override", False),
            enabled=data.get("enabled", True),
            source_path=data.get("source_path"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now()
            ),
            metadata=data.get("metadata", {}),
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on name and scope."""
        if not isinstance(other, Rule):
            return NotImplemented
        return self.name == other.name and self.scope == other.scope

    def __hash__(self) -> int:
        """Hash based on name and scope."""
        return hash((self.name, self.scope))


@dataclass
class RuleMatch:
    """Result of matching a rule against context.
    
    Attributes:
        rule: The matched rule
        match_reason: Human-readable explanation of why the rule matched
        matched_files: List of files that triggered the match (for FILE_MATCH)
        context_vars: Context variables used in matching
    """
    rule: Rule
    match_reason: str
    matched_files: list[str] = field(default_factory=list)
    context_vars: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_name": self.rule.name,
            "rule_scope": self.rule.scope.value,
            "match_reason": self.match_reason,
            "matched_files": self.matched_files,
            "context_vars": self.context_vars,
        }


@dataclass
class RuleEvaluationTrace:
    """Trace information for rule evaluation.
    
    Used for debugging and understanding which rules were applied
    and why during a request.
    
    Attributes:
        request_id: Unique identifier for the request
        timestamp: When the evaluation occurred
        evaluated_rules: Names of all rules that were evaluated
        matched_rules: Rules that matched the context
        skipped_rules: Rules that were skipped with reasons
        conflicts: Detected conflicts between rules
        final_rules: Names of rules in the final merged result
        total_content_size: Total size of rule content in characters
    """
    request_id: str
    timestamp: datetime
    evaluated_rules: list[str]
    matched_rules: list[RuleMatch]
    skipped_rules: list[tuple[str, str]]  # (rule_name, reason)
    conflicts: list[tuple[str, str, str]]  # (rule1, rule2, reason)
    final_rules: list[str]
    total_content_size: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "evaluated_rules": self.evaluated_rules,
            "matched_rules": [m.to_dict() for m in self.matched_rules],
            "skipped_rules": [
                {"name": name, "reason": reason}
                for name, reason in self.skipped_rules
            ],
            "conflicts": [
                {"rule1": r1, "rule2": r2, "reason": reason}
                for r1, r2, reason in self.conflicts
            ],
            "final_rules": self.final_rules,
            "total_content_size": self.total_content_size,
        }
