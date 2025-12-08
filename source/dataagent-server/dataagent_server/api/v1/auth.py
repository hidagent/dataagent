"""Authentication API endpoints."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataagent_server.auth import (
    create_access_token,
    get_token_expiration_seconds,
    hash_password,
    verify_password,
    TokenResponse,
)
from dataagent_server.database import get_db_session, SUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request model."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response model."""
    
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict[str, Any]


class RegisterRequest(BaseModel):
    """User registration request."""
    
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=128)
    email: str | None = Field(None, max_length=256)
    user_account: str | None = Field(None, max_length=128, description="Domain account")
    user_source: str = Field("local", description="User source: local, ldap, oauth, sso")
    department: str | None = Field(None, max_length=128)
    role: str | None = Field(None, max_length=64)


class UserResponse(BaseModel):
    """User response model."""
    
    user_id: str
    username: str
    user_account: str | None
    user_source: str
    display_name: str
    email: str | None
    department: str | None
    role: str | None
    status: str
    created_at: datetime
    last_login_at: datetime | None


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    """User login endpoint.
    
    Args:
        request: FastAPI request
        body: Login credentials
        
    Returns:
        JWT token and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    async with get_db_session() as session:
        # Find user by username
        result = await session.execute(
            select(SUser).where(SUser.username == body.username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        # Verify password
        if not user.password_hash or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        # Check user status
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User account is {user.status}",
            )
        
        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        
        # Create access token
        access_token = create_access_token(user.user_id, user.username)
        
        logger.info(f"User logged in: {user.username}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=get_token_expiration_seconds(),
            user={
                "user_id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "department": user.department,
                "role": user.role,
            },
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: Request, body: RegisterRequest) -> UserResponse:
    """Register a new user.
    
    Args:
        request: FastAPI request
        body: Registration data
        
    Returns:
        Created user info
        
    Raises:
        HTTPException: If username already exists
    """
    async with get_db_session() as session:
        # Check if username exists
        result = await session.execute(
            select(SUser).where(SUser.username == body.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )
        
        # Create user
        user = SUser(
            user_id=str(uuid.uuid4())[:8],
            username=body.username,
            password_hash=hash_password(body.password),
            display_name=body.display_name,
            email=body.email,
            user_account=body.user_account,
            user_source=body.user_source,
            department=body.department,
            role=body.role,
            status="active",
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"User registered: {user.username}")
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            user_account=user.user_account,
            user_source=user.user_source,
            display_name=user.display_name,
            email=user.email,
            department=user.department,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    """User logout endpoint.
    
    Currently just returns success. In production, implement token blacklist.
    
    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}
