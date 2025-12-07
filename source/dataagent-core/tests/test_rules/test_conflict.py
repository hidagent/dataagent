"""Tests for ConflictDetector.

**Feature: agent-rules**
**Property 14: Conflict Detection Accuracy**
**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
"""

import pytest
from hypothesis import given, strategies as st, settings

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion
from dataagent_core.rules.conflict import ConflictDetector, RuleConflict, ConflictReport


class TestConflictDetectorBasic:
    """Basic tests for ConflictDetector."""

    def test_no_conflicts_with_unique_names(self) -> None:
        """Test that no conflicts are detected with unique rule names."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="rule1",
                description="Rule 1",
                content="Content 1",
                scope=RuleScope.USER,
            ),
            Rule(
                name="rule2",
                description="Rule 2",
                content="Content 2",
                scope=RuleScope.PROJECT,
            ),
        ]
        
        report = detector.detect_conflicts(rules)
        
        assert not report.has_conflicts()
        assert len(report.conflicts) == 0

    def test_detects_same_name_conflict(self) -> None:
        """Test detection of same-name conflicts across scopes."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="shared-rule",
                description="Global version",
                content="Global content",
                scope=RuleScope.GLOBAL,
            ),
            Rule(
                name="shared-rule",
                description="User version",
                content="User content",
                scope=RuleScope.USER,
            ),
        ]
        
        report = detector.detect_conflicts(rules)
        
        assert report.has_conflicts()
        assert len(report.conflicts) == 1
        conflict = report.conflicts[0]
        assert conflict.conflict_type == "same_name"
        assert conflict.rule1_scope == RuleScope.USER  # Higher priority wins
        assert conflict.rule2_scope == RuleScope.GLOBAL

    def test_detects_multiple_same_name_conflicts(self) -> None:
        """Test detection of multiple same-name conflicts."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="multi-rule",
                description="Global",
                content="Global",
                scope=RuleScope.GLOBAL,
            ),
            Rule(
                name="multi-rule",
                description="User",
                content="User",
                scope=RuleScope.USER,
            ),
            Rule(
                name="multi-rule",
                description="Project",
                content="Project",
                scope=RuleScope.PROJECT,
            ),
        ]
        
        report = detector.detect_conflicts(rules)
        
        assert report.has_conflicts()
        # Project wins over both User and Global
        assert len(report.conflicts) == 2

    def test_scope_priority_in_resolution(self) -> None:
        """Test that higher scope priority wins in conflict resolution."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="priority-rule",
                description="Global",
                content="Global",
                scope=RuleScope.GLOBAL,
            ),
            Rule(
                name="priority-rule",
                description="Session",
                content="Session",
                scope=RuleScope.SESSION,
            ),
        ]
        
        report = detector.detect_conflicts(rules)
        
        assert report.has_conflicts()
        conflict = report.conflicts[0]
        # Session has highest priority
        assert conflict.rule1_scope == RuleScope.SESSION
        assert "session scope takes precedence" in conflict.resolution.lower()


class TestContradictoryRuleDetection:
    """Tests for contradictory rule detection."""

    def test_detects_allow_deny_contradiction(self) -> None:
        """Test detection of allow/deny contradictions."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="allow-rule",
                description="Allow rule",
                content="Always allow file operations",
                scope=RuleScope.USER,
            ),
            Rule(
                name="deny-rule",
                description="Deny rule",
                content="Never allow file operations",
                scope=RuleScope.PROJECT,
            ),
        ]
        
        report = detector.detect_conflicts(rules)
        
        # Should have a warning about potential contradiction
        assert len(report.warnings) > 0
        assert any("contradiction" in w.lower() for w in report.warnings)

    def test_no_warning_for_non_contradictory_rules(self) -> None:
        """Test that non-contradictory rules don't trigger warnings."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="rule1",
                description="Rule 1",
                content="Use Python for scripting",
                scope=RuleScope.USER,
            ),
            Rule(
                name="rule2",
                description="Rule 2",
                content="Follow PEP 8 guidelines",
                scope=RuleScope.PROJECT,
            ),
        ]
        
        report = detector.detect_conflicts(rules)
        
        assert len(report.warnings) == 0


