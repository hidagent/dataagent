"""Unit tests for RuleStore implementations.

Tests for FileRuleStore and MemoryRuleStore.
**Validates: Requirements 2.1, 2.2, 2.3, 2.6**
"""

import pytest
import tempfile
from pathlib import Path

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion
from dataagent_core.rules.store import FileRuleStore, MemoryRuleStore


def create_test_rule(
    name: str = "test-rule",
    scope: RuleScope = RuleScope.USER,
    **kwargs,
) -> Rule:
    """Helper to create test rules."""
    defaults = {
        "description": "Test rule description",
        "content": "# Test Rule\n\nThis is test content.",
    }
    defaults.update(kwargs)
    return Rule(name=name, scope=scope, **defaults)


class TestMemoryRuleStore:
    """Tests for MemoryRuleStore."""

    def test_save_and_get_rule(self) -> None:
        """Test saving and retrieving a rule."""
        store = MemoryRuleStore()
        rule = create_test_rule()
        
        store.save_rule(rule)
        retrieved = store.get_rule("test-rule", RuleScope.USER)
        
        assert retrieved is not None
        assert retrieved.name == "test-rule"
        assert retrieved.description == "Test rule description"

    def test_list_rules(self) -> None:
        """Test listing all rules."""
        store = MemoryRuleStore()
        store.save_rule(create_test_rule("rule1", RuleScope.USER))
        store.save_rule(create_test_rule("rule2", RuleScope.PROJECT))
        store.save_rule(create_test_rule("rule3", RuleScope.GLOBAL))
        
        all_rules = store.list_rules()
        assert len(all_rules) == 3

    def test_list_rules_by_scope(self) -> None:
        """Test listing rules filtered by scope."""
        store = MemoryRuleStore()
        store.save_rule(create_test_rule("rule1", RuleScope.USER))
        store.save_rule(create_test_rule("rule2", RuleScope.USER))
        store.save_rule(create_test_rule("rule3", RuleScope.PROJECT))
        
        user_rules = store.list_rules(RuleScope.USER)
        assert len(user_rules) == 2
        
        project_rules = store.list_rules(RuleScope.PROJECT)
        assert len(project_rules) == 1

    def test_delete_rule(self) -> None:
        """Test deleting a rule."""
        store = MemoryRuleStore()
        rule = create_test_rule()
        store.save_rule(rule)
        
        assert store.get_rule("test-rule", RuleScope.USER) is not None
        
        result = store.delete_rule("test-rule", RuleScope.USER)
        assert result is True
        assert store.get_rule("test-rule", RuleScope.USER) is None

    def test_delete_nonexistent_rule(self) -> None:
        """Test deleting a rule that doesn't exist."""
        store = MemoryRuleStore()
        result = store.delete_rule("nonexistent", RuleScope.USER)
        assert result is False

    def test_get_rule_priority_order(self) -> None:
        """Test that get_rule returns highest priority scope first."""
        store = MemoryRuleStore()
        store.save_rule(create_test_rule("shared", RuleScope.GLOBAL, description="Global"))
        store.save_rule(create_test_rule("shared", RuleScope.USER, description="User"))
        store.save_rule(create_test_rule("shared", RuleScope.PROJECT, description="Project"))
        
        # Without scope, should return project (highest priority)
        rule = store.get_rule("shared")
        assert rule is not None
        assert rule.description == "Project"

    def test_rule_exists(self) -> None:
        """Test rule_exists method."""
        store = MemoryRuleStore()
        store.save_rule(create_test_rule())
        
        assert store.rule_exists("test-rule", RuleScope.USER) is True
        assert store.rule_exists("nonexistent", RuleScope.USER) is False

    def test_clear(self) -> None:
        """Test clearing all rules."""
        store = MemoryRuleStore()
        store.save_rule(create_test_rule("rule1"))
        store.save_rule(create_test_rule("rule2"))
        
        store.clear()
        assert len(store.list_rules()) == 0


