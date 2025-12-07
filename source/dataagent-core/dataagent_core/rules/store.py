"""Rule storage for Agent Rules.

This module provides storage backends for rules:
- RuleStore: Abstract base class defining the storage interface
- FileRuleStore: File-based storage implementation
- MemoryRuleStore: In-memory storage for testing
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from dataagent_core.rules.models import Rule, RuleScope
from dataagent_core.rules.parser import RuleParser, RuleParseError


logger = logging.getLogger(__name__)


class RuleStore(ABC):
    """Abstract base class for rule storage.
    
    Defines the interface for storing and retrieving rules.
    Implementations can use different backends (file system, database, etc.).
    """

    @abstractmethod
    def list_rules(self, scope: RuleScope | None = None) -> list[Rule]:
        """List all rules, optionally filtered by scope.
        
        Args:
            scope: Optional scope to filter by.
            
        Returns:
            List of rules matching the filter.
        """
        ...

    @abstractmethod
    def get_rule(self, name: str, scope: RuleScope | None = None) -> Rule | None:
        """Get a rule by name.
        
        Args:
            name: The rule name to look up.
            scope: Optional scope to search in. If None, searches all scopes
                   in priority order (project > user > global).
                   
        Returns:
            The rule if found, None otherwise.
        """
        ...

    @abstractmethod
    def save_rule(self, rule: Rule) -> None:
        """Save a rule.
        
        Args:
            rule: The rule to save.
            
        Raises:
            ValueError: If the rule cannot be saved (e.g., invalid scope).
        """
        ...

    @abstractmethod
    def delete_rule(self, name: str, scope: RuleScope) -> bool:
        """Delete a rule.
        
        Args:
            name: The rule name to delete.
            scope: The scope to delete from.
            
        Returns:
            True if the rule was deleted, False if not found.
        """
        ...

    @abstractmethod
    def reload(self) -> None:
        """Reload rules from the underlying storage.
        
        This should refresh the cache and pick up any external changes.
        """
        ...

    def rule_exists(self, name: str, scope: RuleScope | None = None) -> bool:
        """Check if a rule exists.
        
        Args:
            name: The rule name to check.
            scope: Optional scope to check in.
            
        Returns:
            True if the rule exists, False otherwise.
        """
        return self.get_rule(name, scope) is not None


class FileRuleStore(RuleStore):
    """File-based rule storage.
    
    Stores rules as Markdown files with YAML frontmatter in designated
    directories for each scope level.
    
    Directory structure:
    - Global: ~/.dataagent/rules/
    - User: ~/.dataagent/users/{user_id}/rules/
    - Project: {project_root}/.dataagent/rules/
    
    Attributes:
        global_dir: Path to global rules directory.
        user_dir: Path to user rules directory.
        project_dir: Path to project rules directory.
    """

    def __init__(
        self,
        global_dir: Path | None = None,
        user_dir: Path | None = None,
        project_dir: Path | None = None,
    ):
        """Initialize the file rule store.
        
        Args:
            global_dir: Path to global rules directory.
            user_dir: Path to user rules directory.
            project_dir: Path to project rules directory.
        """
        self.global_dir = global_dir
        self.user_dir = user_dir
        self.project_dir = project_dir
        self.parser = RuleParser()
        self._cache: dict[str, Rule] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure rules are loaded into cache."""
        if not self._loaded:
            self.reload()

    def list_rules(self, scope: RuleScope | None = None) -> list[Rule]:
        """List all rules, optionally filtered by scope."""
        self._ensure_loaded()
        
        if scope is None:
            return list(self._cache.values())
        
        return [r for r in self._cache.values() if r.scope == scope]

    def get_rule(self, name: str, scope: RuleScope | None = None) -> Rule | None:
        """Get a rule by name."""
        self._ensure_loaded()
        
        if scope is not None:
            key = f"{scope.value}:{name}"
            return self._cache.get(key)
        
        # Search in priority order: project > user > global
        for s in [RuleScope.PROJECT, RuleScope.USER, RuleScope.GLOBAL]:
            key = f"{s.value}:{name}"
            if key in self._cache:
                return self._cache[key]
        
        return None

    def save_rule(self, rule: Rule) -> None:
        """Save a rule to file."""
        dir_path = self._get_dir_for_scope(rule.scope)
        if not dir_path:
            raise ValueError(f"No directory configured for scope: {rule.scope}")

        # Ensure directory exists
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Generate file path
        file_path = dir_path / f"{rule.name}.md"
        
        # Generate file content
        content = self._generate_rule_file(rule)
        
        # Write file
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved rule '{rule.name}' to {file_path}")
        
        # Update cache
        key = f"{rule.scope.value}:{rule.name}"
        rule.source_path = str(file_path)
        self._cache[key] = rule

    def delete_rule(self, name: str, scope: RuleScope) -> bool:
        """Delete a rule file."""
        dir_path = self._get_dir_for_scope(scope)
        if not dir_path:
            return False

        file_path = dir_path / f"{name}.md"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted rule '{name}' from {file_path}")
            
            # Update cache
            key = f"{scope.value}:{name}"
            self._cache.pop(key, None)
            return True
        
        return False

    def reload(self) -> None:
        """Reload all rules from disk."""
        self._cache.clear()
        
        # Load rules from each scope directory
        scope_dirs = [
            (RuleScope.GLOBAL, self.global_dir),
            (RuleScope.USER, self.user_dir),
            (RuleScope.PROJECT, self.project_dir),
        ]
        
        for scope, dir_path in scope_dirs:
            if dir_path and dir_path.exists():
                for rule in self._load_rules_from_dir(dir_path, scope):
                    key = f"{scope.value}:{rule.name}"
                    self._cache[key] = rule
        
        self._loaded = True
        logger.debug(f"Loaded {len(self._cache)} rules")

    def _load_rules_from_dir(self, dir_path: Path, scope: RuleScope) -> Iterator[Rule]:
        """Load all rules from a directory."""
        for file_path in dir_path.glob("*.md"):
            try:
                rule = self.parser.parse_file(file_path, scope)
                if rule:
                    yield rule
            except RuleParseError as e:
                logger.warning(f"Failed to parse rule file {file_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading rule {file_path}: {e}")

    def _get_dir_for_scope(self, scope: RuleScope) -> Path | None:
        """Get the directory path for a scope."""
        return {
            RuleScope.GLOBAL: self.global_dir,
            RuleScope.USER: self.user_dir,
            RuleScope.PROJECT: self.project_dir,
        }.get(scope)

    def _generate_rule_file(self, rule: Rule) -> str:
        """Generate rule file content from a Rule object."""
        lines = [
            "---",
            f"name: {rule.name}",
            f"description: {rule.description}",
            f"inclusion: {rule.inclusion.value}",
        ]
        
        if rule.file_match_pattern:
            lines.append(f"fileMatchPattern: {rule.file_match_pattern}")
        
        if rule.priority != 50:
            lines.append(f"priority: {rule.priority}")
        
        if rule.override:
            lines.append("override: true")
        
        if not rule.enabled:
            lines.append("enabled: false")
        
        lines.extend(["---", "", rule.content])
        
        return "\n".join(lines)

    def get_rule_path(self, name: str, scope: RuleScope) -> Path | None:
        """Get the file path for a rule.
        
        Args:
            name: The rule name.
            scope: The rule scope.
            
        Returns:
            Path to the rule file, or None if scope has no directory.
        """
        dir_path = self._get_dir_for_scope(scope)
        if not dir_path:
            return None
        return dir_path / f"{name}.md"


