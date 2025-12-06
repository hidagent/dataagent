"""User workspace management."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceQuota:
    """Quota configuration for user workspaces."""
    
    max_size_bytes: int = 1024 * 1024 * 1024  # 1GB default
    max_files: int = 10000
    max_file_size_bytes: int = 100 * 1024 * 1024  # 100MB default


@dataclass
class WorkspaceInfo:
    """Information about a user workspace."""
    
    user_id: str
    path: Path
    size_bytes: int = 0
    file_count: int = 0
    created: bool = False


class UserWorkspaceManager:
    """Manages user workspaces with isolation and quotas.
    
    Each user gets an isolated workspace directory for file operations.
    """
    
    def __init__(
        self,
        base_path: Path | str,
        default_quota: WorkspaceQuota | None = None,
    ) -> None:
        """Initialize workspace manager.
        
        Args:
            base_path: Base directory for all user workspaces.
            default_quota: Default quota for new workspaces.
        """
        self.base_path = Path(base_path)
        self.default_quota = default_quota or WorkspaceQuota()
        self._user_quotas: dict[str, WorkspaceQuota] = {}
    
    def get_workspace_path(self, user_id: str) -> Path:
        """Get the workspace path for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            Path to user's workspace directory.
        """
        # Sanitize user_id to prevent path traversal
        safe_user_id = self._sanitize_user_id(user_id)
        return self.base_path / safe_user_id
    
    def _sanitize_user_id(self, user_id: str) -> str:
        """Sanitize user ID for safe filesystem use.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            Sanitized user ID safe for filesystem paths.
        """
        # Remove any path separators and dangerous characters
        safe_id = user_id.replace("/", "_").replace("\\", "_")
        safe_id = safe_id.replace("..", "_")
        # Only allow alphanumeric, underscore, hyphen
        safe_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in safe_id)
        return safe_id or "anonymous"
    
    def create_workspace(self, user_id: str) -> WorkspaceInfo:
        """Create a workspace for a user.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            WorkspaceInfo with workspace details.
        """
        workspace_path = self.get_workspace_path(user_id)
        
        if workspace_path.exists():
            return self.get_workspace_info(user_id)
        
        workspace_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created workspace for user {user_id}: {workspace_path}")
        
        return WorkspaceInfo(
            user_id=user_id,
            path=workspace_path,
            size_bytes=0,
            file_count=0,
            created=True,
        )
    
    def get_workspace_info(self, user_id: str) -> WorkspaceInfo:
        """Get information about a user's workspace.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            WorkspaceInfo with workspace details.
        """
        workspace_path = self.get_workspace_path(user_id)
        
        if not workspace_path.exists():
            return WorkspaceInfo(
                user_id=user_id,
                path=workspace_path,
                size_bytes=0,
                file_count=0,
                created=False,
            )
        
        # Calculate size and file count
        size_bytes = 0
        file_count = 0
        
        for root, dirs, files in os.walk(workspace_path):
            for f in files:
                file_path = Path(root) / f
                try:
                    size_bytes += file_path.stat().st_size
                    file_count += 1
                except OSError:
                    pass
        
        return WorkspaceInfo(
            user_id=user_id,
            path=workspace_path,
            size_bytes=size_bytes,
            file_count=file_count,
            created=True,
        )
    
    def delete_workspace(self, user_id: str) -> bool:
        """Delete a user's workspace.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            True if workspace was deleted, False if not found.
        """
        workspace_path = self.get_workspace_path(user_id)
        
        if not workspace_path.exists():
            return False
        
        shutil.rmtree(workspace_path)
        logger.info(f"Deleted workspace for user {user_id}")
        return True
    
    def validate_path(self, user_id: str, path: Path | str) -> bool:
        """Validate that a path is within the user's workspace.
        
        Args:
            user_id: The user identifier.
            path: Path to validate.
            
        Returns:
            True if path is within workspace, False otherwise.
        """
        workspace_path = self.get_workspace_path(user_id)
        target_path = Path(path).resolve()
        
        try:
            target_path.relative_to(workspace_path.resolve())
            return True
        except ValueError:
            return False
    
    def resolve_path(self, user_id: str, relative_path: str) -> Path:
        """Resolve a relative path within user's workspace.
        
        Args:
            user_id: The user identifier.
            relative_path: Path relative to workspace root.
            
        Returns:
            Absolute path within workspace.
            
        Raises:
            ValueError: If path escapes workspace.
        """
        workspace_path = self.get_workspace_path(user_id)
        
        # Normalize and resolve the path
        target_path = (workspace_path / relative_path).resolve()
        
        # Ensure it's within workspace
        if not self.validate_path(user_id, target_path):
            raise ValueError(f"Path escapes workspace: {relative_path}")
        
        return target_path
    
    def set_quota(self, user_id: str, quota: WorkspaceQuota) -> None:
        """Set quota for a user's workspace.
        
        Args:
            user_id: The user identifier.
            quota: Quota configuration.
        """
        self._user_quotas[user_id] = quota
    
    def get_quota(self, user_id: str) -> WorkspaceQuota:
        """Get quota for a user's workspace.
        
        Args:
            user_id: The user identifier.
            
        Returns:
            Quota configuration for the user.
        """
        return self._user_quotas.get(user_id, self.default_quota)
    
    def check_quota(self, user_id: str, additional_bytes: int = 0) -> bool:
        """Check if user is within quota limits.
        
        Args:
            user_id: The user identifier.
            additional_bytes: Additional bytes to be added.
            
        Returns:
            True if within quota, False if would exceed.
        """
        info = self.get_workspace_info(user_id)
        quota = self.get_quota(user_id)
        
        # Check size quota
        if info.size_bytes + additional_bytes > quota.max_size_bytes:
            return False
        
        # Check file count quota
        if info.file_count >= quota.max_files:
            return False
        
        return True
    
    def cleanup_old_workspaces(self, max_age_days: int = 30) -> int:
        """Clean up workspaces not accessed recently.
        
        Args:
            max_age_days: Maximum age in days before cleanup.
            
        Returns:
            Number of workspaces cleaned up.
        """
        import time
        
        if not self.base_path.exists():
            return 0
        
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = time.time()
        cleaned = 0
        
        for workspace_dir in self.base_path.iterdir():
            if not workspace_dir.is_dir():
                continue
            
            try:
                mtime = workspace_dir.stat().st_mtime
                if current_time - mtime > max_age_seconds:
                    shutil.rmtree(workspace_dir)
                    cleaned += 1
                    logger.info(f"Cleaned up old workspace: {workspace_dir.name}")
            except OSError as e:
                logger.warning(f"Failed to check/clean workspace {workspace_dir}: {e}")
        
        return cleaned