class TestFileRuleStore:
    """Tests for FileRuleStore."""

    def test_save_and_load_rule(self) -> None:
        """Test saving a rule to file and loading it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            store = FileRuleStore(user_dir=user_dir)
            
            rule = create_test_rule()
            store.save_rule(rule)
            
            # Verify file was created
            file_path = user_dir / "test-rule.md"
            assert file_path.exists()
            
            # Reload and verify
            store.reload()
            retrieved = store.get_rule("test-rule", RuleScope.USER)
            
            assert retrieved is not None
            assert retrieved.name == "test-rule"
            assert retrieved.description == "Test rule description"

    def test_directory_creation(self) -> None:
        """Test that directories are created automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "nested" / "user" / "rules"
            store = FileRuleStore(user_dir=user_dir)
            
            rule = create_test_rule()
            store.save_rule(rule)
            
            assert user_dir.exists()
            assert (user_dir / "test-rule.md").exists()

    def test_load_multiple_scopes(self) -> None:
        """Test loading rules from multiple scope directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_dir = Path(tmpdir) / "global"
            user_dir = Path(tmpdir) / "user"
            project_dir = Path(tmpdir) / "project"
            
            store = FileRuleStore(
                global_dir=global_dir,
                user_dir=user_dir,
                project_dir=project_dir,
            )
            
            # Save rules to different scopes
            store.save_rule(create_test_rule("global-rule", RuleScope.GLOBAL))
            store.save_rule(create_test_rule("user-rule", RuleScope.USER))
            store.save_rule(create_test_rule("project-rule", RuleScope.PROJECT))
            
            # Reload and verify
            store.reload()
            
            assert len(store.list_rules()) == 3
            assert len(store.list_rules(RuleScope.GLOBAL)) == 1
            assert len(store.list_rules(RuleScope.USER)) == 1
            assert len(store.list_rules(RuleScope.PROJECT)) == 1

    def test_delete_rule_file(self) -> None:
        """Test that deleting a rule removes the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            store = FileRuleStore(user_dir=user_dir)
            
            rule = create_test_rule()
            store.save_rule(rule)
            
            file_path = user_dir / "test-rule.md"
            assert file_path.exists()
            
            result = store.delete_rule("test-rule", RuleScope.USER)
            assert result is True
            assert not file_path.exists()

    def test_reload_picks_up_external_changes(self) -> None:
        """Test that reload picks up files added externally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            user_dir.mkdir(parents=True)
            
            store = FileRuleStore(user_dir=user_dir)
            store.reload()
            
            assert len(store.list_rules()) == 0
            
            # Add a file externally
            rule_file = user_dir / "external.md"
            rule_file.write_text("""---
name: external
description: Externally added rule
---

Content.
""")
            
            # Reload should pick it up
            store.reload()
            assert len(store.list_rules()) == 1
            assert store.get_rule("external", RuleScope.USER) is not None

    def test_caching_behavior(self) -> None:
        """Test that rules are cached after first load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            store = FileRuleStore(user_dir=user_dir)
            
            rule = create_test_rule()
            store.save_rule(rule)
            
            # First access triggers load
            rules1 = store.list_rules()
            assert len(rules1) == 1
            
            # Second access uses cache (no reload)
            rules2 = store.list_rules()
            assert len(rules2) == 1

    def test_save_rule_with_all_options(self) -> None:
        """Test saving a rule with all optional fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            store = FileRuleStore(user_dir=user_dir)
            
            rule = Rule(
                name="full-rule",
                description="Rule with all options",
                content="# Full Rule\n\nContent here.",
                scope=RuleScope.USER,
                inclusion=RuleInclusion.FILE_MATCH,
                file_match_pattern="*.py",
                priority=80,
                override=True,
                enabled=False,
            )
            store.save_rule(rule)
            
            # Reload and verify all fields
            store.reload()
            retrieved = store.get_rule("full-rule", RuleScope.USER)
            
            assert retrieved is not None
            assert retrieved.inclusion == RuleInclusion.FILE_MATCH
            assert retrieved.file_match_pattern == "*.py"
            assert retrieved.priority == 80
            assert retrieved.override is True
            assert retrieved.enabled is False

    def test_get_rule_path(self) -> None:
        """Test getting the file path for a rule."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            store = FileRuleStore(user_dir=user_dir)
            
            path = store.get_rule_path("test", RuleScope.USER)
            assert path == user_dir / "test.md"

    def test_save_without_configured_dir(self) -> None:
        """Test that saving to unconfigured scope raises error."""
        store = FileRuleStore()  # No directories configured
        rule = create_test_rule()
        
        with pytest.raises(ValueError, match="No directory configured"):
            store.save_rule(rule)

    def test_invalid_rule_file_skipped(self) -> None:
        """Test that invalid rule files are skipped during load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir) / "user"
            user_dir.mkdir(parents=True)
            
            # Create a valid rule
            valid_file = user_dir / "valid.md"
            valid_file.write_text("""---
name: valid
description: Valid rule
---

Content.
""")
            
            # Create an invalid rule (missing description)
            invalid_file = user_dir / "invalid.md"
            invalid_file.write_text("""---
name: invalid
---

Content.
""")
            
            store = FileRuleStore(user_dir=user_dir)
            store.reload()
            
            # Only valid rule should be loaded
            rules = store.list_rules()
            assert len(rules) == 1
            assert rules[0].name == "valid"
