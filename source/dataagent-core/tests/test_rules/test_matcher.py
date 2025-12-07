"""Property-based tests for RuleMatcher.

**Feature: agent-rules, Property 5: Always Inclusion Guarantee**
**Feature: agent-rules, Property 6: FileMatch Pattern Correctness**
**Feature: agent-rules, Property 7: Manual Reference Inclusion**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6**
"""

import pytest
from hypothesis import given, strategies as st, settings

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion, RuleMatch
from dataagent_core.rules.matcher import RuleMatcher, MatchContext


def create_rule(
    name: str = "test",
    inclusion: RuleInclusion = RuleInclusion.ALWAYS,
    file_match_pattern: str | None = None,
    enabled: bool = True,
) -> Rule:
    """Helper to create test rules."""
    return Rule(
        name=name,
        description="Test rule",
        content="Test content",
        scope=RuleScope.USER,
        inclusion=inclusion,
        file_match_pattern=file_match_pattern,
        enabled=enabled,
    )


class TestRuleMatcherBasic:
    """Basic tests for RuleMatcher."""

    def test_match_always_rule(self) -> None:
        """Test that always rules are always matched."""
        matcher = RuleMatcher()
        rule = create_rule(inclusion=RuleInclusion.ALWAYS)
        context = MatchContext()
        
        matched, skipped = matcher.match_rules([rule], context)
        
        assert len(matched) == 1
        assert matched[0].rule == rule
        assert "always" in matched[0].match_reason

    def test_match_manual_rule_referenced(self) -> None:
        """Test that manual rules match when referenced."""
        matcher = RuleMatcher()
        rule = create_rule(name="my-rule", inclusion=RuleInclusion.MANUAL)
        context = MatchContext(manual_rules=["my-rule"])
        
        matched, skipped = matcher.match_rules([rule], context)
        
        assert len(matched) == 1
        assert matched[0].rule == rule

    def test_skip_manual_rule_not_referenced(self) -> None:
        """Test that manual rules are skipped when not referenced."""
        matcher = RuleMatcher()
        rule = create_rule(name="my-rule", inclusion=RuleInclusion.MANUAL)
        context = MatchContext(manual_rules=[])
        
        matched, skipped = matcher.match_rules([rule], context)
        
        assert len(matched) == 0
        assert len(skipped) == 1
        assert skipped[0][0] == "my-rule"

    def test_match_file_pattern(self) -> None:
        """Test file pattern matching."""
        matcher = RuleMatcher()
        rule = create_rule(
            inclusion=RuleInclusion.FILE_MATCH,
            file_match_pattern="*.py",
        )
        context = MatchContext(current_files=["main.py", "test.js"])
        
        matched, skipped = matcher.match_rules([rule], context)
        
        assert len(matched) == 1
        assert "main.py" in matched[0].matched_files

    def test_skip_file_pattern_no_match(self) -> None:
        """Test that file pattern rules are skipped when no files match."""
        matcher = RuleMatcher()
        rule = create_rule(
            inclusion=RuleInclusion.FILE_MATCH,
            file_match_pattern="*.py",
        )
        context = MatchContext(current_files=["main.js", "test.ts"])
        
        matched, skipped = matcher.match_rules([rule], context)
        
        assert len(matched) == 0
        assert len(skipped) == 1

    def test_skip_disabled_rule(self) -> None:
        """Test that disabled rules are skipped."""
        matcher = RuleMatcher()
        rule = create_rule(enabled=False)
        context = MatchContext()
        
        matched, skipped = matcher.match_rules([rule], context)
        
        assert len(matched) == 0
        assert len(skipped) == 1
        assert skipped[0][1] == "disabled"


