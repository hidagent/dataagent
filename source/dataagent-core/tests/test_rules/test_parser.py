"""Property-based tests for RuleParser.

**Feature: agent-rules, Property 2: Frontmatter Extraction Completeness**
**Feature: agent-rules, Property 3: Invalid Frontmatter Handling**
**Feature: agent-rules, Property 11: Path Safety Validation**
**Validates: Requirements 1.1, 1.2, 1.4, 1.5, 12.1, 12.2**
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from dataagent_core.rules.models import RuleScope, RuleInclusion
from dataagent_core.rules.parser import RuleParser, RuleParseError, MAX_RULE_FILE_SIZE


class TestRuleParserBasic:
    """Basic tests for RuleParser."""

    def test_parse_valid_rule(self) -> None:
        """Test parsing a valid rule file content."""
        parser = RuleParser()
        content = """---
name: test-rule
description: A test rule for validation
inclusion: always
priority: 60
---

# Test Rule

This is the rule content.
"""
        rule = parser.parse_content(content, RuleScope.USER)
        
        assert rule.name == "test-rule"
        assert rule.description == "A test rule for validation"
        assert rule.inclusion == RuleInclusion.ALWAYS
        assert rule.priority == 60
        assert "# Test Rule" in rule.content

    def test_parse_minimal_rule(self) -> None:
        """Test parsing a rule with only required fields."""
        parser = RuleParser()
        content = """---
name: minimal
description: Minimal rule
---

Content here.
"""
        rule = parser.parse_content(content, RuleScope.GLOBAL)
        
        assert rule.name == "minimal"
        assert rule.description == "Minimal rule"
        assert rule.inclusion == RuleInclusion.ALWAYS  # default
        assert rule.priority == 50  # default
        assert rule.enabled is True  # default

    def test_parse_file_match_rule(self) -> None:
        """Test parsing a rule with fileMatch inclusion."""
        parser = RuleParser()
        content = """---
name: python-rules
description: Rules for Python files
inclusion: fileMatch
fileMatchPattern: "*.py"
priority: 70
---

Follow PEP 8.
"""
        rule = parser.parse_content(content, RuleScope.PROJECT)
        
        assert rule.name == "python-rules"
        assert rule.inclusion == RuleInclusion.FILE_MATCH
        assert rule.file_match_pattern == "*.py"

    def test_parse_manual_rule(self) -> None:
        """Test parsing a rule with manual inclusion."""
        parser = RuleParser()
        content = """---
name: security-review
description: Security review checklist
inclusion: manual
priority: 90
---

Security checklist...
"""
        rule = parser.parse_content(content, RuleScope.USER)
        
        assert rule.inclusion == RuleInclusion.MANUAL
        assert rule.priority == 90


class TestRuleParserErrors:
    """Tests for RuleParser error handling."""

    def test_missing_frontmatter(self) -> None:
        """Test that missing frontmatter raises error."""
        parser = RuleParser()
        content = "# No frontmatter\nJust content."
        
        with pytest.raises(RuleParseError, match="Missing or invalid YAML frontmatter"):
            parser.parse_content(content, RuleScope.USER)

    def test_missing_name(self) -> None:
        """Test that missing name raises error."""
        parser = RuleParser()
        content = """---
description: No name field
---

Content.
"""
        with pytest.raises(RuleParseError, match="Missing required field: name"):
            parser.parse_content(content, RuleScope.USER)

    def test_missing_description(self) -> None:
        """Test that missing description raises error."""
        parser = RuleParser()
        content = """---
name: no-description
---

Content.
"""
        with pytest.raises(RuleParseError, match="Missing required field: description"):
            parser.parse_content(content, RuleScope.USER)

    def test_empty_name(self) -> None:
        """Test that empty name raises error."""
        parser = RuleParser()
        content = """---
name: 
description: Has empty name
---

Content.
"""
        with pytest.raises(RuleParseError, match="Missing required field: name"):
            parser.parse_content(content, RuleScope.USER)


class TestRuleParserPropertyTests:
    """Property-based tests for RuleParser."""

    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        description=st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != ""),
        content=st.text(min_size=0, max_size=500),
        inclusion=st.sampled_from(["always", "fileMatch", "manual"]),
        priority=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_frontmatter_extraction_completeness(
        self,
        name: str,
        description: str,
        content: str,
        inclusion: str,
        priority: int,
    ) -> None:
        """
        **Feature: agent-rules, Property 2: Frontmatter Extraction Completeness**
        
        For any rule file with valid YAML frontmatter containing name, description,
        and optional fields, parsing should extract all specified fields correctly.
        """
        # Skip if name or description contain problematic YAML characters
        # or have leading/trailing whitespace (YAML strips these)
        yaml_special_chars = ':\n"\'#[]{}|>&*!%@`'
        assume(not any(c in name for c in yaml_special_chars))
        assume(not any(c in description for c in yaml_special_chars))
        assume(name == name.strip())
        assume(description == description.strip())
        
        parser = RuleParser()
        rule_content = f"""---
name: {name}
description: {description}
inclusion: {inclusion}
priority: {priority}
---