class MemoryRuleStore(RuleStore):
    """In-memory rule storage for testing.
    
    Stores rules in memory without persisting to disk.
    Useful for unit tests and temporary rule storage.
    """

    def __init__(self) -> None:
        """Initialize the memory store."""
        self._rules: dict[str, Rule] = {}

    def list_rules(self, scope: RuleScope | None = None) -> list[Rule]:
        """List all rules, optionally filtered by scope."""
        if scope is None:
            return list(self._rules.values())
        return [r for r in self._rules.values() if r.scope == scope]

    def get_rule(self, name: str, scope: RuleScope | None = None) -> Rule | None:
        """Get a rule by name."""
        if scope is not None:
            key = f"{scope.value}:{name}"
            return self._rules.get(key)
        
        # Search in priority order
        for s in [RuleScope.PROJECT, RuleScope.USER, RuleScope.GLOBAL]:
            key = f"{s.value}:{name}"
            if key in self._rules:
                return self._rules[key]
        
        return None

    def save_rule(self, rule: Rule) -> None:
        """Save a rule to memory."""
        key = f"{rule.scope.value}:{rule.name}"
        self._rules[key] = rule

    def delete_rule(self, name: str, scope: RuleScope) -> bool:
        """Delete a rule from memory."""
        key = f"{scope.value}:{name}"
        if key in self._rules:
            del self._rules[key]
            return True
        return False

    def reload(self) -> None:
        """No-op for memory store."""
        pass

    def clear(self) -> None:
        """Clear all rules from memory."""
        self._rules.clear()
