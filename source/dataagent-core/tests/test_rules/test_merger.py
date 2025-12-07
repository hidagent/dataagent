"""Property-based tests for RuleMerger.

**Feature: agent-rules, Property 4: Scope Priority Ordering**
**Feature: agent-rules, Property 8: Priority Ordering Consistency**
**Feature: agent-rules, Property 9: Override Behavior**
**Feature: agent-rules, Property 10: Size Limit Truncation**
**Validates: Requirements 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion, RuleMatch
from dataagent_core.rules.merger import RuleMerger


def create_rule(
    name: str = "test",
    scope: RuleScope = RuleScope.USER,
    priority: int = 50,
    override: bool = False,
    content: str = "Test content",
) -> Rule:
    """Helper to create test rules."""
    return Rule(
        name=name,
        description="Test rule",
        content=content,
        scope=scope,
        priority=priority,
        override=override,
    )


def create_match(rule: Rule) -> RuleMatch:
    """Helper to create a RuleMatch from a Rule."""
    return RuleMatch(rule=rule, match_reason="test")


class TestRuleMergerBasic:
    """Basic tests for RuleMerger."""

    def test_merge_single_rule(self) -> None:
        """Test merging a single rule."""
        merger = RuleMerger()
        rule = create_rule()
        matches = [create_match(rule)]
        
        final, conflicts = merger.merge_rules(matches)
        
        assert len(final) == 1
        assert final[0] == rule
        assert len(conflicts) == 0

    def test_merge_multiple_rules(self) -> None:
        """Test merging multiple rules."""
        merger = RuleMerger()
        rules = [
            create_rule(name="rule1"),
            create_rule(name="rule2"),
            create_rule(name="rule3"),
        ]
        matches = [create_match(r) for r in rules]
        
        final, conflicts = merger.merge_rules(matches)
        
        assert len(final) == 3
        assert len(conflicts) == 0

    def test_scope_priority_ordering(self) -> None:
        """Test that higher scope takes priority."""
        merger = RuleMerger()
        matches = [
            create_match(create_rule(name="shared", scope=RuleScope.GLOBAL)),
            create_match(create_rule(name="shared", scope=RuleScope.USER)),
            create_match(create_rule(name="shared", scope=RuleScope.PROJECT)),
        ]
        
        final, conflicts = merger.merge_rules(matches)
        
        # Should keep PROJECT (highest priority)
        assert len(final) == 1
        assert final[0].scope == RuleScope.PROJECT
        assert len(conflicts) == 2

    def test_rule_priority_ordering(self) -> None:
        """Test that higher priority rules come first."""
        merger = RuleMerger()
        matches = [
            create_match(create_rule(name="low", priority=30)),
            create_match(create_rule(name="high", priority=80)),
            create_match(create_rule(name="medium", priority=50)),
        ]
        
        final, conflicts = merger.merge_rules(matches)
        
        # Should be sorted by priority (descending)
        assert final[0].name == "high"
        assert final[1].name == "medium"
        assert final[2].name == "low"

    def test_override_behavior(self) -> None:
        """Test that override replaces existing rule."""
        merger = RuleMerger()
        matches = [
            create_match(create_rule(
                name="shared",
                scope=RuleScope.PROJECT,
                content="Project content",
            )),
            create_match(create_rule(
                name="shared",
                scope=RuleScope.USER,
                override=True,
                content="User override content",
            )),
        ]
        
        final, conflicts = merger.merge_rules(matches)
        
        # User rule with override should replace project rule
        assert len(final) == 1
        assert final[0].content == "User override content"


class TestRuleMergerPropertyTests:
    """Property-based tests for RuleMerger."""

    @given(
        scopes=st.lists(
            st.sampled_from([RuleScope.GLOBAL, RuleScope.USER, RuleScope.PROJECT]),
            min_size=2,
            max_size=3,
            unique=True,
        )
    )
    @settings(max_examples=100)
    def test_scope_priority_ordering_property(self, scopes: list[RuleScope]) -> None:
        """
        **Feature: agent-rules, Property 4: Scope Priority Ordering**
        
        For any set of rules with the same name at different scopes,
        merging shall always select the rule from the highest-priority scope.
        """
        merger = RuleMerger()
        
        # Create rules with same name at different scopes
        matches = [
            create_match(create_rule(name="shared", scope=scope))
            for scope in scopes
        ]
        
        final, _ = merger.merge_rules(matches)
        
        # Should keep only one rule
        assert len(final) == 1
        
        # Should be the highest priority scope
        expected_scope = max(scopes, key=lambda s: merger.SCOPE_PRIORITY[s])
        assert final[0].scope == expected_scope

    @given(
        priorities=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=2,
            max_size=10,
            unique=True,
        )
    )
    @settings(max_examples=100)
    def test_priority_ordering_consistency(self, priorities: list[int]) -> None:
        """
        **Feature: agent-rules, Property 8: Priority Ordering Consistency**
        
        For any set of matched rules, the final merged list shall be ordered
        by scope priority (descending), then rule priority (descending),
        then alphabetically by name.
        """
        merger = RuleMerger()
        
        # Create rules with different priorities
        matches = [
            create_match(create_rule(name=f"rule{i}", priority=p))
            for i, p in enumerate(priorities)
        ]
        
        final, _ = merger.merge_rules(matches)
        
        # Verify ordering: higher priority should come first
        for i in range(len(final) - 1):
            # Same scope, so compare by priority
            assert final[i].priority >= final[i + 1].priority or \
                   (final[i].priority == final[i + 1].priority and 
                    final[i].name <= final[i + 1].name)

    @given(
        base_priority=st.integers(min_value=1, max_value=50),
        override_priority=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100)
    def test_override_behavior_property(
        self,
        base_priority: int,
        override_priority: int,
    ) -> None:
        """
        **Feature: agent-rules, Property 9: Override Behavior**
        
        For any rule with override=true, if a lower-priority rule with the
        same name exists, the override rule shall replace it in the final list.
        """
        merger = RuleMerger()
        
        # Higher scope rule (would normally win)
        base_rule = create_rule(
            name="shared",
            scope=RuleScope.PROJECT,
            priority=base_priority,
            content="Base content",
        )
        
        # Lower scope rule with override
        override_rule = create_rule(
            name="shared",
            scope=RuleScope.USER,
            priority=override_priority,
            override=True,
            content="Override content",
        )
        
        matches = [create_match(base_rule), create_match(override_rule)]
        final, conflicts = merger.merge_rules(matches)
        
        # Override rule should win
        assert len(final) == 1
        assert final[0].content == "Override content"
        assert len(conflicts) > 0

    @given(
        num_rules=st.integers(min_value=5, max_value=20),
        content_size=st.integers(min_value=1000, max_value=5000),
        max_size=st.integers(min_value=5000, max_value=20000),
    )
    @settings(max_examples=50)
    def test_size_limit_truncation(
        self,
        num_rules: int,
        content_size: int,
        max_size: int,
    ) -> None:
        """
        **Feature: agent-rules, Property 10: Size Limit Truncation**
        
        For any set of rules whose total content exceeds the max_content_size,
        the merger shall truncate lower-priority rules first while keeping
        higher-priority rules intact.
        """
        merger = RuleMerger(max_content_size=max_size)
        
        # Create rules with varying priorities
        matches = [
            create_match(create_rule(
                name=f"rule{i}",
                priority=100 - i,  # Higher index = lower priority
                content="x" * content_size,
            ))
            for i in range(num_rules)
        ]
        
        final, _ = merger.merge_rules(matches)
        
        # Total size should not exceed limit
        total_size = sum(len(r.content) for r in final)
        assert total_size <= max_size
        
        # Higher priority rules should be kept
        if len(final) > 0:
            # First rule should have highest priority
            assert final[0].priority == 100


class TestPromptGeneration:
    """Tests for prompt section generation."""

    def test_build_prompt_section_empty(self) -> None:
        """Test building prompt with no rules."""
        merger = RuleMerger()
        result = merger.build_prompt_section([])
        assert result == ""

    def test_build_prompt_section_single(self) -> None:
        """Test building prompt with single rule."""
        merger = RuleMerger()
        rule = create_rule(name="test-rule", content="# Test\n\nContent here.")
        
        result = merger.build_prompt_section([rule])
        
        assert "## Agent Rules" in result
        assert "### test-rule" in result
        assert "Content here." in result

    def test_build_prompt_section_multiple(self) -> None:
        """Test building prompt with multiple rules."""
        merger = RuleMerger()
        rules = [
            create_rule(name="rule1", content="Content 1"),
            create_rule(name="rule2", content="Content 2"),
        ]
        
        result = merger.build_prompt_section(rules)
        
        assert "### rule1" in result
        assert "### rule2" in result
        assert "Content 1" in result
        assert "Content 2" in result


class TestConflictDetection:
    """Tests for conflict detection."""

    def test_detect_no_conflicts(self) -> None:
        """Test detection with no conflicts."""
        merger = RuleMerger()
        rules = [
            create_rule(name="rule1"),
            create_rule(name="rule2"),
        ]
        
        conflicts = merger.detect_conflicts(rules)
        assert len(conflicts) == 0

    def test_detect_name_conflict(self) -> None:
        """Test detection of name conflicts."""
        merger = RuleMerger()
        rules = [
            create_rule(name="shared", scope=RuleScope.GLOBAL),
            create_rule(name="shared", scope=RuleScope.USER),
            create_rule(name="unique"),
        ]
        
        conflicts = merger.detect_conflicts(rules)
        
        assert len(conflicts) == 1
        assert conflicts[0]["name"] == "shared"
        assert "global" in conflicts[0]["scopes"]
        assert "user" in conflicts[0]["scopes"]
