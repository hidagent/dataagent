"""Workspace management API endpoints.

Provides CRUD operations for user workspaces with multi-tenant isolation.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dataagent_server.api.deps import get_current_user_id
from dataagent_server.database.factory import get_db_session
from dataagent_server.database.models import SWorkspace, SUserWorkspaceRel, SUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# =============================================================================
# Request/Response Models
# =============================================================================

class WorkspaceCreate(BaseModel):
    """Request model for creating a workspace."""
    
    name: str = Field(..., min_length=1, max_length=128, description="Workspace name")
    path: str = Field(..., min_length=1, max_length=512, description="Filesystem path")
    description: str | None = Field(None, max_length=1024, description="Workspace description")
    max_size_bytes: int = Field(default=1073741824, ge=0, description="Max size in bytes (default 1GB)")
    max_files: int = Field(default=10000, ge=0, description="Max number of files")
    is_default: bool = Field(default=False, description="Set as default workspace")


class WorkspaceUpdate(BaseModel):
    """Request model for updating a workspace."""
    
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=1024)
    max_size_bytes: int | None = Field(None, ge=0)
    max_files: int | None = Field(None, ge=0)
    is_default: bool | None = Field(None)
    is_active: bool | None = Field(None)


class WorkspaceResponse(BaseModel):
    """Response model for workspace data."""
    
    workspace_id: str
    name: str
    path: str
    description: str | None
    max_size_bytes: int
    max_files: int
    current_size_bytes: int
    current_file_count: int
    is_default: bool
    is_active: bool
    permission: str
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None


class WorkspaceListResponse(BaseModel):
    """Response model for workspace list."""
    
    workspaces: list[WorkspaceResponse]
    total: int


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceListResponse:
    """List all workspaces for the current user."""
    
    async with get_db_session() as db:
        # Query workspaces with user relationship
        result = await db.execute(
            select(SWorkspace, SUserWorkspaceRel)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(SUserWorkspaceRel.user_id == user_id)
            .order_by(SUserWorkspaceRel.is_default.desc(), SWorkspace.name)
        )
        rows = result.all()
        
        workspaces = []
        for workspace, rel in rows:
            workspaces.append(WorkspaceResponse(
                workspace_id=workspace.workspace_id,
                name=workspace.name,
                path=workspace.path,
                description=workspace.description,
                max_size_bytes=workspace.max_size_bytes,
                max_files=workspace.max_files,
                current_size_bytes=workspace.current_size_bytes,
                current_file_count=workspace.current_file_count,
                is_default=rel.is_default,
                is_active=workspace.is_active,
                permission=rel.permission,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                last_accessed_at=workspace.last_accessed_at,
            ))
        
        return WorkspaceListResponse(workspaces=workspaces, total=len(workspaces))


@router.get("/default", response_model=WorkspaceResponse | None)
async def get_default_workspace(
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceResponse | None:
    """Get the default workspace for the current user."""
    
    async with get_db_session() as db:
        result = await db.execute(
            select(SWorkspace, SUserWorkspaceRel)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SUserWorkspaceRel.user_id == user_id,
                    SUserWorkspaceRel.is_default == True,
                )
            )
        )
        row = result.first()
        
        if not row:
            return None
        
        workspace, rel = row
        return WorkspaceResponse(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            path=workspace.path,
            description=workspace.description,
            max_size_bytes=workspace.max_size_bytes,
            max_files=workspace.max_files,
            current_size_bytes=workspace.current_size_bytes,
            current_file_count=workspace.current_file_count,
            is_default=rel.is_default,
            is_active=workspace.is_active,
            permission=rel.permission,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_accessed_at=workspace.last_accessed_at,
        )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceResponse:
    """Create a new workspace for the current user."""
    now = datetime.now(timezone.utc)
    
    async with get_db_session() as db:
        # Generate workspace ID
        workspace_id = str(uuid.uuid4())
        
        # If setting as default, unset other defaults first
        if workspace_data.is_default:
            await _unset_default_workspace(db, user_id)
        
        # Create workspace
        workspace = SWorkspace(
            workspace_id=workspace_id,
            name=workspace_data.name,
            path=workspace_data.path,
            description=workspace_data.description,
            max_size_bytes=workspace_data.max_size_bytes,
            max_files=workspace_data.max_files,
            current_size_bytes=0,
            current_file_count=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(workspace)
        
        # Create user-workspace relationship
        rel = SUserWorkspaceRel(
            user_id=user_id,
            workspace_id=workspace_id,
            is_default=workspace_data.is_default,
            permission="admin",  # Creator gets admin permission
            created_at=now,
        )
        db.add(rel)
        
        await db.commit()
        
        logger.info(f"Created workspace {workspace_id} for user {user_id}")
        
        return WorkspaceResponse(
            workspace_id=workspace_id,
            name=workspace.name,
            path=workspace.path,
            description=workspace.description,
            max_size_bytes=workspace.max_size_bytes,
            max_files=workspace.max_files,
            current_size_bytes=0,
            current_file_count=0,
            is_default=workspace_data.is_default,
            is_active=True,
            permission="admin",
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
        )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceResponse:
    """Get a specific workspace by ID."""
    
    async with get_db_session() as db:
        result = await db.execute(
            select(SWorkspace, SUserWorkspaceRel)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SWorkspace.workspace_id == workspace_id,
                    SUserWorkspaceRel.user_id == user_id,
                )
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {workspace_id} not found",
            )
        
        workspace, rel = row
        return WorkspaceResponse(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            path=workspace.path,
            description=workspace.description,
            max_size_bytes=workspace.max_size_bytes,
            max_files=workspace.max_files,
            current_size_bytes=workspace.current_size_bytes,
            current_file_count=workspace.current_file_count,
            is_default=rel.is_default,
            is_active=workspace.is_active,
            permission=rel.permission,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_accessed_at=workspace.last_accessed_at,
        )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceResponse:
    """Update a workspace."""
    now = datetime.now(timezone.utc)
    
    async with get_db_session() as db:
        # Get workspace with permission check
        result = await db.execute(
            select(SWorkspace, SUserWorkspaceRel)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SWorkspace.workspace_id == workspace_id,
                    SUserWorkspaceRel.user_id == user_id,
                )
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {workspace_id} not found",
            )
        
        workspace, rel = row
        
        # Check permission
        if rel.permission not in ("admin", "read_write"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission to update workspace",
            )
        
        # Update workspace fields
        if workspace_data.name is not None:
            workspace.name = workspace_data.name
        if workspace_data.description is not None:
            workspace.description = workspace_data.description
        if workspace_data.max_size_bytes is not None:
            workspace.max_size_bytes = workspace_data.max_size_bytes
        if workspace_data.max_files is not None:
            workspace.max_files = workspace_data.max_files
        if workspace_data.is_active is not None:
            workspace.is_active = workspace_data.is_active
        
        workspace.updated_at = now
        
        # Update default status
        if workspace_data.is_default is not None:
            if workspace_data.is_default:
                await _unset_default_workspace(db, user_id)
            rel.is_default = workspace_data.is_default
        
        await db.commit()
        
        logger.info(f"Updated workspace {workspace_id}")
        
        return WorkspaceResponse(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            path=workspace.path,
            description=workspace.description,
            max_size_bytes=workspace.max_size_bytes,
            max_files=workspace.max_files,
            current_size_bytes=workspace.current_size_bytes,
            current_file_count=workspace.current_file_count,
            is_default=rel.is_default,
            is_active=workspace.is_active,
            permission=rel.permission,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_accessed_at=workspace.last_accessed_at,
        )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Delete a workspace."""
    
    async with get_db_session() as db:
        # Get workspace with permission check
        result = await db.execute(
            select(SWorkspace, SUserWorkspaceRel)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SWorkspace.workspace_id == workspace_id,
                    SUserWorkspaceRel.user_id == user_id,
                )
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {workspace_id} not found",
            )
        
        workspace, rel = row
        
        # Check permission
        if rel.permission != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can delete workspace",
            )
        
        # Delete relationship and workspace
        await db.delete(rel)
        await db.delete(workspace)
        await db.commit()
        
        logger.info(f"Deleted workspace {workspace_id}")


