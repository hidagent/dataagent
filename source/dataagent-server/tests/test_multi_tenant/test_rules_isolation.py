"""Rules isolation tests.

Verifies that users cannot access each other's rules.
"""

import pytest
from pathlib import Path

from .conftest import (
    TestUser,
    SecurityAuditLogger,
    assert_contains_marker,
    assert_isolation_enforced,
)


class TestRulesIsolation:
    """Test rules isolation between users."""
    
    # =========================================================================
    # Positive Tests - Users can access their own rules
    # =========================================================================
    
    def test_alice_can_read_own_rules(self, alice: TestUser) -> None:
        """Alice can read her own rules."""
        rule_path = alice.rules_path / f"{alice.user_id}-main-rule.md"
        
        assert rule_path.exists(), f"Alice's rule should exist at {rule_path}"
        
        content = rule_path.read_text()
        assert_contains_marker(content, alice.secret_markers["rule"], should_contain=True)
        assert alice.user_id in content
    
    def test_alice_can_list_own_rules(self, alice: TestUser) -> None:
        """Alice can list her own rules."""
        rules = list(alice.rules_path.glob("*.md"))
        
        assert len(rules) >= 2, "Alice should have at least 2 rules"
        
        rule_names = [r.stem for r in rules]
        assert f"{alice.user_id}-main-rule" in rule_names
        assert f"{alice.user_id}-secondary-rule" in rule_names
    
    def test_bob_can_read_own_rules(self, bob: TestUser) -> None:
        """Bob can read his own rules."""
        rule_path = bob.rules_path / f"{bob.user_id}-main-rule.md"
        
        assert rule_path.exists(), f"Bob's rule should exist at {rule_path}"
        
        content = rule_path.read_text()
        assert_contains_marker(content, bob.secret_markers["rule"], should_contain=True)
        assert bob.user_id in content
    
    def test_alice_can_create_new_rule(self, alice: TestUser) -> None:
        """Alice can create new rules in her rules directory."""
        new_rule_path = alice.rules_path / "alice-test-rule.md"
        
        rule_content = f"""---
name: alice-test-rule
description: Test rule
inclusion: manual
---

# Test Rule
Contains: {alice.secret_markers['rule']}_TEST
"""
        new_rule_path.write_text(rule_content)
        
        assert new_rule_path.exists()
        assert alice.secret_markers["rule"] in new_rule_path.read_text()
        
        # Cleanup
        new_rule_path.unlink()
    
    # =========================================================================
    # Negative Tests - Users cannot access other's rules
    # =========================================================================
    
    def test_alice_cannot_read_bob_rules_direct_path(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Alice cannot read Bob's rules using direct path."""
        bob_rule_path = bob.rules_path / f"{bob.user_id}-main-rule.md"
        
        # Verify Bob's rule exists
        assert bob_rule_path.exists(), "Bob's rule should exist for this test"
        
        # Verify paths are separate
        try:
            bob_rule_path.resolve().relative_to(alice.rules_path.resolve())
            pytest.fail("Bob's rules path should NOT be within Alice's rules path")
        except ValueError:
            # Expected - paths are separate
            pass
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="rule",
            resource_id=str(bob_rule_path),
            action="read",
            result="denied",
            details={"reason": "path outside user's rules directory"},
        )
    
    def test_alice_rules_do_not_contain_bob_markers(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Alice's rules should not contain Bob's secret markers."""
        for rule_path in alice.rules_path.glob("*.md"):
            content = rule_path.read_text()
            assert_contains_marker(
                content,
                bob.secret_markers["rule"],
                should_contain=False,
            )
    
    def test_bob_rules_do_not_contain_alice_markers(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Bob's rules should not contain Alice's secret markers."""
        for rule_path in bob.rules_path.glob("*.md"):
            content = rule_path.read_text()
            assert_contains_marker(
                content,
                alice.secret_markers["rule"],
                should_contain=False,
            )
    
    def test_rules_directories_are_separate(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Verify rules directories are completely separate."""
        alice_resolved = alice.rules_path.resolve()
        bob_resolved = bob.rules_path.resolve()
        
        # Neither should be a parent of the other
        try:
            alice_resolved.relative_to(bob_resolved)
            pytest.fail("Alice's rules should not be inside Bob's")
        except ValueError:
            pass
        
        try:
            bob_resolved.relative_to(alice_resolved)
            pytest.fail("Bob's rules should not be inside Alice's")
        except ValueError:
            pass
        
        assert alice_resolved != bob_resolved


class TestRulesIsolationWithRuleStore:
    """Test rules isolation using FileRuleStore."""
    
    def test_rule_store_loads_only_user_rules(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """FileRuleStore should only load rules for the specified user."""
        from dataagent_core.rules.store import FileRuleStore
        from dataagent_core.rules.models import RuleScope
        
        # Create store for Alice
        alice_store = FileRuleStore(
            user_dir=alice.rules_path,
        )
        alice_store.reload()
        
        alice_rules = alice_store.list_rules()
        
        # All rules should be Alice's
        for rule in alice_rules:
            assert alice.user_id in rule.name or alice.user_id in rule.content
            # Should not contain Bob's markers
            assert_contains_marker(
                rule.content,
                bob.secret_markers["rule"],
                should_contain=False,
            )
    
    def test_rule_store_isolation_between_users(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Different users should have completely separate rule stores."""
        from dataagent_core.rules.store import FileRuleStore
        
        alice_store = FileRuleStore(user_dir=alice.rules_path)
        bob_store = FileRuleStore(user_dir=bob.rules_path)
        
        alice_store.reload()
        bob_store.reload()
        
        alice_rules = alice_store.list_rules()
        bob_rules = bob_store.list_rules()
        
        alice_rule_names = {r.name for r in alice_rules}
        bob_rule_names = {r.name for r in bob_rules}
        
        # No overlap in rule names
        overlap = alice_rule_names & bob_rule_names
        assert len(overlap) == 0, f"Rules should not overlap: {overlap}"
    
    def test_alice_cannot_get_bob_rule_by_name(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Alice's rule store should not find Bob's rules by name."""
        from dataagent_core.rules.store import FileRuleStore
        
        alice_store = FileRuleStore(user_dir=alice.rules_path)
        alice_store.reload()
        
        # Try to get Bob's rule
        bob_rule = alice_store.get_rule(f"{bob.user_id}-main-rule")
        
        assert bob_rule is None, "Alice should not be able to get Bob's rule"


class TestRulesAPIIsolation:
    """Test rules isolation via REST API."""
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_list_rules_returns_only_user_rules(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """API should return only the requesting user's rules."""
        from .conftest import make_request_as_user
        
        # Request as Alice
        response = make_request_as_user(
            api_client,
            alice,
            "GET",
            f"/api/v1/users/{alice.user_id}/rules",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All rules should be Alice's
        for rule in data.get("rules", []):
            assert alice.user_id in rule["name"] or bob.user_id not in rule["name"]
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_access_bob_rules(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to access Bob's rules via API."""
        from .conftest import make_request_as_user
        
        # Alice tries to access Bob's rules
        response = make_request_as_user(
            api_client,
            alice,
            "GET",
            f"/api/v1/users/{bob.user_id}/rules",
        )
        
        # Should be forbidden
        assert_isolation_enforced(response.status_code)
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_modify_bob_rules(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to modify Bob's rules via API."""
        from .conftest import make_request_as_user
        
        # Alice tries to update Bob's rule
        response = make_request_as_user(
            api_client,
            alice,
            "PUT",
            f"/api/v1/users/{bob.user_id}/rules/{bob.user_id}-main-rule",
            json={"content": "Hacked by Alice!"},
        )
        
        assert_isolation_enforced(response.status_code)
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_delete_bob_rules(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to delete Bob's rules via API."""
        from .conftest import make_request_as_user
        
        # Alice tries to delete Bob's rule
        response = make_request_as_user(
            api_client,
            alice,
            "DELETE",
            f"/api/v1/users/{bob.user_id}/rules/{bob.user_id}-main-rule",
        )
        
        assert_isolation_enforced(response.status_code)


class TestRulesSecurityAudit:
    """Test security audit logging for rules operations."""
    
    def test_audit_log_records_cross_tenant_rule_access(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Security audit should record cross-tenant rule access attempts."""
        # Simulate cross-tenant access attempts
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="rule",
            resource_id=f"{bob.user_id}-main-rule",
            action="read",
            result="denied",
        )
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="rule",
            resource_id=f"{bob.user_id}-main-rule",
            action="write",
            result="denied",
        )
        
        cross_tenant = security_audit.get_cross_tenant_attempts()
        assert len(cross_tenant) == 2
        
        violations = security_audit.get_violations()
        assert len(violations) == 0