class TestRuleMatcherPropertyTests:
    """Property-based tests for RuleMatcher."""

    @given(
        rule_names=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),
            min_size=1,
            max_size=10,
            unique=True,
        )
    )
    @settings(max_examples=100)
    def test_always_inclusion_guarantee(self, rule_names: list[str]) -> None:
        """
        **Feature: agent-rules, Property 5: Always Inclusion Guarantee**
        
        For any rule with inclusion mode "always", the rule shall be included
        in the matched rules list regardless of the match context.
        """
        matcher = RuleMatcher()
        rules = [
            create_rule(name=name, inclusion=RuleInclusion.ALWAYS)
            for name in rule_names
        ]
        
        # Test with empty context
        context = MatchContext()
        matched, _ = matcher.match_rules(rules, context)
        
        assert len(matched) == len(rules)
        matched_names = {m.rule.name for m in matched}
        assert matched_names == set(rule_names)

    @given(
        pattern=st.sampled_from(["*.py", "*.js", "*.ts", "*.md"]),
        matching_files=st.lists(
            st.sampled_from(["main.py", "test.py", "app.js", "index.ts", "README.md"]),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_file_match_pattern_correctness(
        self,
        pattern: str,
        matching_files: list[str],
    ) -> None:
        """
        **Feature: agent-rules, Property 6: FileMatch Pattern Correctness**
        
        For any rule with inclusion mode "fileMatch" and a glob pattern,
        the rule shall be included if and only if at least one file matches.
        """
        matcher = RuleMatcher()
        rule = create_rule(
            inclusion=RuleInclusion.FILE_MATCH,
            file_match_pattern=pattern,
        )
        context = MatchContext(current_files=matching_files)
        
        matched, _ = matcher.match_rules([rule], context)
        
        # Check if any file matches the pattern
        extension = pattern[1:]  # Remove *
        has_matching_file = any(f.endswith(extension) for f in matching_files)
        
        if has_matching_file:
            assert len(matched) == 1
        else:
            assert len(matched) == 0

    @given(
        rule_name=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),
        referenced=st.booleans(),
    )
    @settings(max_examples=100)
    def test_manual_reference_inclusion(
        self,
        rule_name: str,
        referenced: bool,
    ) -> None:
        """
        **Feature: agent-rules, Property 7: Manual Reference Inclusion**
        
        For any rule with inclusion mode "manual", the rule shall be included
        if and only if its name appears in the manual_rules list.
        """
        matcher = RuleMatcher()
        rule = create_rule(name=rule_name, inclusion=RuleInclusion.MANUAL)
        
        manual_rules = [rule_name] if referenced else []
        context = MatchContext(manual_rules=manual_rules)
        
        matched, _ = matcher.match_rules([rule], context)
        
        if referenced:
            assert len(matched) == 1
            assert matched[0].rule.name == rule_name
        else:
            assert len(matched) == 0


class TestFilePatternMatching:
    """Tests for file pattern matching."""

    def test_match_extension(self) -> None:
        """Test matching by file extension."""
        matcher = RuleMatcher()
        files = matcher._match_files("*.py", ["main.py", "test.js", "utils.py"])
        assert set(files) == {"main.py", "utils.py"}

    def test_match_full_path(self) -> None:
        """Test matching full path patterns."""
        matcher = RuleMatcher()
        files = matcher._match_files("src/*.py", ["src/main.py", "test/main.py"])
        assert files == ["src/main.py"]

    def test_match_filename_only(self) -> None:
        """Test that filename is also checked."""
        matcher = RuleMatcher()
        files = matcher._match_files("*.py", ["src/main.py"])
        assert files == ["src/main.py"]

    def test_match_recursive_pattern(self) -> None:
        """Test recursive ** patterns."""
        matcher = RuleMatcher()
        files = matcher._match_files(
            "src/**/*.py",
            ["src/main.py", "src/utils/helper.py", "test/main.py"],
        )
        assert "src/main.py" in files or "src/utils/helper.py" in files


class TestReferenceExtraction:
    """Tests for reference extraction."""

    def test_extract_manual_references(self) -> None:
        """Test extracting @rulename references."""
        matcher = RuleMatcher()
        text = "Please use @coding-standards and @security-review for this."
        refs = matcher.extract_manual_references(text)
        assert set(refs) == {"coding-standards", "security-review"}

    def test_extract_file_references_backticks(self) -> None:
        """Test extracting backtick-quoted file paths."""
        matcher = RuleMatcher()
        text = "Check `src/main.py` and `test/utils.ts` for examples."
        files = matcher.extract_file_references(text)
        assert "src/main.py" in files
        assert "test/utils.ts" in files

    def test_extract_file_references_prefix(self) -> None:
        """Test extracting file: prefixed paths."""
        matcher = RuleMatcher()
        text = "See file:src/main.py for details."
        files = matcher.extract_file_references(text)
        assert "src/main.py" in files
