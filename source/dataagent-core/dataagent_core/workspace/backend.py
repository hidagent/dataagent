"""Sandboxed filesystem backend for multi-tenant isolation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataagent_core.workspace.manager import UserWorkspaceManager

logger = logging.getLogger(__name__)


class PathEscapeError(Exception):
    """Raised when a path operation attempts to escape the sandbox."""
    pass


class QuotaExceededError(Exception):
    """Raised when a workspace quota is exceeded."""
    pass


class SandboxedFilesystemBackend:
    """Filesystem backend that restricts operations to user's workspace.
    
    All file operations are sandboxed within the user's workspace directory.
    Path traversal attacks are prevented by validating all paths.
    """
    
    def __init__(
        self,
        workspace_manager: UserWorkspaceManager,
        user_id: str,
        check_quota: bool = True,
    ) -> None:
        """Initialize sandboxed backend.
        
        Args:
            workspace_manager: Workspace manager instance.
            user_id: User ID for this backend.
            check_quota: Whether to check quotas on write operations.
        """
        self.workspace_manager = workspace_manager
        self.user_id = user_id
        self.check_quota = check_quota
        
        # Ensure workspace exists
        self.workspace_manager.create_workspace(user_id)
    
    @property
    def workspace_path(self) -> Path:
        """Get the workspace path for this backend."""
        return self.workspace_manager.get_workspace_path(self.user_id)
    
    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve and validate a path within the sandbox.
        
        Args:
            path: Path to resolve (relative or absolute).
            
        Returns:
            Resolved absolute path within workspace.
            
        Raises:
            PathEscapeError: If path escapes the sandbox.
        """
        path = Path(path)
        
        # If absolute, check if it's within workspace
        if path.is_absolute():
            resolved = path.resolve()
        else:
            # Relative path - resolve from workspace root
            resolved = (self.workspace_path / path).resolve()
        
        # Validate path is within workspace
        if not self.workspace_manager.validate_path(self.user_id, resolved):
            raise PathEscapeError(
                f"Path '{path}' escapes workspace sandbox"
            )
        
        return resolved
    
    def _check_write_quota(self, size: int) -> None:
        """Check if write operation would exceed quota.
        
        Args:
            size: Size of data to write in bytes.
            
        Raises:
            QuotaExceededError: If quota would be exceeded.
        """
        if not self.check_quota:
            return
        
        if not self.workspace_manager.check_quota(self.user_id, size):
            raise QuotaExceededError(
                f"Write operation would exceed workspace quota for user {self.user_id}"
            )
    
    def read_file(self, path: str | Path) -> str:
        """Read a file from the sandbox.
        
        Args:
            path: Path to file (relative to workspace or absolute within workspace).
            
        Returns:
            File contents as string.
            
        Raises:
            PathEscapeError: If path escapes sandbox.
            FileNotFoundError: If file doesn't exist.
        """
        resolved = self._resolve_path(path)
        return resolved.read_text(encoding="utf-8")
    
    def read_file_bytes(self, path: str | Path) -> bytes:
        """Read a file as bytes from the sandbox.
        
        Args:
            path: Path to file.
            
        Returns:
            File contents as bytes.
        """
        resolved = self._resolve_path(path)
        return resolved.read_bytes()
    
    def write_file(self, path: str | Path, content: str) -> Path:
        """Write content to a file in the sandbox.
        
        Args:
            path: Path to file.
            content: Content to write.
            
        Returns:
            Resolved path to written file.
            
        Raises:
            PathEscapeError: If path escapes sandbox.
            QuotaExceededError: If quota would be exceeded.
        """
        resolved = self._resolve_path(path)
        
        # Check quota
        content_bytes = content.encode("utf-8")
        self._check_write_quota(len(content_bytes))
        
        # Create parent directories
        resolved.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        resolved.write_text(content, encoding="utf-8")
        logger.debug(f"Wrote file: {resolved}")
        
        return resolved
    
    def write_file_bytes(self, path: str | Path, content: bytes) -> Path:
        """Write bytes to a file in the sandbox.
        
        Args:
            path: Path to file.
            content: Bytes to write.
            
        Returns:
            Resolved path to written file.
        """
        resolved = self._resolve_path(path)
        
        # Check quota
        self._check_write_quota(len(content))
        
        # Create parent directories
        resolved.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        resolved.write_bytes(content)
        logger.debug(f"Wrote file (bytes): {resolved}")
        
        return resolved
    
    def delete_file(self, path: str | Path) -> bool:
        """Delete a file from the sandbox.
        
        Args:
            path: Path to file.
            
        Returns:
            True if file was deleted, False if not found.
        """
        resolved = self._resolve_path(path)
        
        if not resolved.exists():
            return False
        
        if resolved.is_dir():
            raise IsADirectoryError(f"Cannot delete directory with delete_file: {path}")
        
        resolved.unlink()
        logger.debug(f"Deleted file: {resolved}")
        return True
    
    def exists(self, path: str | Path) -> bool:
        """Check if a path exists in the sandbox.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path exists.
        """
        try:
            resolved = self._resolve_path(path)
            return resolved.exists()
        except PathEscapeError:
            return False
    
    def is_file(self, path: str | Path) -> bool:
        """Check if path is a file.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path is a file.
        """
        try:
            resolved = self._resolve_path(path)
            return resolved.is_file()
        except PathEscapeError:
            return False
    
    def is_dir(self, path: str | Path) -> bool:
        """Check if path is a directory.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path is a directory.
        """
        try:
            resolved = self._resolve_path(path)
            return resolved.is_dir()
        except PathEscapeError:
            return False
    
    def list_dir(self, path: str | Path = ".") -> list[str]:
        """List directory contents.
        
        Args:
            path: Path to directory (default: workspace root).
            
        Returns:
            List of file/directory names.
        """
        resolved = self._resolve_path(path)
        
        if not resolved.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        return [p.name for p in resolved.iterdir()]
    
    def mkdir(self, path: str | Path, parents: bool = True) -> Path:
        """Create a directory in the sandbox.
        
        Args:
            path: Path to directory.
            parents: Create parent directories if needed.
            
        Returns:
            Resolved path to created directory.
        """
        resolved = self._resolve_path(path)
        resolved.mkdir(parents=parents, exist_ok=True)
        logger.debug(f"Created directory: {resolved}")
        return resolved
    
    def rmdir(self, path: str | Path, recursive: bool = False) -> bool:
        """Remove a directory from the sandbox.
        
        Args:
            path: Path to directory.
            recursive: Remove contents recursively.
            
        Returns:
            True if directory was removed.
        """
        import shutil
        
        resolved = self._resolve_path(path)
        
        if not resolved.exists():
            return False
        
        if not resolved.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        if recursive:
            shutil.rmtree(resolved)
        else:
            resolved.rmdir()
        
        logger.debug(f"Removed directory: {resolved}")
        return True
    
    def get_relative_path(self, absolute_path: Path) -> str:
        """Get path relative to workspace root.
        
        Args:
            absolute_path: Absolute path within workspace.
            
        Returns:
            Path relative to workspace root.
        """
        return str(absolute_path.relative_to(self.workspace_path))
