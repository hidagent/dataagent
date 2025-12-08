"""API client for DataAgent Server."""

import httpx
from typing import Any


class APIClient:
    """HTTP client for DataAgent Server API."""
    
    def __init__(self, base_url: str, token: str | None = None, api_key: str | None = None):
        """Initialize API client.
        
        Args:
            base_url: Server base URL (e.g., http://localhost:8000)
            token: JWT access token
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.api_key = api_key
    
    def _get_headers(self, user_id: str | None = None) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if user_id:
            headers["X-User-ID"] = user_id
        return headers
    
    async def login(self, username: str, password: str) -> dict[str, Any]:
        """Login and get access token.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Login response with token and user info
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    
    async def register(
        self,
        username: str,
        password: str,
        display_name: str,
        email: str | None = None,
        user_account: str | None = None,
        user_source: str = "local",
        department: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Register a new user.
        
        Returns:
            Created user info
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "display_name": display_name,
                    "email": email,
                    "user_account": user_account,
                    "user_source": user_source,
                    "department": department,
                    "role": role,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile data
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/user-profiles/{user_id}",
                headers=self._get_headers(user_id),
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_mcp_servers(self, user_id: str) -> list[dict[str, Any]]:
        """Get MCP servers for user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of MCP server configurations
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{user_id}/mcp-servers",
                headers=self._get_headers(user_id),
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json().get("servers", [])
    
    async def get_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Get user sessions.
        
        Args:
            user_id: User ID
            limit: Max results
            offset: Offset for pagination
            
        Returns:
            Sessions list with pagination info
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions",
                headers=self._get_headers(user_id),
                params={"user_id": user_id, "limit": limit, "offset": offset},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_session_messages(self, session_id: str, user_id: str) -> list[dict[str, Any]]:
        """Get messages for a session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            List of messages
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/messages",
                headers=self._get_headers(user_id),
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json().get("messages", [])
    
    async def check_health(self) -> dict[str, Any] | None:
        """Check server health.
        
        Returns:
            Health status or None if unavailable
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/health",
                    headers=self._get_headers(),
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None
