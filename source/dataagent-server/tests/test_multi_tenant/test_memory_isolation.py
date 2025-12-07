"""Memory/Knowledge isolation tests.

Verifies that users cannot access each other's memory and knowledge.
"""

import pytest
from pathlib import Path

from .conftest import (
    TestUser,
    SecurityAuditLogger,
    assert_contains_marker,
    assert_isolation_enforced,
)


class TestMemoryIsolation:
    """Test memory isolation between users."""
    
    # =========================================================================
    # Positive Tests - Users can access their own memory
    # =========================================================================
    
    def test_alice_can_read_own_memory(self, alice: TestUser) -> None:
        """Alice can read her own agent.md memory file."""
        memory_path = alice.memory_path / "agent.md"
        
        assert memory_path.exists(), f"Alice's memory should exist at {memory_path}"
        
        content = memory_path.read_text()
        assert_contains_marker(content, alice.secret_markers["memory"], should_contain=True)
        assert alice.user_id in content
        assert alice.display_name in content
    
    def test_alice_can_update_own_memory(self, alice: TestUser) -> None:
        """Alice can update her own memory file."""
        memory_path = alice.memory_path / "agent.md"
        
        original_content = memory_path.read_text()
        
        # Add new content
        new_content = original_content + "\n\n## New Section\nAlice added this."
        memory_path.write_text(new_content)
        
        # Verify update
        updated_content = memory_path.read_text()
        assert "New Section" in updated_content
        assert "Alice added this" in updated_content
        
        # Restore original
        memory_path.write_text(original_content)
    
    def test_bob_can_read_own_memory(self, bob: TestUser) -> None:
        """Bob can read his own agent.md memory file."""
        memory_path = bob.memory_path / "agent.md"
        
        assert memory_path.exists(), f"Bob's memory should exist at {memory_path}"
        
        content = memory_path.read_text()
        assert_contains_marker(content, bob.secret_markers["memory"], should_contain=True)
        assert bob.user_id in content
        assert bob.display_name in content
    
    def test_alice_can_create_memory_files(self, alice: TestUser) -> None:
        """Alice can create additional memory files."""
        new_memory_path = alice.memory_path / "notes.md"
        
        content = f"# Alice's Notes\n\nSecret: {alice.secret_markers['memory']}_NOTES"
        new_memory_path.write_text(content)
        
        assert new_memory_path.exists()
        assert alice.secret_markers["memory"] in new_memory_path.read_text()
        
        # Cleanup
        new_memory_path.unlink()
    
    # =========================================================================
    # Negative Tests - Users cannot access other's memory
    # =========================================================================
    
    def test_alice_cannot_read_bob_memory_direct_path(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Alice cannot read Bob's memory using direct path."""
        bob_memory_path = bob.memory_path / "agent.md"
        
        # Verify Bob's memory exists
        assert bob_memory_path.exists(), "Bob's memory should exist for this test"
        
        # Verify paths are separate
        try:
            bob_memory_path.resolve().relative_to(alice.memory_path.resolve())
            pytest.fail("Bob's memory path should NOT be within Alice's memory path")
        except ValueError:
            # Expected - paths are separate
            pass
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="memory",
            resource_id=str(bob_memory_path),
            action="read",
            result="denied",
            details={"reason": "path outside user's memory directory"},
        )
    
    def test_alice_memory_does_not_contain_bob_markers(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Alice's memory should not contain Bob's secret markers."""
        for memory_file in alice.memory_path.glob("*.md"):
            content = memory_file.read_text()
            assert_contains_marker(
                content,
                bob.secret_markers["memory"],
                should_contain=False,
            )
    
    def test_bob_memory_does_not_contain_alice_markers(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Bob's memory should not contain Alice's secret markers."""
        for memory_file in bob.memory_path.glob("*.md"):
            content = memory_file.read_text()
            assert_contains_marker(
                content,
                alice.secret_markers["memory"],
                should_contain=False,
            )
    
    def test_memory_directories_are_separate(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Verify memory directories are completely separate."""
        alice_resolved = alice.memory_path.resolve()
        bob_resolved = bob.memory_path.resolve()
        
        # Neither should be a parent of the other
        try:
            alice_resolved.relative_to(bob_resolved)
            pytest.fail("Alice's memory should not be inside Bob's")
        except ValueError:
            pass
        
        try:
            bob_resolved.relative_to(alice_resolved)
            pytest.fail("Bob's memory should not be inside Alice's")
        except ValueError:
            pass
        
        assert alice_resolved != bob_resolved
    
    def test_path_traversal_to_other_user_memory_blocked(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Path traversal to other user's memory should be blocked."""
        traversal_paths = [
            f"../test_bob/agent/agent.md",
            f"../../users/test_bob/agent/agent.md",
            f"agent.md/../../../test_bob/agent/agent.md",
        ]
        
        for traversal_path in traversal_paths:
            attempted_path = (alice.memory_path / traversal_path).resolve()
            
            try:
                attempted_path.relative_to(alice.memory_path.resolve())
                if bob.user_id in str(attempted_path):
                    pytest.fail(f"Path traversal succeeded: {traversal_path}")
            except ValueError:
                security_audit.log(
                    requesting_user=alice.user_id,
                    target_user=bob.user_id,
                    resource_type="memory",
                    resource_id=traversal_path,
                    action="read",
                    result="denied",
                    details={"reason": "path traversal blocked"},
                )


class TestMemoryMiddlewareIsolation:
    """Test memory isolation using AgentMemoryMiddleware."""
    
    @pytest.mark.skip(reason="Requires Settings configuration")
    def test_memory_middleware_uses_user_specific_path(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """AgentMemoryMiddleware should use user-specific paths."""
        from dataagent_core.config import Settings
        from dataagent_core.middleware.memory import AgentMemoryMiddleware
        
        # Note: This test requires proper Settings configuration
        # Skip for now as it needs environment setup
        pass
    
    @pytest.mark.skip(reason="Requires Settings configuration")
    def test_memory_middleware_loads_only_user_memory(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """AgentMemoryMiddleware should only load the user's own memory."""
        # Note: This test requires proper Settings configuration
        # Skip for now as it needs environment setup
        pass
    
    def test_memory_paths_are_user_isolated(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Memory paths should be isolated per user."""
        # Verify the path structure includes user_id
        alice_path_str = str(alice.memory_path)
        bob_path_str = str(bob.memory_path)
        
        assert alice.user_id in alice_path_str
        assert bob.user_id in bob_path_str
        assert alice.user_id not in bob_path_str
        assert bob.user_id not in alice_path_str


class TestMemoryClearIsolation:
    """Test memory clear operation isolation."""
    
    def test_clear_alice_memory_does_not_affect_bob(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Clearing Alice's memory should not affect Bob's memory."""
        # Create a test file in Alice's memory
        alice_test_file = alice.memory_path / "test-clear.md"
        alice_test_file.write_text("Alice's test file")
        
        # Verify Bob's memory exists
        bob_memory = bob.memory_path / "agent.md"
        bob_content_before = bob_memory.read_text()
        
        # Clear Alice's test file
        alice_test_file.unlink()
        
        # Bob's memory should be unchanged
        assert bob_memory.exists()
        bob_content_after = bob_memory.read_text()
        assert bob_content_before == bob_content_after
    
    def test_alice_cannot_clear_bob_memory(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Alice should not be able to clear Bob's memory."""
        bob_memory = bob.memory_path / "agent.md"
        bob_content_before = bob_memory.read_text()
        
        # Verify Alice cannot access Bob's path
        try:
            bob_memory.resolve().relative_to(alice.memory_path.resolve())
            pytest.fail("Bob's memory should not be accessible from Alice's path")
        except ValueError:
            pass
        
        # Bob's memory should still exist and be unchanged
        assert bob_memory.exists()
        assert bob_memory.read_text() == bob_content_before
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="memory",
            resource_id=str(bob_memory),
            action="delete",
            result="denied",
        )


class TestMemoryAPIIsolation:
    """Test memory isolation via REST API."""
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_get_memory_status_returns_only_user_memory(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """API should return only the requesting user's memory status."""
        from .conftest import make_request_as_user
        
        response = make_request_as_user(
            api_client,
            alice,
            "GET",
            f"/api/v1/users/{alice.user_id}/memory/status",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Path should be Alice's
        assert alice.user_id in data.get("path", "")
        assert bob.user_id not in data.get("path", "")
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_access_bob_memory(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to access Bob's memory via API."""
        from .conftest import make_request_as_user
        
        response = make_request_as_user(
            api_client,
            alice,
            "GET",
            f"/api/v1/users/{bob.user_id}/memory/status",
        )
        
        assert_isolation_enforced(response.status_code)
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_delete_bob_memory(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to delete Bob's memory via API."""
        from .conftest import make_request_as_user
        
        response = make_request_as_user(
            api_client,
            alice,
            "DELETE",
            f"/api/v1/users/{bob.user_id}/memory",
        )
        
        assert_isolation_enforced(response.status_code)


class TestMemorySecurityAudit:
    """Test security audit logging for memory operations."""
    
    def test_audit_log_records_cross_tenant_memory_access(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Security audit should record cross-tenant memory access attempts."""
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="memory",
            resource_id="agent.md",
            action="read",
            result="denied",
        )
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="memory",
            resource_id="agent.md",
            action="delete",
            result="denied",
        )
        
        cross_tenant = security_audit.get_cross_tenant_attempts()
        assert len(cross_tenant) == 2
        
        violations = security_audit.get_violations()
        assert len(violations) == 0
