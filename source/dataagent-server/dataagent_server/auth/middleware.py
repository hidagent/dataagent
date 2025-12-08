"""Authentication middleware for FastAPI."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dataagent_server.auth.jwt import decode_access_token, TokenPayload
from dataagent_server.config import get_settings

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for JWT
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[TokenPayload]:
    """Get current user from JWT token.
    
    Args:
        request: FastAPI request
        credentials: Bearer token credentials
        
    Returns:
        TokenPayload if valid token, None if auth disabled
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    settings = get_settings()
    
    # Skip auth if disabled
    if settings.auth_disabled:
        return None
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_payload = decode_access_token(credentials.credentials)
    
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_payload


async def get_optional_user_from_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[TokenPayload]:
    """Get current user from JWT token (optional).
    
    Does not raise exception if token is missing.
    
    Args:
        request: FastAPI request
        credentials: Bearer token credentials
        
    Returns:
        TokenPayload if valid token, None otherwise
    """
    if not credentials:
        return None
    
    return decode_access_token(credentials.credentials)


def require_user_match(user_id_param: str = "user_id"):
    """Dependency factory to require user ID match.
    
    Args:
        user_id_param: Name of the path parameter containing user ID
        
    Returns:
        Dependency function
    """
    async def dependency(
        request: Request,
        token: Optional[TokenPayload] = Depends(get_current_user_from_token),
    ) -> str:
        """Verify user ID matches token.
        
        Args:
            request: FastAPI request
            token: Token payload
            
        Returns:
            User ID from path
            
        Raises:
            HTTPException: If user ID doesn't match
        """
        settings = get_settings()
        
        # Get user_id from path
        path_user_id = request.path_params.get(user_id_param)
        
        # If auth disabled, use header or path user_id
        if settings.auth_disabled:
            header_user_id = request.headers.get("X-User-ID")
            return header_user_id or path_user_id or settings.default_user
        
        # Verify token user matches path user
        if token and path_user_id and token.user_id != path_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: user ID mismatch",
            )
        
        return token.user_id if token else path_user_id
    
    return dependency
