"""Property-based tests for Rule models.

**Feature: agent-rules, Property 1: Rule Parsing Round Trip**
**Feature: agent-rules, Property 12: Rule Serialization Completeness**
**Validates: Requirements 1.1, 10.1, 10.2, 10.5**
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings

from dataagent_core.rules.models import (
    Rule,
    RuleScope,
    RuleInclusion,
    RuleMatch,
    RuleEvaluationTrace,
)


# Strategies for generating test data
rule_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() != "")

rule_description_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != "")

rule_content_strategy = st.text(min_size=0, max_size=1000)

rule_scope_strategy = st.sampled_from(list(RuleScope))

rule_inclusion_strategy = st.sampled_from(list(RuleInclusion))

priority_strategy = st.integers(min_value=1, max_value=100)

file_pattern_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=50).map(lambda x: f"*.{x}" if x else None),
)


@st.composite
def rule_strategy(draw: st.DrawFn) -> Rule:
    """Generate a random valid Rule."""
    return Rule(
        name=draw(rule_name_strategy),
        description=draw(rule_description_strategy),
        content=draw(rule_content_strategy),
        scope=draw(rule_scope_strategy),
        inclusion=draw(rule_inclusion_strategy),
        file_match_pattern=draw(file_pattern_strategy),
        priority=draw(priority_strategy),
        override=draw(st.booleans()),
        enabled=draw(st.booleans()),
        source_path=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        metadata=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=0, max_size=50),
            max_size=5,
        )),
    )


class TestRuleModel:
    """Tests for Rule model."""

    def test_rule_creation_basic(self) -> None:
        """Test basic rule creation."""
        rule = Rule(
            name="test-rule",
            description="A test rule",
            content="# Test\nThis is a test rule.",
            scope=RuleScope.USER,
        )
        assert rule.name == "test-rule"
        assert rule.description == "A test rule"
        assert rule.scope == RuleScope.USER
        assert rule.inclusion == RuleInclusion.ALWAYS
        assert rule.priority == 50
        assert rule.enabled is True

    def test_rule_validation_empty_name(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Rule(
                name="",
                description="Test",
                content="Content",
                scope=RuleScope.USER,
            )

    def test_rule_validation_empty_description(self) -> None:
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            Rule(
                name="test",
                description="",
                content="Content",
                scope=RuleScope.USER,
            )

    def test_rule_validation_invalid_priority(self) -> None:
        """Test that invalid priority raises ValueError."""
        with pytest.raises(ValueError, match="Priority must be between"):
            Rule(
                name="test",
                description="Test",
                content="Content",
                scope=RuleScope.USER,
                priority=0,
            )
        with pytest.raises(ValueError, match="Priority must be between"):
            Rule(
                name="test",
                description="Test",
                content="Content",
                scope=RuleScope.USER,
                priority=101,
            )

    @given(rule=rule_strategy())
    @settings(max_examples=100)
    def test_rule_serialization_round_trip(self, rule: Rule) -> None:
        """
        **Feature: agent-rules, Property 1: Rule Parsing Round Trip**
        
        For any valid Rule object, serializing it to a dictionary and then
        deserializing it back should produce an equivalent Rule object.
        """
        # Serialize to dict
        rule_dict = rule.to_dict()
        
        # Deserialize back
        restored_rule = Rule.from_dict(rule_dict)
        
        # Verify all fields match
        assert restored_rule.name == rule.name
        assert restored_rule.description == rule.description
        assert restored_rule.content == rule.content
        assert restored_rule.scope == rule.scope
        assert restored_rule.inclusion == rule.inclusion
        assert restored_rule.file_match_pattern == rule.file_match_pattern
        assert restored_rule.priority == rule.priority
        assert restored_rule.override == rule.override
        assert restored_rule.enabled == rule.enabled
        assert restored_rule.source_path == rule.source_path
        assert restored_rule.metadata == rule.metadata

    @given(rule=rule_strategy())
    @settings(max_examples=100)
    def test_rule_to_dict_completeness(self, rule: Rule) -> None:
        """
        **Feature: agent-rules, Property 12: Rule Serialization Completeness**
        
        For any Rule object, serializing to JSON should include all fields.
        """
        rule_dict = rule.to_dict()
        
        # Verify all expected keys are present
        expected_keys = {
            "name", "description", "content", "scope", "inclusion",
            "file_match_pattern", "priority", "override", "enabled",
            "source_path", "created_at", "updated_at", "metadata"
        }
        assert set(rule_dict.keys()) == expected_keys

    def test_rule_equality(self) -> None:
        """Test rule equality based on name and scope."""
        rule1 = Rule(
            name="test",
            description="Test 1",
            content="Content 1",
            scope=RuleScope.USER,
        )
        rule2 = Rule(
            name="test",
            description="Test 2",
            content="Content 2",
            scope=RuleScope.USER,
        )
        rule3 = Rule(
            name="test",
            description="Test 3",
            content="Content 3",
            scope=RuleScope.PROJECT,
        )
        
        assert rule1 == rule2  # Same name and scope
        assert rule1 != rule3  # Different scope

    def test_rule_hash(self) -> None:
        """Test rule hashing for use in sets/dicts."""
        rule1 = Rule(
            name="test",
            description="Test",
            content="Content",
            scope=RuleScope.USER,
        )
        rule2 = Rule(
            name="test",
            description="Different",
            content="Different",
            scope=RuleScope.USER,
        )
        
        # Same name and scope should have same hash
        assert hash(rule1) == hash(rule2)
        
        # Can be used in sets
        rule_set = {rule1, rule2}
        assert len(rule_set) == 1


class TestRuleMatch:
    """Tests for RuleMatch model."""

    def test_rule_match_creation(self) -> None:
        """Test RuleMatch creation."""
        rule = Rule(
            name="test",
            description="Test",
            content="Content",
            scope=RuleScope.USER,
        )
        match = RuleMatch(
            rule=rule,
            match_reason="always included",
            matched_files=["test.py"],
        )
        assert match.rule == rule
        assert match.match_reason == "always included"
        assert match.matched_files == ["test.py"]

    def test_rule_match_to_dict(self) -> None:
        """Test RuleMatch serialization."""
        rule = Rule(
            name="test",
            description="Test",
            content="Content",
            scope=RuleScope.USER,
        )
        match = RuleMatch(
            rule=rule,
            match_reason="file pattern matched",
            matched_files=["src/main.py", "src/utils.py"],
        )
        
        match_dict = match.to_dict()
        assert match_dict["rule_name"] == "test"
        assert match_dict["rule_scope"] == "user"
        assert match_dict["match_reason"] == "file pattern matched"
        assert match_dict["matched_files"] == ["src/main.py", "src/utils.py"]


class TestRuleEvaluationTrace:
    """Tests for RuleEvaluationTrace model."""

    def test_trace_creation(self) -> None:
        """Test RuleEvaluationTrace creation."""
        trace = RuleEvaluationTrace(
            request_id="req-123",
            timestamp=datetime.now(),
            evaluated_rules=["rule1", "rule2"],
            matched_rules=[],
            skipped_rules=[("rule2", "disabled")],
            conflicts=[],
            final_rules=["rule1"],
            total_content_size=100,
        )
        assert trace.request_id == "req-123"
        assert len(trace.evaluated_rules) == 2
        assert len(trace.skipped_rules) == 1

    def test_trace_to_dict(self) -> None:
        """Test RuleEvaluationTrace serialization."""
        rule = Rule(
            name="test",
            description="Test",
            content="Content",
            scope=RuleScope.USER,
        )
        match = RuleMatch(rule=rule, match_reason="always")
        
        trace = RuleEvaluationTrace(
            request_id="req-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            evaluated_rules=["test"],
            matched_rules=[match],
            skipped_rules=[],
            conflicts=[("rule1", "rule2", "duplicate name")],
            final_rules=["test"],
            total_content_size=100,
        )
        
        trace_dict = trace.to_dict()
        assert trace_dict["request_id"] == "req-123"
        assert "2024-01-01" in trace_dict["timestamp"]
        assert len(trace_dict["matched_rules"]) == 1
        assert len(trace_dict["conflicts"]) == 1
        assert trace_dict["conflicts"][0]["reason"] == "duplicate name"
