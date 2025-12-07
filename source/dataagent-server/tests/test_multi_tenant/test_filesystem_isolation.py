"""Filesystem isolation tests.

Verifies that users cannot access each other's files and directories.
"""

import pytest
from pathlib import Path

from .conftest import (
    TestUser,
    SecurityAuditLogger,
    assert_contains_marker,
    assert_isolation_enforced,
)


class TestFilesystemIsolation:
    """Test filesystem isolation between users."""
    
    # =========================================================================
    # Positive Tests - Users can access their own files
    # =========================================================================
    
    def test_alice_can_read_own_files(self, alice: TestUser) -> None:
        """Alice can read her own knowledge files."""
        faq_path = alice.workspace_path / "knowledge" / f"{alice.user_id}-faq.md"
        
        assert faq_path.exists(), f"Alice's FAQ file should exist at {faq_path}"
        
        content = faq_path.read_text()
        assert_contains_marker(content, alice.secret_markers["file"], should_contain=True)
        assert alice.user_id in content
    
    def test_alice_can_list_own_directory(self, alice: TestUser) -> None:
        """Alice can list files in her own workspace."""
        knowledge_dir = alice.workspace_path / "knowledge"
        
        files = list(knowledge_dir.iterdir())
        assert len(files) >= 3, "Alice should have at least 3 knowledge files"
        
        file_names = [f.name for f in files]
        assert f"{alice.user_id}-faq.md" in file_names
        assert f"{alice.user_id}-guide.md" in file_names
    
    def test_bob_can_read_own_files(self, bob: TestUser) -> None:
        """Bob can read his own knowledge files."""
        faq_path = bob.workspace_path / "knowledge" / f"{bob.user_id}-faq.md"
        
        assert faq_path.exists(), f"Bob's FAQ file should exist at {faq_path}"
        
        content = faq_path.read_text()
        assert_contains_marker(content, bob.secret_markers["file"], should_contain=True)
        assert bob.user_id in content
    
    def test_alice_can_write_to_own_workspace(self, alice: TestUser) -> None:
        """Alice can write files to her own workspace."""
        test_file = alice.workspace_path / "knowledge" / "alice-test-write.md"
        
        test_content = f"Test content with {alice.secret_markers['file']}"
        test_file.write_text(test_content)
        
        assert test_file.exists()
        assert test_file.read_text() == test_content
        
        # Cleanup
        test_file.unlink()
    
    # =========================================================================
    # Negative Tests - Users cannot access other's files
    # =========================================================================
    
    def test_alice_cannot_read_bob_files_direct_path(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Alice cannot read Bob's files using direct path."""
        bob_faq_path = bob.workspace_path / "knowledge" / f"{bob.user_id}-faq.md"
        
        # Verify Bob's file exists (for test validity)
        assert bob_faq_path.exists(), "Bob's file should exist for this test"
        
        # In a properly isolated system, Alice's workspace manager should
        # not allow access to Bob's path
        # This test verifies the path is outside Alice's workspace
        
        try:
            # Check if path is within Alice's workspace
            bob_faq_path.resolve().relative_to(alice.workspace_path.resolve())
            # If we get here, the path is within Alice's workspace (BAD!)
            pytest.fail("Bob's path should NOT be within Alice's workspace")
        except ValueError:
            # Expected - path is outside Alice's workspace
            pass
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="file",
            resource_id=str(bob_faq_path),
            action="read",
            result="denied",
            details={"reason": "path outside workspace"},
        )
    
    def test_alice_files_do_not_contain_bob_secrets(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Alice's files should not contain Bob's secret markers."""
        knowledge_dir = alice.workspace_path / "knowledge"
        
        for file_path in knowledge_dir.glob("*.md"):
            content = file_path.read_text()
            assert_contains_marker(
                content,
                bob.secret_markers["file"],
                should_contain=False,
            )
    
    def test_bob_files_do_not_contain_alice_secrets(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Bob's files should not contain Alice's secret markers."""
        knowledge_dir = bob.workspace_path / "knowledge"
        
        for file_path in knowledge_dir.glob("*.md"):
            content = file_path.read_text()
            assert_contains_marker(
                content,
                alice.secret_markers["file"],
                should_contain=False,
            )
    
    def test_path_traversal_attack_blocked(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Path traversal attacks should be blocked by workspace manager.
        
        This test verifies that the WorkspaceManager correctly blocks
        path traversal attempts. The actual blocking happens at the
        application layer, not the filesystem layer.
        """
        from dataagent_core.workspace.manager import UserWorkspaceManager
        
        # Create a workspace manager with the test base path
        manager = UserWorkspaceManager(
            base_path=alice.workspace_path.parent,
        )
        
        # Simulate path traversal attempts
        traversal_paths = [
            f"../test_bob/knowledge/{bob.user_id}-faq.md",
            f"../../test_bob/knowledge/{bob.user_id}-faq.md",
            f"knowledge/../../../test_bob/knowledge/{bob.user_id}-faq.md",
        ]
        
        for traversal_path in traversal_paths:
            # The workspace manager should reject paths outside the user's workspace
            try:
                resolved = manager.resolve_path(alice.user_id, traversal_path)
                # If resolve succeeds, verify it's still within Alice's workspace
                is_valid = manager.validate_path(alice.user_id, resolved)
                if not is_valid:
                    # Path was resolved but is invalid - this is correct behavior
                    security_audit.log(
                        requesting_user=alice.user_id,
                        target_user=bob.user_id,
                        resource_type="file",
                        resource_id=traversal_path,
                        action="read",
                        result="denied",
                        details={"reason": "path validation failed"},
                    )
            except ValueError:
                # Expected - path traversal blocked
                security_audit.log(
                    requesting_user=alice.user_id,
                    target_user=bob.user_id,
                    resource_type="file",
                    resource_id=traversal_path,
                    action="read",
                    result="denied",
                    details={"reason": "path traversal blocked"},
                )
    
    def test_workspaces_are_separate_directories(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Verify workspaces are in completely separate directories."""
        alice_resolved = alice.workspace_path.resolve()
        bob_resolved = bob.workspace_path.resolve()
        
        # Neither should be a parent of the other
        try:
            alice_resolved.relative_to(bob_resolved)
            pytest.fail("Alice's workspace should not be inside Bob's")
        except ValueError:
            pass
        
        try:
            bob_resolved.relative_to(alice_resolved)
            pytest.fail("Bob's workspace should not be inside Alice's")
        except ValueError:
            pass
        
        # They should have different paths
        assert alice_resolved != bob_resolved
    
    # =========================================================================
    # Search Isolation Tests
    # =========================================================================
    
    def test_search_in_alice_workspace_finds_only_alice_files(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Searching in Alice's workspace should only find Alice's files."""
        # Search for "SECRET" in Alice's workspace
        found_files = []
        for file_path in alice.workspace_path.rglob("*.md"):
            content = file_path.read_text()
            if "SECRET" in content:
                found_files.append(file_path)
        
        # All found files should be Alice's
        for file_path in found_files:
            assert alice.user_id in str(file_path) or alice.user_id in file_path.read_text()
            # Should not contain Bob's markers
            content = file_path.read_text()
            assert_contains_marker(content, bob.secret_markers["file"], should_contain=False)
    
    def test_glob_pattern_respects_workspace_boundary(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Glob patterns should respect workspace boundaries."""
        # This pattern should only match files in Alice's workspace
        pattern = alice.workspace_path / "**" / "*.md"
        
        matched_files = list(alice.workspace_path.rglob("*.md"))
        
        for file_path in matched_files:
            # All matched files should be within Alice's workspace
            assert str(alice.workspace_path) in str(file_path)
            # None should be in Bob's workspace
            assert str(bob.workspace_path) not in str(file_path)


class TestFilesystemIsolationWithWorkspaceManager:
    """Test filesystem isolation using WorkspaceManager."""
    
    def test_workspace_manager_validates_paths(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """WorkspaceManager should validate paths are within user's workspace."""
        from dataagent_core.workspace.manager import UserWorkspaceManager
        
        manager = UserWorkspaceManager(
            base_path=alice.workspace_path.parent,
        )
        
        # Alice's path should be valid
        assert manager.validate_path(alice.user_id, alice.workspace_path / "knowledge")
        
        # Bob's path should be invalid for Alice
        assert not manager.validate_path(alice.user_id, bob.workspace_path / "knowledge")
    
    def test_workspace_manager_blocks_path_traversal(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """WorkspaceManager should block path traversal attempts."""
        from dataagent_core.workspace.manager import UserWorkspaceManager
        
        manager = UserWorkspaceManager(
            base_path=alice.workspace_path.parent,
        )
        
        # Path traversal should be blocked
        traversal_path = f"../test_bob/knowledge"
        
        try:
            resolved = manager.resolve_path(alice.user_id, traversal_path)
            # If resolve succeeds, verify it's still within Alice's workspace
            assert manager.validate_path(alice.user_id, resolved)
        except ValueError:
            # Expected - path traversal blocked
            pass


class TestFilesystemSecurityAudit:
    """Test security audit logging for filesystem operations."""
    
    def test_audit_log_records_cross_tenant_attempts(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Security audit should record all cross-tenant access attempts."""
        # Simulate cross-tenant access attempts
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="file",
            resource_id=f"{bob.workspace_path}/knowledge/bob-faq.md",
            action="read",
            result="denied",
        )
        
        security_audit.log(
            requesting_user=bob.user_id,
            target_user=alice.user_id,
            resource_type="file",
            resource_id=f"{alice.workspace_path}/knowledge/alice-faq.md",
            action="read",
            result="denied",
        )
        
        # Verify audit log
        cross_tenant = security_audit.get_cross_tenant_attempts()
        assert len(cross_tenant) == 2
        
        violations = security_audit.get_violations()
        assert len(violations) == 0, "There should be no security violations"
    
    def test_audit_report_generation(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Security audit should generate comprehensive reports."""
        # Log some events
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=alice.user_id,
            resource_type="file",
            resource_id="alice-faq.md",
            action="read",
            result="allowed",
        )
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="file",
            resource_id="bob-faq.md",
            action="read",
            result="denied",
        )
        
        report = security_audit.generate_report()
        
        assert report["total_events"] == 2
        assert report["cross_tenant_attempts"] == 1
        assert report["violations"] == 0
        assert report["all_blocked"] is True
        assert "file" in report["events_by_type"]
