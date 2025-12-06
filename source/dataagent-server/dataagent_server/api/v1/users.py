"""User management REST API endpoints."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from dataagent_server.api.deps import get_current_user_id
from dataagent_server.config import get_settings

router = APIRouter(prefix="/users/{user_id}", tags=["Users"])


class MemoryDeleteResponse(BaseModel):
    """Response model for memory deletion."""
    
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")


def _check_user_access(user_id: str, current_user_id: str) -> None:
    """Check if current user can access the target user's resources."""
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's resources",
        )


def _get_user_memory_path(user_id: str) -> Path:
    """Get the memory path for a user."""
    # Memory is stored in ~/.deepagents/users/{user_id}/
    return Path.home() / ".deepagents" / "users" / user_id


@router.delete("/memory", response_model=MemoryDeleteResponse)
async def delete_user_memory(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> MemoryDeleteResponse:
    """Delete all memory for a user.
    
    This removes the user's agent memory directory, clearing all
    stored preferences and context.
    """
    _check_user_access(user_id, current_user_id)
    
    memory_path = _get_user_memory_path(user_id)
    
    if not memory_path.exists():
        return MemoryDeleteResponse(
            success=True,
            message=f"No memory found for user {user_id}",
        )
    
    try:
        shutil.rmtree(memory_path)
        return MemoryDeleteResponse(
            success=True,
            message=f"Memory cleared for user {user_id}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear memory: {e}",
        )


@router.get("/memory/status")
async def get_user_memory_status(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Get memory status for a user."""
    _check_user_access(user_id, current_user_id)
    
    memory_path = _get_user_memory_path(user_id)
    
    if not memory_path.exists():
        return {
            "exists": False,
            "path": str(memory_path),
            "size_bytes": 0,
            "file_count": 0,
        }
    
    # Calculate size and file count
    size_bytes = 0
    file_count = 0
    
    for root, dirs, files in memory_path.walk():
        for f in files:
            file_path = root / f
            try:
                size_bytes += file_path.stat().st_size
                file_count += 1
            except OSError:
                pass
    
    return {
        "exists": True,
        "path": str(memory_path),
        "size_bytes": size_bytes,
        "file_count": file_count,
    }