class TestConflictReport:
    """Tests for ConflictReport."""

    def test_to_dict(self) -> None:
        """Test ConflictReport serialization."""
        conflict = RuleConflict(
            rule1_name="rule1",
            rule1_scope=RuleScope.USER,
            rule2_name="rule2",
            rule2_scope=RuleScope.GLOBAL,
            conflict_type="same_name",
            resolution="user scope wins",
            details="Test details",
        )
        report = ConflictReport(
            conflicts=[conflict],
            warnings=["Test warning"],
        )
        
        data = report.to_dict()
        
        assert data["total_conflicts"] == 1
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["rule1_name"] == "rule1"
        assert data["warnings"] == ["Test warning"]


class TestRuleConflict:
    """Tests for RuleConflict."""

    def test_to_dict(self) -> None:
        """Test RuleConflict serialization."""
        conflict = RuleConflict(
            rule1_name="winner",
            rule1_scope=RuleScope.PROJECT,
            rule2_name="loser",
            rule2_scope=RuleScope.GLOBAL,
            conflict_type="same_name",
            resolution="project wins",
            details="Details here",
        )
        
        data = conflict.to_dict()
        
        assert data["rule1_name"] == "winner"
        assert data["rule1_scope"] == "project"
        assert data["rule2_name"] == "loser"
        assert data["rule2_scope"] == "global"
        assert data["conflict_type"] == "same_name"
        assert data["resolution"] == "project wins"


class TestGetWinningRule:
    """Tests for get_winning_rule method."""

    def test_returns_highest_scope_priority(self) -> None:
        """Test that highest scope priority rule wins."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="rule",
                description="Global",
                content="Global",
                scope=RuleScope.GLOBAL,
            ),
            Rule(
                name="rule",
                description="Project",
                content="Project",
                scope=RuleScope.PROJECT,
            ),
        ]
        
        winner = detector.get_winning_rule(rules)
        
        assert winner is not None
        assert winner.scope == RuleScope.PROJECT

    def test_returns_none_for_empty_list(self) -> None:
        """Test that None is returned for empty list."""
        detector = ConflictDetector()
        
        winner = detector.get_winning_rule([])
        
        assert winner is None

    def test_considers_rule_priority_within_scope(self) -> None:
        """Test that rule priority is considered within same scope."""
        detector = ConflictDetector()
        rules = [
            Rule(
                name="rule",
                description="Low priority",
                content="Low",
                scope=RuleScope.USER,
                priority=10,
            ),
            Rule(
                name="rule",
                description="High priority",
                content="High",
                scope=RuleScope.USER,
                priority=90,
            ),
        ]
        
        winner = detector.get_winning_rule(rules)
        
        assert winner is not None
        assert winner.priority == 90


class TestConflictDetectorPropertyTests:
    """Property-based tests for ConflictDetector."""

    @given(
        num_rules=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=50)
    def test_conflict_count_matches_duplicate_names(self, num_rules: int) -> None:
        """
        **Property 14: Conflict Detection Accuracy**
        
        The number of conflicts should match the number of duplicate names.
        """
        detector = ConflictDetector()
        
        # Create rules with same name at different scopes
        scopes = [RuleScope.GLOBAL, RuleScope.USER, RuleScope.PROJECT]
        rules = []
        for i in range(min(num_rules, len(scopes))):
            rules.append(
                Rule(
                    name="same-name",
                    description=f"Rule {i}",
                    content=f"Content {i}",
                    scope=scopes[i],
                )
            )
        
        report = detector.detect_conflicts(rules)
        
        # Number of conflicts should be (n-1) for n rules with same name
        expected_conflicts = max(0, len(rules) - 1)
        assert len(report.conflicts) == expected_conflicts

    @given(
        names=st.lists(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_unique_names_no_conflicts(self, names: list[str]) -> None:
        """Test that unique names produce no conflicts."""
        detector = ConflictDetector()
        
        # Make names unique
        unique_names = list(set(names))
        
        rules = [
            Rule(
                name=name,
                description=f"Rule {name}",
                content=f"Content for {name}",
                scope=RuleScope.USER,
            )
            for name in unique_names
        ]
        
        report = detector.detect_conflicts(rules)
        
        # No same-name conflicts with unique names
        same_name_conflicts = [
            c for c in report.conflicts if c.conflict_type == "same_name"
        ]
        assert len(same_name_conflicts) == 0
