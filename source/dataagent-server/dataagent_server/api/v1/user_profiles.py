"""User profile API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from dataagent_server.auth import get_api_key
from dataagent_server.models import (
    UserProfileRequest,
    UserProfileResponse,
    UserProfileListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-profiles", tags=["user-profiles"])


def _get_profile_store(request: Request):
    """Get user profile store from app state."""
    store = getattr(request.app.state, "user_profile_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User profile store not initialized",
        )
    return store


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> UserProfileResponse:
    """获取用户档案。
    
    Args:
        user_id: 用户唯一标识。
        
    Returns:
        用户档案信息。
        
    Raises:
        HTTPException: 如果用户不存在。
    """
    store = _get_profile_store(request)
    
    profile = await store.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile not found: {user_id}",
        )
    
    return UserProfileResponse(
        user_id=profile.user_id,
        username=profile.username,
        display_name=profile.display_name,
        email=profile.email,
        department=profile.department,
        role=profile.role,
        custom_fields=profile.custom_fields,
        created_at=profile.created_at.isoformat() if profile.created_at else None,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )


@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_user_profile(
    profile_request: UserProfileRequest,
    request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> UserProfileResponse:
    """创建用户档案。
    
    Args:
        profile_request: 用户档案请求。
        
    Returns:
        创建的用户档案。
    """
    from dataagent_core.user import UserProfile
    
    store = _get_profile_store(request)
    
    # Check if profile already exists
    existing = await store.get_profile(profile_request.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User profile already exists: {profile_request.user_id}",
        )
    
    # Create profile
    profile = UserProfile(
        user_id=profile_request.user_id,
        username=profile_request.username,
        display_name=profile_request.display_name,
        email=profile_request.email,
        department=profile_request.department,
        role=profile_request.role,
        custom_fields=profile_request.custom_fields or {},
    )
    
    await store.save_profile(profile)
    logger.info(f"Created user profile: {profile.user_id}")
    
    return UserProfileResponse(
        user_id=profile.user_id,
        username=profile.username,
        display_name=profile.display_name,
        email=profile.email,
        department=profile.department,
        role=profile.role,
        custom_fields=profile.custom_fields,
        created_at=profile.created_at.isoformat() if profile.created_at else None,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )


@router.put("/{user_id}", response_model=UserProfileResponse)
async def update_user_profile(
    user_id: str,
    profile_request: UserProfileRequest,
    request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> UserProfileResponse:
    """更新用户档案。
    
    Args:
        user_id: 用户唯一标识。
        profile_request: 用户档案请求。
        
    Returns:
        更新后的用户档案。
        
    Raises:
        HTTPException: 如果用户不存在。
    """
    from dataagent_core.user import UserProfile
    
    store = _get_profile_store(request)
    
    # Check if profile exists
    existing = await store.get_profile(user_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile not found: {user_id}",
        )
    
    # Update profile
    profile = UserProfile(
        user_id=user_id,
        username=profile_request.username,
        display_name=profile_request.display_name,
        email=profile_request.email,
        department=profile_request.department,
        role=profile_request.role,
        custom_fields=profile_request.custom_fields or {},
        created_at=existing.created_at,
    )
    
    await store.save_profile(profile)
    logger.info(f"Updated user profile: {user_id}")
    
    return UserProfileResponse(
        user_id=profile.user_id,
        username=profile.username,
        display_name=profile.display_name,
        email=profile.email,
        department=profile.department,
        role=profile.role,
        custom_fields=profile.custom_fields,
        created_at=profile.created_at.isoformat() if profile.created_at else None,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )


@router.delete("/{user_id}")
async def delete_user_profile(
    user_id: str,
    request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> dict:
    """删除用户档案。
    
    Args:
        user_id: 用户唯一标识。
        
    Returns:
        删除结果。
        
    Raises:
        HTTPException: 如果用户不存在。
    """
    store = _get_profile_store(request)
    
    deleted = await store.delete_profile(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile not found: {user_id}",
        )
    
    logger.info(f"Deleted user profile: {user_id}")
    return {"success": True, "message": f"User profile deleted: {user_id}"}


@router.get("", response_model=UserProfileListResponse)
async def list_user_profiles(
    request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> UserProfileListResponse:
    """列出所有用户档案。
    
    Returns:
        用户档案列表。
    """
    store = _get_profile_store(request)
    
    profiles = await store.list_profiles()
    
    return UserProfileListResponse(
        profiles=[
            UserProfileResponse(
                user_id=p.user_id,
                username=p.username,
                display_name=p.display_name,
                email=p.email,
                department=p.department,
                role=p.role,
                custom_fields=p.custom_fields,
                created_at=p.created_at.isoformat() if p.created_at else None,
                updated_at=p.updated_at.isoformat() if p.updated_at else None,
            )
            for p in profiles
        ],
        total=len(profiles),
    )
