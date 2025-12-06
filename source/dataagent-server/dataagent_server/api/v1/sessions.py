"""Session management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from dataagent_server.auth import get_api_key
from dataagent_server.models import (
    MessageInfo,
    MessageListResponse,
    SessionInfo,
    SessionListResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_session_store(request: Request):
    """Get session store from app state."""
    return request.app.state.session_store


def get_message_store(request: Request):
    """Get message store from app state."""
    return request.app.state.message_store


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    user_id: str | None = Query(None, description="Filter by user ID"),
    _api_key: str | None = Depends(get_api_key),
) -> SessionListResponse:
    """List all sessions.
    
    Args:
        user_id: Optional user ID to filter sessions.
        
    Returns:
        A list of session information.
    """
    session_store = get_session_store(request)
    
    if user_id:
        sessions = await session_store.list_by_user(user_id)
    else:
        # For now, return empty list if no user_id specified
        # In production, this should be restricted or paginated
        sessions = []
    
    session_infos = [
        SessionInfo(
            session_id=s.session_id,
            user_id=s.user_id,
            assistant_id=s.assistant_id,
            created_at=s.created_at,
            last_active=s.last_active,
        )
        for s in sessions
    ]
    
    return SessionListResponse(sessions=session_infos, total=len(session_infos))


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    request: Request,
    session_id: str,
    _api_key: str | None = Depends(get_api_key),
) -> SessionInfo:
    """Get session details by ID.
    
    Args:
        session_id: The session ID to retrieve.
        
    Returns:
        Session information.
        
    Raises:
        HTTPException: If session not found.
    """
    session_store = get_session_store(request)
    session = await session_store.get(session_id)
    
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    return SessionInfo(
        session_id=session.session_id,
        user_id=session.user_id,
        assistant_id=session.assistant_id,
        created_at=session.created_at,
        last_active=session.last_active,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    request: Request,
    session_id: str,
    _api_key: str | None = Depends(get_api_key),
) -> None:
    """Delete a session by ID.
    
    Args:
        session_id: The session ID to delete.
        
    Raises:
        HTTPException: If session not found.
    """
    session_store = get_session_store(request)
    session = await session_store.get(session_id)
    
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    await session_store.delete(session_id)


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    request: Request,
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    _api_key: str | None = Depends(get_api_key),
) -> MessageListResponse:
    """Get message history for a session.
    
    Args:
        session_id: The session ID to get messages for.
        limit: Maximum number of messages to return (1-1000).
        offset: Number of messages to skip for pagination.
        
    Returns:
        List of messages ordered by creation time (oldest first).
        
    Raises:
        HTTPException: If session not found.
    """
    session_store = get_session_store(request)
    message_store = get_message_store(request)
    
    # Verify session exists
    session = await session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    # Get messages
    messages = await message_store.get_messages(session_id, limit=limit, offset=offset)
    total = await message_store.count_messages(session_id)
    
    message_infos = [
        MessageInfo(
            message_id=m.message_id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            metadata=m.metadata,
        )
        for m in messages
    ]
    
    return MessageListResponse(
        messages=message_infos,
        total=total,
        limit=limit,
        offset=offset,
    )
