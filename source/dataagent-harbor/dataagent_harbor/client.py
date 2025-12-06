"""HTTP client for DataAgent Server."""

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator

import httpx
import websockets

logger = logging.getLogger(__name__)


class DataAgentClient:
    """Async HTTP/WebSocket client for DataAgent Server.
    
    Supports both REST API and WebSocket connections for testing.
    
    Args:
        base_url: Base URL of the DataAgent Server.
        api_key: API key for authentication.
        timeout: Request timeout in seconds.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._http_client: httpx.AsyncClient | None = None
    
    @property
    def headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            )
        return self._http_client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def health_check(self) -> dict[str, Any]:
        """Check server health.
        
        Returns:
            Health check response with status, version, uptime.
        """
        client = await self._get_client()
        response = await client.get("/api/v1/health")
        response.raise_for_status()
        return response.json()
    
    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        assistant_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat message via REST API.
        
        Args:
            message: The message to send.
            session_id: Optional session ID.
            assistant_id: Optional assistant ID.
            
        Returns:
            Chat response with session_id and events.
        """
        client = await self._get_client()
        
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        if assistant_id:
            payload["assistant_id"] = assistant_id
        
        response = await client.post("/api/v1/chat", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def chat_stream(
        self,
        message: str,
        session_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a chat message via WebSocket and stream events.
        
        Args:
            message: The message to send.
            session_id: Session ID for the chat.
            
        Yields:
            Server events as dictionaries.
        """
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws/chat/{session_id}"
        
        extra_headers = {}
        if self.api_key:
            extra_headers["X-API-Key"] = self.api_key
        
        async with websockets.connect(
            ws_url,
            extra_headers=extra_headers,
            close_timeout=10,
        ) as ws:
            # Send chat message
            await ws.send(json.dumps({
                "type": "chat",
                "payload": {"message": message},
            }))
            
            # Receive events until done
            async for msg in ws:
                event = json.loads(msg)
                yield event
                
                # Check if this is the done event
                if event.get("event_type") == "done":
                    break
    
    async def cancel_chat(self, session_id: str) -> dict[str, Any]:
        """Cancel an ongoing chat session.
        
        Args:
            session_id: Session ID to cancel.
            
        Returns:
            Cancellation response.
        """
        client = await self._get_client()
        response = await client.post(f"/api/v1/chat/{session_id}/cancel")
        response.raise_for_status()
        return response.json()
    
    async def get_sessions(self, user_id: str | None = None) -> dict[str, Any]:
        """Get list of sessions.
        
        Args:
            user_id: Optional user ID to filter.
            
        Returns:
            Session list response.
        """
        client = await self._get_client()
        params = {}
        if user_id:
            params["user_id"] = user_id
        response = await client.get("/api/v1/sessions", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session details.
        
        Args:
            session_id: Session ID.
            
        Returns:
            Session info.
        """
        client = await self._get_client()
        response = await client.get(f"/api/v1/sessions/{session_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get message history for a session.
        
        Args:
            session_id: Session ID.
            limit: Maximum messages to return.
            offset: Number of messages to skip.
            
        Returns:
            Message list response.
        """
        client = await self._get_client()
        response = await client.get(
            f"/api/v1/sessions/{session_id}/messages",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session.
        
        Args:
            session_id: Session ID to delete.
        """
        client = await self._get_client()
        response = await client.delete(f"/api/v1/sessions/{session_id}")
        response.raise_for_status()


class TimedResponse:
    """Response with timing information."""
    
    def __init__(
        self,
        data: dict[str, Any],
        response_time: float,
        status_code: int = 200,
    ) -> None:
        self.data = data
        self.response_time = response_time
        self.status_code = status_code


async def timed_chat(
    client: DataAgentClient,
    message: str,
    session_id: str | None = None,
    use_websocket: bool = False,
) -> TimedResponse:
    """Execute a chat request with timing.
    
    Args:
        client: DataAgent client.
        message: Message to send.
        session_id: Optional session ID.
        use_websocket: Whether to use WebSocket instead of REST.
        
    Returns:
        TimedResponse with data and timing.
    """
    start_time = time.time()
    
    if use_websocket and session_id:
        # Collect all events from WebSocket
        events = []
        text_content = []
        
        async for event in client.chat_stream(message, session_id):
            events.append(event)
            if event.get("event_type") == "text":
                text_content.append(event.get("data", {}).get("content", ""))
        
        response_time = time.time() - start_time
        
        return TimedResponse(
            data={
                "session_id": session_id,
                "events": events,
                "text": "".join(text_content),
            },
            response_time=response_time,
        )
    else:
        # Use REST API
        data = await client.chat(message, session_id)
        response_time = time.time() - start_time
        
        # Extract text from events
        text_content = []
        for event in data.get("events", []):
            if event.get("event_type") == "text":
                text_content.append(event.get("content", ""))
        
        data["text"] = "".join(text_content)
        
        return TimedResponse(
            data=data,
            response_time=response_time,
        )
