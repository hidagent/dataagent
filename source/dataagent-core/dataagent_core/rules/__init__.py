"""Agent Rules module for DataAgent Core.

This module provides rule-based configuration for agent behavior,
supporting multi-level rules (global, user, project), conditional
triggering, and priority management.
"""

from dataagent_core.rules.models import (
    Rule,
    RuleScope,
    RuleInclusion,
    RuleMatch,
    RuleEvaluationTrace,
)
from dataagent_core.rules.parser import RuleParser, RuleParseError, MAX_RULE_FILE_SIZE
from dataagent_core.rules.store import RuleStore, FileRuleStore, MemoryRuleStore
from dataagent_core.rules.matcher import RuleMatcher, MatchContext
from dataagent_core.rules.merger import RuleMerger
from dataagent_core.rules.conflict import ConflictDetector, RuleConflict, ConflictReport

__all__ = [
    # Models
    "Rule",
    "RuleScope",
    "RuleInclusion",
    "RuleMatch",
    "RuleEvaluationTrace",
    # Parser
    "RuleParser",
    "RuleParseError",
    "MAX_RULE_FILE_SIZE",
    # Store
    "RuleStore",
    "FileRuleStore",
    "MemoryRuleStore",
    # Matcher
    "RuleMatcher",
    "MatchContext",
    # Merger
    "RuleMerger",
    # Conflict Detection
    "ConflictDetector",
    "RuleConflict",
    "ConflictReport",
]
