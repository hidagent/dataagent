"""Tests for user workspace manager.

Property 53: 用户工作区配额检查
"""

import tempfile
from pathlib import Path

import pytest

from dataagent_core.workspace.manager import (
    UserWorkspaceManager,
    WorkspaceQuota,
    WorkspaceInfo,
)


class TestUserWorkspaceManager:
    """Tests for UserWorkspaceManager."""

    def test_init(self):
        """Test initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            assert manager.base_path == Path(tmpdir)
            assert manager.default_quota is not None

    def test_get_workspace_path(self):
        """Test getting workspace path for user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            path = manager.get_workspace_path("user1")
            assert path == Path(tmpdir) / "user1"

    def test_sanitize_user_id(self):
        """Test user ID sanitization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            
            # Normal ID
            assert manager._sanitize_user_id("user123") == "user123"
            
            # Path traversal attempt
            assert ".." not in manager._sanitize_user_id("../../../etc")
            
            # Special characters
            safe = manager._sanitize_user_id("user/with\\special:chars")
            assert "/" not in safe
            assert "\\" not in safe

    def test_create_workspace(self):
        """Test creating a workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            info = manager.create_workspace("user1")
            
            assert info.user_id == "user1"
            assert info.path.exists()
            assert info.created is True

    def test_create_workspace_idempotent(self):
        """Test creating workspace twice returns existing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            info1 = manager.create_workspace("user1")
            info2 = manager.create_workspace("user1")
            
            assert info1.path == info2.path
            # Second call should return created=False (already exists)
            assert info2.created is False or info2.path.exists()

    def test_get_workspace_info_nonexistent(self):
        """Test getting info for nonexistent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            info = manager.get_workspace_info("nonexistent")
            
            assert info.created is False
            assert info.size_bytes == 0
            assert info.file_count == 0

    def test_get_workspace_info_with_files(self):
        """Test getting info for workspace with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            # Create some files
            workspace = manager.get_workspace_path("user1")
            (workspace / "file1.txt").write_text("hello")
            (workspace / "file2.txt").write_text("world")
            
            info = manager.get_workspace_info("user1")
            assert info.file_count == 2
            assert info.size_bytes > 0

    def test_delete_workspace(self):
        """Test deleting a workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            result = manager.delete_workspace("user1")
            assert result is True
            assert not manager.get_workspace_path("user1").exists()

    def test_delete_nonexistent_workspace(self):
        """Test deleting nonexistent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            result = manager.delete_workspace("nonexistent")
            assert result is False

    def test_validate_path_within_workspace(self):
        """Test path validation for paths within workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            workspace = manager.get_workspace_path("user1")
            
            # Valid paths
            assert manager.validate_path("user1", workspace / "file.txt")
            assert manager.validate_path("user1", workspace / "subdir" / "file.txt")

    def test_validate_path_outside_workspace(self):
        """Test path validation rejects paths outside workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            # Invalid paths
            assert not manager.validate_path("user1", Path("/etc/passwd"))
            assert not manager.validate_path("user1", Path(tmpdir) / "user2" / "file.txt")

    def test_resolve_path(self):
        """Test resolving relative paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            workspace = manager.get_workspace_path("user1")
            
            resolved = manager.resolve_path("user1", "subdir/file.txt")
            assert resolved == (workspace / "subdir" / "file.txt").resolve()

    def test_resolve_path_escape_raises(self):
        """Test resolving path that escapes workspace raises."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            with pytest.raises(ValueError, match="escapes workspace"):
                manager.resolve_path("user1", "../../../etc/passwd")


class TestWorkspaceQuota:
    """Tests for workspace quota management.
    
    Property 53: 用户工作区配额检查
    """

    def test_default_quota(self):
        """Test default quota values."""
        quota = WorkspaceQuota()
        assert quota.max_size_bytes == 1024 * 1024 * 1024  # 1GB
        assert quota.max_files == 10000
        assert quota.max_file_size_bytes == 100 * 1024 * 1024  # 100MB

    def test_custom_quota(self):
        """Test custom quota values."""
        quota = WorkspaceQuota(
            max_size_bytes=500 * 1024 * 1024,
            max_files=1000,
            max_file_size_bytes=10 * 1024 * 1024,
        )
        assert quota.max_size_bytes == 500 * 1024 * 1024
        assert quota.max_files == 1000
        assert quota.max_file_size_bytes == 10 * 1024 * 1024

    def test_set_user_quota(self):
        """Test setting quota for specific user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            
            custom_quota = WorkspaceQuota(max_size_bytes=100 * 1024 * 1024)
            manager.set_quota("user1", custom_quota)
            
            assert manager.get_quota("user1") == custom_quota

    def test_get_default_quota(self):
        """Test getting default quota for user without custom quota."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            quota = manager.get_quota("user1")
            assert quota == manager.default_quota

    def test_check_quota_within_limits(self):
        """Property 53: 配额检查 - 在限制内返回 True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            # Empty workspace should be within quota
            assert manager.check_quota("user1") is True
            assert manager.check_quota("user1", additional_bytes=1000) is True

    def test_check_quota_exceeds_size(self):
        """Property 53: 配额检查 - 超出大小限制返回 False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            # Set very small quota
            manager.set_quota("user1", WorkspaceQuota(max_size_bytes=100))
            
            # Create file that exceeds quota
            workspace = manager.get_workspace_path("user1")
            (workspace / "large.txt").write_text("x" * 200)
            
            # Should fail quota check
            assert manager.check_quota("user1") is False

    def test_check_quota_exceeds_file_count(self):
        """Property 53: 配额检查 - 超出文件数限制返回 False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            # Set very small file count quota
            manager.set_quota("user1", WorkspaceQuota(max_files=2))
            
            # Create files
            workspace = manager.get_workspace_path("user1")
            (workspace / "file1.txt").write_text("a")
            (workspace / "file2.txt").write_text("b")
            
            # Should fail quota check (at limit)
            assert manager.check_quota("user1") is False

    def test_check_quota_with_additional_bytes(self):
        """Property 53: 配额检查 - 考虑额外字节."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.create_workspace("user1")
            
            # Set quota
            manager.set_quota("user1", WorkspaceQuota(max_size_bytes=1000))
            
            # Create file using some quota
            workspace = manager.get_workspace_path("user1")
            (workspace / "file.txt").write_text("x" * 500)
            
            # Check with additional bytes
            assert manager.check_quota("user1", additional_bytes=400) is True
            assert manager.check_quota("user1", additional_bytes=600) is False