@router.post("/{workspace_id}/set-default", response_model=WorkspaceResponse)
async def set_default_workspace(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceResponse:
    """Set a workspace as the default for the current user."""
    
    async with get_db_session() as db:
        # Get workspace
        result = await db.execute(
            select(SWorkspace, SUserWorkspaceRel)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SWorkspace.workspace_id == workspace_id,
                    SUserWorkspaceRel.user_id == user_id,
                )
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {workspace_id} not found",
            )
        
        workspace, rel = row
        
        # Unset other defaults
        await _unset_default_workspace(db, user_id)
        
        # Set this as default
        rel.is_default = True
        await db.commit()
        
        logger.info(f"Set workspace {workspace_id} as default for user {user_id}")
        
        return WorkspaceResponse(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            path=workspace.path,
            description=workspace.description,
            max_size_bytes=workspace.max_size_bytes,
            max_files=workspace.max_files,
            current_size_bytes=workspace.current_size_bytes,
            current_file_count=workspace.current_file_count,
            is_default=True,
            is_active=workspace.is_active,
            permission=rel.permission,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_accessed_at=workspace.last_accessed_at,
        )


# =============================================================================
# Helper Functions
# =============================================================================

async def _unset_default_workspace(db: AsyncSession, user_id: str) -> None:
    """Unset all default workspaces for a user."""
    result = await db.execute(
        select(SUserWorkspaceRel).where(
            and_(
                SUserWorkspaceRel.user_id == user_id,
                SUserWorkspaceRel.is_default == True,
            )
        )
    )
    for rel in result.scalars():
        rel.is_default = False


