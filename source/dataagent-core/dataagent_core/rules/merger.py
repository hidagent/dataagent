"""Rule merger for Agent Rules.

This module handles merging matched rules into a final list:
- Priority-based sorting (scope priority, then rule priority)
- Conflict detection and resolution
- Size limit enforcement
- System prompt generation
"""

import logging
from typing import Any

from dataagent_core.rules.models import Rule, RuleMatch, RuleScope


logger = logging.getLogger(__name__)


class RuleMerger:
    """Merges matched rules into a final list.
    
    Handles:
    - Sorting by scope priority and rule priority
    - Detecting and resolving name conflicts
    - Enforcing size limits
    - Building the system prompt section
    
    Scope priority (highest to lowest):
    - SESSION (4)
    - PROJECT (3)
    - USER (2)
    - GLOBAL (1)
    """

    # Scope priority values (higher = more important)
    SCOPE_PRIORITY = {
        RuleScope.GLOBAL: 1,
        RuleScope.USER: 2,
        RuleScope.PROJECT: 3,
        RuleScope.SESSION: 4,
    }

    def __init__(self, max_content_size: int = 100_000):
        """Initialize the merger.
        
        Args:
            max_content_size: Maximum total size of rule content in characters.
        """
        self.max_content_size = max_content_size

    def merge_rules(
        self,
        matches: list[RuleMatch],
    ) -> tuple[list[Rule], list[tuple[str, str, str]]]:
        """Merge matched rules into a final list.
        
        Args:
            matches: List of matched rules.
            
        Returns:
            Tuple of (final_rules, conflicts).
            - final_rules: Sorted list of rules to apply.
            - conflicts: List of (rule1, rule2, reason) for detected conflicts.
        """
        conflicts: list[tuple[str, str, str]] = []

        # Sort by priority
        sorted_matches = self._sort_by_priority(matches)

        # Process rules, handling duplicates and overrides
        final_rules: list[Rule] = []
        seen_names: dict[str, Rule] = {}

        for match in sorted_matches:
            rule = match.rule
            
            if rule.name in seen_names:
                existing = seen_names[rule.name]
                
                if rule.override:
                    # Override: replace existing rule
                    final_rules = [r for r in final_rules if r.name != rule.name]
                    final_rules.append(rule)
                    seen_names[rule.name] = rule
                    
                    conflicts.append((
                        rule.name,
                        existing.name,
                        f"overridden by {rule.scope.value} scope"
                    ))
                    logger.debug(
                        f"Rule '{rule.name}' from {rule.scope.value} "
                        f"overrides {existing.scope.value}"
                    )
                else:
                    # Conflict: keep higher priority (already in list)
                    conflicts.append((
                        rule.name,
                        existing.name,
                        f"duplicate name, keeping {existing.scope.value} scope"
                    ))
                    logger.debug(
                        f"Rule '{rule.name}' conflict: keeping {existing.scope.value}, "
                        f"skipping {rule.scope.value}"
                    )
            else:
                final_rules.append(rule)
                seen_names[rule.name] = rule

        # Enforce size limit
        final_rules = self._truncate_if_needed(final_rules)

        return final_rules, conflicts

    def _sort_by_priority(self, matches: list[RuleMatch]) -> list[RuleMatch]:
        """Sort matches by priority.
        
        Sort order:
        1. Scope priority (descending) - higher scope wins
        2. Rule priority (descending) - higher priority wins
        3. Name (ascending) - alphabetical for consistency
        
        Args:
            matches: List of matches to sort.
            
        Returns:
            Sorted list of matches.
        """
        def sort_key(match: RuleMatch) -> tuple[int, int, str]:
            rule = match.rule
            scope_priority = self.SCOPE_PRIORITY.get(rule.scope, 0)
            # Negate for descending order
            return (-scope_priority, -rule.priority, rule.name)

        return sorted(matches, key=sort_key)

    def _truncate_if_needed(self, rules: list[Rule]) -> list[Rule]:
        """Truncate rules if total size exceeds limit.
        
        Removes lower-priority rules (from the end) until within limit.
        
        Args:
            rules: List of rules sorted by priority.
            
        Returns:
            Truncated list of rules.
        """
        total_size = 0
        result = []

        for rule in rules:
            rule_size = len(rule.content)
            
            if total_size + rule_size <= self.max_content_size:
                result.append(rule)
                total_size += rule_size
            else:
                logger.warning(
                    f"Rule '{rule.name}' truncated due to size limit "
                    f"({total_size + rule_size} > {self.max_content_size})"
                )
                break

        return result

    def build_prompt_section(self, rules: list[Rule]) -> str:
        """Build the system prompt section from rules.
        
        Args:
            rules: List of rules to include.
            
        Returns:
            Formatted string for inclusion in system prompt.
        """
        if not rules:
            return ""

        sections = [
            "## Agent Rules\n",
            "The following rules guide your behavior:\n",
        ]

        for rule in rules:
            sections.append(f"### {rule.name}\n")
            sections.append(f"*{rule.description}*\n")
            sections.append(rule.content)
            sections.append("\n")

        return "\n".join(sections)

    def get_total_size(self, rules: list[Rule]) -> int:
        """Get total content size of rules.
        
        Args:
            rules: List of rules.
            
        Returns:
            Total size in characters.
        """
        return sum(len(rule.content) for rule in rules)

    def detect_conflicts(
        self,
        rules: list[Rule],
    ) -> list[dict[str, Any]]:
        """Detect conflicts between rules.
        
        Finds rules with the same name at different scopes.
        
        Args:
            rules: List of all rules.
            
        Returns:
            List of conflict dictionaries with name, scopes, and resolution.
        """
        # Group rules by name
        name_map: dict[str, list[Rule]] = {}
        for rule in rules:
            if rule.name not in name_map:
                name_map[rule.name] = []
            name_map[rule.name].append(rule)

        # Find conflicts
        conflicts = []
        for name, rule_list in name_map.items():
            if len(rule_list) > 1:
                # Sort by scope priority to determine winner
                sorted_rules = sorted(
                    rule_list,
                    key=lambda r: -self.SCOPE_PRIORITY.get(r.scope, 0)
                )
                winner = sorted_rules[0]
                
                conflicts.append({
                    "name": name,
                    "scopes": [r.scope.value for r in rule_list],
                    "resolution": f"Using {winner.scope.value} scope (highest priority)",
                    "winner_scope": winner.scope.value,
                })

        return conflicts
