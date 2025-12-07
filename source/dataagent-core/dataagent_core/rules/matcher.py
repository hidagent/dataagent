"""Rule matcher for Agent Rules.

This module handles matching rules against the current context:
- MatchContext: Context information for rule matching
- RuleMatcher: Matches rules based on inclusion mode and context
"""

import fnmatch
import logging
from dataclasses import dataclass, field
from typing import Any

from dataagent_core.rules.models import Rule, RuleInclusion, RuleMatch


logger = logging.getLogger(__name__)


@dataclass
class MatchContext:
    """Context for rule matching.
    
    Contains information about the current request that is used
    to determine which rules should be applied.
    
    Attributes:
        current_files: List of file paths currently in context.
        user_query: The user's query/message.
        session_id: Current session identifier.
        assistant_id: Current assistant identifier.
        manual_rules: List of rule names explicitly referenced by user.
        extra_vars: Additional context variables.
    """
    current_files: list[str] = field(default_factory=list)
    user_query: str = ""
    session_id: str = ""
    assistant_id: str = ""
    manual_rules: list[str] = field(default_factory=list)
    extra_vars: dict[str, Any] = field(default_factory=dict)


class RuleMatcher:
    """Matches rules against context.
    
    Evaluates each rule's inclusion mode against the current context
    to determine which rules should be applied.
    
    Inclusion modes:
    - ALWAYS: Always included
    - FILE_MATCH: Included when files match the pattern
    - MANUAL: Included only when explicitly referenced
    """

    def match_rules(
        self,
        rules: list[Rule],
        context: MatchContext,
    ) -> tuple[list[RuleMatch], list[tuple[str, str]]]:
        """Match rules against context.
        
        Args:
            rules: List of rules to evaluate.
            context: The current matching context.
            
        Returns:
            Tuple of (matched_rules, skipped_rules).
            - matched_rules: List of RuleMatch objects for matched rules.
            - skipped_rules: List of (rule_name, reason) for skipped rules.
        """
        matched: list[RuleMatch] = []
        skipped: list[tuple[str, str]] = []

        for rule in rules:
            # Skip disabled rules
            if not rule.enabled:
                skipped.append((rule.name, "disabled"))
                continue

            # Try to match the rule
            match_result = self._match_rule(rule, context)
            
            if match_result:
                matched.append(match_result)
                logger.debug(f"Rule '{rule.name}' matched: {match_result.match_reason}")
            else:
                reason = self._get_skip_reason(rule, context)
                skipped.append((rule.name, reason))
                logger.debug(f"Rule '{rule.name}' skipped: {reason}")

        return matched, skipped

    def _match_rule(self, rule: Rule, context: MatchContext) -> RuleMatch | None:
        """Match a single rule against context.
        
        Args:
            rule: The rule to match.
            context: The matching context.
            
        Returns:
            RuleMatch if the rule matches, None otherwise.
        """
        if rule.inclusion == RuleInclusion.ALWAYS:
            return RuleMatch(
                rule=rule,
                match_reason="always included",
            )

        if rule.inclusion == RuleInclusion.MANUAL:
            if rule.name in context.manual_rules:
                return RuleMatch(
                    rule=rule,
                    match_reason="manually referenced",
                )
            return None

        if rule.inclusion == RuleInclusion.FILE_MATCH:
            if not rule.file_match_pattern:
                logger.warning(
                    f"Rule '{rule.name}' has fileMatch inclusion but no pattern"
                )
                return None

            matched_files = self._match_files(
                rule.file_match_pattern,
                context.current_files,
            )
            
            if matched_files:
                return RuleMatch(
                    rule=rule,
                    match_reason=f"file pattern matched: {rule.file_match_pattern}",
                    matched_files=matched_files,
                )
            return None

        # Unknown inclusion mode
        logger.warning(f"Unknown inclusion mode for rule '{rule.name}': {rule.inclusion}")
        return None

    def _match_files(self, pattern: str, files: list[str]) -> list[str]:
        """Match files against a glob pattern.
        
        Args:
            pattern: Glob pattern to match (e.g., "*.py", "src/**/*.ts").
            files: List of file paths to check.
            
        Returns:
            List of file paths that match the pattern.
        """
        matched = []
        
        for file_path in files:
            # Try matching the full path
            if fnmatch.fnmatch(file_path, pattern):
                matched.append(file_path)
                continue
            
            # Try matching just the filename
            filename = file_path.split("/")[-1]
            if fnmatch.fnmatch(filename, pattern):
                matched.append(file_path)
                continue
            
            # Try matching with ** for recursive patterns
            if "**" in pattern:
                # Convert ** pattern to work with fnmatch
                # e.g., "src/**/*.py" should match "src/foo/bar.py"
                parts = pattern.split("**")
                if len(parts) == 2:
                    prefix, suffix = parts
                    prefix = prefix.rstrip("/")
                    suffix = suffix.lstrip("/")
                    
                    if file_path.startswith(prefix) and fnmatch.fnmatch(
                        file_path[len(prefix):].lstrip("/"), f"*{suffix}"
                    ):
                        matched.append(file_path)

        return matched

    def _get_skip_reason(self, rule: Rule, context: MatchContext) -> str:
        """Get the reason why a rule was skipped.
        
        Args:
            rule: The rule that was skipped.
            context: The matching context.
            
        Returns:
            Human-readable reason for skipping.
        """
        if rule.inclusion == RuleInclusion.MANUAL:
            return "not manually referenced"
        
        if rule.inclusion == RuleInclusion.FILE_MATCH:
            if not rule.file_match_pattern:
                return "no file pattern specified"
            return f"no files matched pattern: {rule.file_match_pattern}"
        
        return "unknown reason"

    def extract_manual_references(self, text: str) -> list[str]:
        """Extract manual rule references from text.
        
        Looks for @rulename patterns in the text.
        
        Args:
            text: Text to search for references.
            
        Returns:
            List of rule names referenced.
        """
        import re
        pattern = r"@(\w[\w\-]*)"
        return re.findall(pattern, text)

    def extract_file_references(self, text: str) -> list[str]:
        """Extract file references from text.
        
        Looks for file paths in various formats:
        - Backtick-quoted paths: `path/to/file.py`
        - file: prefix: file:path/to/file.py
        - path: prefix: path:path/to/file.py
        
        Args:
            text: Text to search for file references.
            
        Returns:
            List of file paths found.
        """
        import re
        
        files = []
        
        # Match backtick-quoted file paths
        backtick_pattern = r"`([^`]+\.\w+)`"
        files.extend(re.findall(backtick_pattern, text))
        
        # Match file: prefix
        file_prefix_pattern = r"file:([^\s]+)"
        files.extend(re.findall(file_prefix_pattern, text))
        
        # Match path: prefix
        path_prefix_pattern = r"path:([^\s]+)"
        files.extend(re.findall(path_prefix_pattern, text))
        
        return files