{content}
"""
        rule = parser.parse_content(rule_content, RuleScope.USER)
        
        assert rule.name == name
        assert rule.description == description
        assert rule.inclusion.value == inclusion
        assert rule.priority == priority

    @given(
        invalid_content=st.one_of(
            # No frontmatter at all
            st.text(min_size=1, max_size=100).filter(lambda x: "---" not in x),
            # Only opening delimiter
            st.text(min_size=1, max_size=100).map(lambda x: f"---\n{x}"),
            # Empty frontmatter with missing fields
            st.just("---\n---\nContent"),
            # Only name, missing description
            st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != "").map(
                lambda x: f"---\nname: {x}\n---\nContent"
            ),
        )
    )
    @settings(max_examples=50)
    def test_invalid_frontmatter_handling(self, invalid_content: str) -> None:
        """
        **Feature: agent-rules, Property 3: Invalid Frontmatter Handling**
        
        For any rule file with invalid YAML frontmatter, the parser should
        raise RuleParseError without crashing.
        """
        parser = RuleParser()
        
        with pytest.raises(RuleParseError):
            parser.parse_content(invalid_content, RuleScope.USER)


class TestPathSafetyValidation:
    """Tests for path safety validation."""

    def test_safe_path_within_allowed_dir(self) -> None:
        """Test that paths within allowed directories are safe."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            allowed = [base]
            
            safe_path = base / "subdir" / "file.md"
            assert parser._is_safe_path(safe_path, allowed) is True

    def test_unsafe_path_outside_allowed_dir(self) -> None:
        """Test that paths outside allowed directories are blocked."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            allowed = [base / "allowed"]
            
            unsafe_path = base / "other" / "file.md"
            assert parser._is_safe_path(unsafe_path, allowed) is False

    def test_path_traversal_blocked(self) -> None:
        """
        **Feature: agent-rules, Property 11: Path Safety Validation**
        
        Test that path traversal attempts are blocked.
        """
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            allowed_dir = base / "allowed"
            allowed_dir.mkdir()
            allowed = [allowed_dir]
            
            # Attempt path traversal
            traversal_path = allowed_dir / ".." / "secret" / "file.md"
            assert parser._is_safe_path(traversal_path, allowed) is False

    @given(
        subpath=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-/"),
            min_size=1,
            max_size=50,
        ).filter(lambda x: ".." not in x and x.strip() != "")
    )
    @settings(max_examples=50)
    def test_safe_subpaths(self, subpath: str) -> None:
        """Test that valid subpaths within allowed dirs are safe."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            allowed = [base]
            
            # Clean up the subpath
            clean_subpath = subpath.strip("/")
            if clean_subpath:
                safe_path = base / clean_subpath / "file.md"
                assert parser._is_safe_path(safe_path, allowed) is True


class TestFileReferenceResolution:
    """Tests for file reference resolution."""

    def test_resolve_valid_reference(self) -> None:
        """Test resolving a valid file reference."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Create a referenced file
            ref_file = base / "included.md"
            ref_file.write_text("Included content here.")
            
            content = "Before #[[file:included.md]] After"
            resolved = parser.resolve_file_references(content, base, [base])
            
            assert "Included content here." in resolved
            assert "#[[file:" not in resolved

    def test_resolve_missing_reference(self) -> None:
        """Test resolving a reference to a missing file."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            content = "Before #[[file:missing.md]] After"
            resolved = parser.resolve_file_references(content, base, [base])
            
            assert "[File not found: missing.md]" in resolved

    def test_resolve_blocked_reference(self) -> None:
        """Test that references outside allowed dirs are blocked."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            allowed = base / "allowed"
            allowed.mkdir()
            
            # Create file outside allowed dir
            outside = base / "outside.md"
            outside.write_text("Secret content")
            
            content = "Before #[[file:../outside.md]] After"
            resolved = parser.resolve_file_references(content, allowed, [allowed])
            
            assert "[File reference blocked:" in resolved
            assert "Secret content" not in resolved


class TestValidation:
    """Tests for content validation."""

    def test_validate_valid_content(self) -> None:
        """Test validation of valid content."""
        parser = RuleParser()
        content = """---
name: valid
description: Valid rule
---

Content.
"""
        is_valid, errors, warnings = parser.validate_content(content)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_content(self) -> None:
        """Test validation of invalid content."""
        parser = RuleParser()
        content = """---
name: 
---

Content.
"""
        is_valid, errors, warnings = parser.validate_content(content)
        
        assert is_valid is False
        assert any("name" in e for e in errors)

    def test_validate_with_warnings(self) -> None:
        """Test validation that produces warnings."""
        parser = RuleParser()
        content = """---
name: test
description: Test
inclusion: unknown_mode
priority: 150
---

Content.
"""
        is_valid, errors, warnings = parser.validate_content(content)
        
        assert is_valid is True  # Still valid, just has warnings
        assert len(warnings) > 0


class TestParseFile:
    """Tests for parsing from files."""

    def test_parse_existing_file(self) -> None:
        """Test parsing an existing rule file."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "rule.md"
            file_path.write_text("""---
name: file-rule
description: Rule from file
---

File content.
""")
            rule = parser.parse_file(file_path, RuleScope.PROJECT)
            
            assert rule is not None
            assert rule.name == "file-rule"
            assert rule.source_path == str(file_path)

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a nonexistent file returns None."""
        parser = RuleParser()
        
        result = parser.parse_file(Path("/nonexistent/file.md"), RuleScope.USER)
        assert result is None

    def test_parse_oversized_file(self) -> None:
        """Test that oversized files raise error."""
        parser = RuleParser()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "large.md"
            # Create a file larger than the limit
            file_path.write_text("x" * (MAX_RULE_FILE_SIZE + 1))
            
            with pytest.raises(RuleParseError, match="exceeds size limit"):
                parser.parse_file(file_path, RuleScope.USER)
