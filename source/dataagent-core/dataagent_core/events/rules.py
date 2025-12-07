"""Rule-related events for DataAgent Core.

**Feature: agent-rules**
**Validates: Requirements 13.2, 13.3**
"""

from dataclasses import dataclass, field
from typing import Any

from dataagent_core.events import ExecutionEvent


@dataclass
class RulesAppliedEvent(ExecutionEvent):
    """Event emitted when rules are applied to a request.
    
    This event contains information about which rules were triggered,
    how many were skipped, and any conflicts detected.
    """
    event_type: str = field(default="rules_applied", init=False)
    triggered_rules: list[dict[str, Any]] = field(default_factory=list)
    skipped_count: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)
    total_size: int = 0

    def _extra_fields(self) -> dict:
        return {
            "triggered_rules": self.triggered_rules,
            "skipped_count": self.skipped_count,
            "conflicts": self.conflicts,
            "total_size": self.total_size,
        }


@dataclass
class RuleDebugEvent(ExecutionEvent):
    """Event emitted when debug mode is enabled for rule evaluation.
    
    This event contains the full trace information for debugging
    rule matching and merging behavior.
    """
    event_type: str = field(default="rule_debug", init=False)
    request_id: str = ""
    evaluated_rules: list[str] = field(default_factory=list)
    matched_rules: list[dict[str, Any]] = field(default_factory=list)
    skipped_rules: list[dict[str, str]] = field(default_factory=list)
    conflicts: list[dict[str, str]] = field(default_factory=list)
    final_rules: list[str] = field(default_factory=list)
    total_content_size: int = 0

    def _extra_fields(self) -> dict:
        return {
            "request_id": self.request_id,
            "evaluated_rules": self.evaluated_rules,
            "matched_rules": self.matched_rules,
            "skipped_rules": self.skipped_rules,
            "conflicts": self.conflicts,
            "final_rules": self.final_rules,
            "total_content_size": self.total_content_size,
        }
