"""JWT Token management for authentication."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pydantic import BaseModel

from dataagent_server.config import get_settings

logger = logging.getLogger(__name__)

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = "dataagent-secret-key-change-in-production"  # Should be from env
JWT_EXPIRATION_HOURS = 1


class TokenPayload(BaseModel):
    """JWT token payload."""
    
    user_id: str
    username: str
    exp: datetime
    iat: datetime
    sub: str = "access"


class TokenResponse(BaseModel):
    """Token response model."""
    
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict[str, Any]


def create_access_token(
    user_id: str,
    username: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token.
    
    Args:
        user_id: User ID
        username: Username
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expire,
        "iat": now,
        "sub": "access",
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> TokenPayload | None:
    """Decode and validate JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_token_expiration_seconds() -> int:
    """Get token expiration time in seconds."""
    return JWT_EXPIRATION_HOURS * 3600
