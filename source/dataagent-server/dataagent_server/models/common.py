"""Common Pydantic models."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error_code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class WebSocketMessage(BaseModel):
    """WebSocket message model for client messages."""
    
    type: str = Field(..., description="Message type: chat, hitl_decision, cancel, ping")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")


class ServerEvent(BaseModel):
    """Server event model for WebSocket responses."""
    
    event_type: str = Field(..., description="Event type from ExecutionEvent")
    data: dict[str, Any] = Field(default_factory=dict, description="Event data")
    timestamp: float = Field(..., description="Event timestamp")
    request_id: str | None = Field(None, description="Optional request ID for tracking")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service status: ok, degraded, unhealthy")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")


class CancelResponse(BaseModel):
    """Response model for cancel endpoint."""
    
    status: str = Field(..., description="Cancellation status")
    session_id: str = Field(..., description="Session ID that was cancelled")
