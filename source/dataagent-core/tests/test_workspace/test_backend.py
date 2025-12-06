"""Tests for sandboxed filesystem backend.

Property 52: 用户工作区路径沙箱
"""

import tempfile
from pathlib import Path

import pytest

from dataagent_core.workspace.manager import UserWorkspaceManager, WorkspaceQuota
from dataagent_core.workspace.backend import (
    SandboxedFilesystemBackend,
    PathEscapeError,
    QuotaExceededError,
)


class TestSandboxedFilesystemBackend:
    """Tests for SandboxedFilesystemBackend."""

    @pytest.fixture
    def backend(self):
        """Create a backend with temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            yield backend

    def test_init_creates_workspace(self):
        """Test initialization creates workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            assert backend.workspace_path.exists()

    def test_write_and_read_file(self):
        """Test writing and reading a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.write_file("test.txt", "hello world")
            content = backend.read_file("test.txt")
            
            assert content == "hello world"

    def test_write_creates_parent_dirs(self):
        """Test writing creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.write_file("subdir/nested/file.txt", "content")
            assert backend.exists("subdir/nested/file.txt")

    def test_delete_file(self):
        """Test deleting a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.write_file("test.txt", "content")
            assert backend.delete_file("test.txt") is True
            assert not backend.exists("test.txt")

    def test_delete_nonexistent_file(self):
        """Test deleting nonexistent file returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            assert backend.delete_file("nonexistent.txt") is False

    def test_exists(self):
        """Test checking file existence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            assert not backend.exists("test.txt")
            backend.write_file("test.txt", "content")
            assert backend.exists("test.txt")

    def test_is_file_and_is_dir(self):
        """Test checking file vs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.write_file("file.txt", "content")
            backend.mkdir("directory")
            
            assert backend.is_file("file.txt")
            assert not backend.is_dir("file.txt")
            assert backend.is_dir("directory")
            assert not backend.is_file("directory")

    def test_list_dir(self):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.write_file("file1.txt", "a")
            backend.write_file("file2.txt", "b")
            backend.mkdir("subdir")
            
            contents = backend.list_dir(".")
            assert "file1.txt" in contents
            assert "file2.txt" in contents
            assert "subdir" in contents

    def test_mkdir_and_rmdir(self):
        """Test creating and removing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.mkdir("testdir")
            assert backend.is_dir("testdir")
            
            backend.rmdir("testdir")
            assert not backend.exists("testdir")

    def test_rmdir_recursive(self):
        """Test recursive directory removal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            backend.write_file("testdir/file.txt", "content")
            backend.rmdir("testdir", recursive=True)
            assert not backend.exists("testdir")


class TestPathSandbox:
    """Tests for path sandboxing.
    
    Property 52: 用户工作区路径沙箱
    """

    def test_path_escape_relative(self):
        """Property 52: 相对路径逃逸被阻止."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            with pytest.raises(PathEscapeError):
                backend.read_file("../../../etc/passwd")

    def test_path_escape_absolute(self):
        """Property 52: 绝对路径逃逸被阻止."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            with pytest.raises(PathEscapeError):
                backend.read_file("/etc/passwd")

    def test_path_escape_write(self):
        """Property 52: 写入路径逃逸被阻止."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            with pytest.raises(PathEscapeError):
                backend.write_file("../../../tmp/evil.txt", "malicious")

    def test_path_escape_delete(self):
        """Property 52: 删除路径逃逸被阻止."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            with pytest.raises(PathEscapeError):
                backend.delete_file("../../../etc/passwd")

    def test_path_escape_exists(self):
        """Property 52: exists 检查路径逃逸返回 False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            # Should return False instead of raising
            assert backend.exists("../../../etc/passwd") is False

    def test_path_escape_symlink(self):
        """Property 52: 符号链接逃逸被阻止."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            # Create a symlink pointing outside workspace
            workspace = backend.workspace_path
            symlink = workspace / "evil_link"
            try:
                symlink.symlink_to("/etc")
            except OSError:
                pytest.skip("Cannot create symlinks")
            
            # Accessing through symlink should fail
            with pytest.raises(PathEscapeError):
                backend.read_file("evil_link/passwd")

    def test_valid_nested_path(self):
        """Property 52: 有效的嵌套路径可以访问."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            backend = SandboxedFilesystemBackend(manager, "user1")
            
            # Valid nested path should work
            backend.write_file("a/b/c/d/file.txt", "deep content")
            content = backend.read_file("a/b/c/d/file.txt")
            assert content == "deep content"


class TestQuotaEnforcement:
    """Tests for quota enforcement in backend."""

    def test_write_exceeds_quota(self):
        """Test writing file that exceeds quota raises."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.set_quota("user1", WorkspaceQuota(max_size_bytes=100))
            backend = SandboxedFilesystemBackend(manager, "user1", check_quota=True)
            
            with pytest.raises(QuotaExceededError):
                backend.write_file("large.txt", "x" * 200)

    def test_write_within_quota(self):
        """Test writing file within quota succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.set_quota("user1", WorkspaceQuota(max_size_bytes=1000))
            backend = SandboxedFilesystemBackend(manager, "user1", check_quota=True)
            
            # Should not raise
            backend.write_file("small.txt", "hello")
            assert backend.read_file("small.txt") == "hello"

    def test_quota_check_disabled(self):
        """Test quota check can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkspaceManager(tmpdir)
            manager.set_quota("user1", WorkspaceQuota(max_size_bytes=10))
            backend = SandboxedFilesystemBackend(manager, "user1", check_quota=False)
            
            # Should not raise even though exceeds quota
            backend.write_file("large.txt", "x" * 100)
            assert backend.exists("large.txt")
