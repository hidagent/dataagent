"""API Key authentication."""

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader

from dataagent_server.config import get_settings

API_KEY_HEADER = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


class APIKeyAuth:
    """API Key authentication dependency.
    
    Validates API keys passed via X-API-Key header.
    Can be disabled via DATAAGENT_AUTH_DISABLED environment variable.
    """
    
    def __init__(self, api_keys: list[str] | None = None, disabled: bool | None = None):
        """Initialize API Key auth.
        
        Args:
            api_keys: List of valid API keys. If None, uses settings.
            disabled: Whether auth is disabled. If None, uses settings.
        """
        self._api_keys = api_keys
        self._disabled = disabled
    
    @property
    def api_keys(self) -> list[str]:
        """Get configured API keys."""
        if self._api_keys is not None:
            return self._api_keys
        return get_settings().api_keys
    
    @property
    def is_disabled(self) -> bool:
        """Check if auth is disabled."""
        if self._disabled is not None:
            return self._disabled
        return get_settings().auth_disabled
    
    async def __call__(self, request: Request) -> str | None:
        """Validate API key from request.
        
        Args:
            request: FastAPI request object.
            
        Returns:
            The validated API key, or None if auth is disabled.
            
        Raises:
            HTTPException: If API key is missing or invalid.
        """
        # Skip auth if disabled
        if self.is_disabled:
            return None
        
        # Skip auth if no API keys configured
        if not self.api_keys:
            return None
        
        # Get API key from header
        api_key = request.headers.get(API_KEY_HEADER)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        return api_key


# Default auth dependency
api_key_auth = APIKeyAuth()


async def get_api_key(request: Request) -> str | None:
    """Dependency to get and validate API key.
    
    Args:
        request: FastAPI request object.
        
    Returns:
        The validated API key, or None if auth is disabled.
    """
    return await api_key_auth(request)
