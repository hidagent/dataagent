"""Chat-related Pydantic models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from dataagent_server.models.user import UserContextRequest


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    
    message: str = Field(..., description="User message to send to the agent")
    session_id: str | None = Field(None, description="Optional session ID to continue conversation")
    assistant_id: str | None = Field(None, description="Optional assistant ID to use")
    user_context: UserContextRequest | None = Field(None, description="Optional user context for personalization")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    session_id: str = Field(..., description="Session ID for the conversation")
    events: list[dict] = Field(default_factory=list, description="List of execution events")


class SessionInfo(BaseModel):
    """Session information model."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    assistant_id: str = Field(..., description="Assistant identifier")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_active: datetime = Field(..., description="Last activity timestamp")


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""
    
    sessions: list[SessionInfo] = Field(default_factory=list, description="List of sessions")
    total: int = Field(0, description="Total number of sessions")


class MessageInfo(BaseModel):
    """Message information model."""
    
    message_id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Session identifier")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Message creation timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class MessageListResponse(BaseModel):
    """Response model for listing messages."""
    
    messages: list[MessageInfo] = Field(default_factory=list, description="List of messages")
    total: int = Field(0, description="Total number of messages")
    limit: int = Field(100, description="Maximum messages returned")
    offset: int = Field(0, description="Number of messages skipped")
