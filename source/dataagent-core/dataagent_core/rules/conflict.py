"""Conflict detection for agent rules.

**Feature: agent-rules**
**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
"""

from dataclasses import dataclass, field
from typing import Any

from dataagent_core.rules.models import Rule, RuleScope


@dataclass
class RuleConflict:
    """Represents a conflict between two rules."""
    rule1_name: str
    rule1_scope: RuleScope
    rule2_name: str
    rule2_scope: RuleScope
    conflict_type: str  # "same_name", "contradictory"
    resolution: str  # How the conflict is resolved
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule1_name": self.rule1_name,
            "rule1_scope": self.rule1_scope.value,
            "rule2_name": self.rule2_name,
            "rule2_scope": self.rule2_scope.value,
            "conflict_type": self.conflict_type,
            "resolution": self.resolution,
            "details": self.details,
        }


@dataclass
class ConflictReport:
    """Report of all detected conflicts."""
    conflicts: list[RuleConflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return len(self.conflicts) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conflicts": [c.to_dict() for c in self.conflicts],
            "warnings": self.warnings,
            "total_conflicts": len(self.conflicts),
        }


class ConflictDetector:
    """Detects conflicts between rules.
    
    Conflicts can occur when:
    1. Multiple rules have the same name at different scopes
    2. Rules have contradictory instructions (detected via keywords)
    """

    # Scope priority for resolution (higher number = higher priority)
    SCOPE_PRIORITY = {
        RuleScope.GLOBAL: 1,
        RuleScope.USER: 2,
        RuleScope.PROJECT: 3,
        RuleScope.SESSION: 4,
    }

    def detect_conflicts(self, rules: list[Rule]) -> ConflictReport:
        """Detect all conflicts in a list of rules.
        
        Args:
            rules: List of rules to check for conflicts.
            
        Returns:
            ConflictReport containing all detected conflicts.
        """
        report = ConflictReport()
        
        # Detect same-name conflicts
        self._detect_same_name_conflicts(rules, report)
        
        # Detect potential contradictory rules
        self._detect_contradictory_rules(rules, report)
        
        return report

    def _detect_same_name_conflicts(
        self, rules: list[Rule], report: ConflictReport
    ) -> None:
        """Detect rules with the same name at different scopes."""
        # Group rules by name
        rules_by_name: dict[str, list[Rule]] = {}
        for rule in rules:
            if rule.name not in rules_by_name:
                rules_by_name[rule.name] = []
            rules_by_name[rule.name].append(rule)
        
        # Check for conflicts
        for name, rule_list in rules_by_name.items():
            if len(rule_list) > 1:
                # Sort by scope priority
                sorted_rules = sorted(
                    rule_list,
                    key=lambda r: self.SCOPE_PRIORITY.get(r.scope, 0),
                    reverse=True,
                )
                
                # The highest priority rule wins
                winner = sorted_rules[0]
                
                for loser in sorted_rules[1:]:
                    conflict = RuleConflict(
                        rule1_name=winner.name,
                        rule1_scope=winner.scope,
                        rule2_name=loser.name,
                        rule2_scope=loser.scope,
                        conflict_type="same_name",
                        resolution=f"{winner.scope.value} scope takes precedence",
                        details=f"Rule '{name}' exists at both {winner.scope.value} and {loser.scope.value} scopes",
                    )
                    report.conflicts.append(conflict)

    def _detect_contradictory_rules(
        self, rules: list[Rule], report: ConflictReport
    ) -> None:
        """Detect potentially contradictory rules based on keywords.
        
        This is a heuristic check that looks for rules that might
        have conflicting instructions.
        """
        # Keywords that might indicate contradictory rules
        contradiction_pairs = [
            (["always", "must", "required"], ["never", "forbidden", "prohibited"]),
            (["enable", "allow", "permit"], ["disable", "deny", "block"]),
            (["include", "add"], ["exclude", "remove"]),
        ]
        
        for i, rule1 in enumerate(rules):
            content1_lower = rule1.content.lower()
            
            for rule2 in rules[i + 1:]:
                content2_lower = rule2.content.lower()
                
                for positive_words, negative_words in contradiction_pairs:
                    has_positive_1 = any(w in content1_lower for w in positive_words)
                    has_negative_1 = any(w in content1_lower for w in negative_words)
                    has_positive_2 = any(w in content2_lower for w in positive_words)
                    has_negative_2 = any(w in content2_lower for w in negative_words)
                    
                    # Check for potential contradiction
                    if (has_positive_1 and has_negative_2) or (has_negative_1 and has_positive_2):
                        # Only warn, don't create a hard conflict
                        warning = (
                            f"Potential contradiction between '{rule1.name}' "
                            f"({rule1.scope.value}) and '{rule2.name}' ({rule2.scope.value}): "
                            f"rules may have conflicting instructions"
                        )
                        if warning not in report.warnings:
                            report.warnings.append(warning)
                        break

    def get_winning_rule(self, rules: list[Rule]) -> Rule | None:
        """Get the rule that would win in case of conflict.
        
        Args:
            rules: List of rules with the same name.
            
        Returns:
            The rule with highest priority, or None if list is empty.
        """
        if not rules:
            return None
        
        return max(
            rules,
            key=lambda r: (
                self.SCOPE_PRIORITY.get(r.scope, 0),
                r.priority,
            ),
        )