async def get_user_default_workspace_path(user_id: str) -> str | None:
    """Get the default workspace path for a user.
    
    This is a utility function that can be used by other modules.
    
    Args:
        user_id: The user ID.
        
    Returns:
        The workspace path or None if no default workspace.
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(SWorkspace)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SUserWorkspaceRel.user_id == user_id,
                    SUserWorkspaceRel.is_default == True,
                    SWorkspace.is_active == True,
                )
            )
        )
        workspace = result.scalar_one_or_none()
        
        if workspace:
            return workspace.path
        
        return None


async def ensure_user_default_workspace(
    user_id: str,
    base_path: str = "/var/dataagent/workspaces",
) -> str:
    """Ensure a user has a default workspace, creating one if needed.
    
    This function will also ensure the user exists in the database before
    creating the workspace relationship (to satisfy foreign key constraints).
    
    If the configured base_path is not writable, falls back to ~/.dataagent/workspaces.
    
    Args:
        user_id: The user ID.
        base_path: Base path for user workspaces.
        
    Returns:
        The workspace path.
    """
    import os
    from pathlib import Path
    
    async with get_db_session() as db:
        # Check for existing default workspace
        result = await db.execute(
            select(SWorkspace)
            .join(SUserWorkspaceRel, SWorkspace.workspace_id == SUserWorkspaceRel.workspace_id)
            .where(
                and_(
                    SUserWorkspaceRel.user_id == user_id,
                    SUserWorkspaceRel.is_default == True,
                )
            )
        )
        workspace = result.scalar_one_or_none()
        
        if workspace:
            logger.debug(f"Found existing workspace for user {user_id}: {workspace.path}")
            return workspace.path
        
        # Ensure user exists in database (required for foreign key constraint)
        user_result = await db.execute(
            select(SUser).where(SUser.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            # User must exist to create workspace relationship
            logger.error(f"User {user_id} not found in database, cannot create workspace")
            raise ValueError(f"User {user_id} not found in database")
        
        # Create default workspace
        now = datetime.now(timezone.utc)
        workspace_id = str(uuid.uuid4())
        
        # Sanitize user_id for path
        safe_user_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in user_id)
        
        # Try to create directory, fall back to home directory if base_path is not writable
        workspace_path = str(Path(base_path) / safe_user_id)
        try:
            os.makedirs(workspace_path, exist_ok=True)
            logger.info(f"Created workspace directory: {workspace_path}")
        except (PermissionError, OSError) as e:
            # Fall back to user's home directory
            fallback_base = Path.home() / ".dataagent" / "workspaces"
            workspace_path = str(fallback_base / safe_user_id)
            logger.warning(
                f"Cannot create workspace at {base_path}/{safe_user_id}: {e}. "
                f"Falling back to {workspace_path}"
            )
            os.makedirs(workspace_path, exist_ok=True)
        
        # Create workspace record
        workspace = SWorkspace(
            workspace_id=workspace_id,
            name=f"{user_id}'s Workspace",
            path=workspace_path,
            description="Default workspace",
            max_size_bytes=1073741824,  # 1GB
            max_files=10000,
            current_size_bytes=0,
            current_file_count=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(workspace)
        
        # Create relationship
        rel = SUserWorkspaceRel(
            user_id=user_id,
            workspace_id=workspace_id,
            is_default=True,
            permission="admin",
            created_at=now,
        )
        db.add(rel)
        
        await db.commit()
        
        logger.info(f"Created default workspace for user {user_id}: {workspace_path}")
        
        return workspace_path
