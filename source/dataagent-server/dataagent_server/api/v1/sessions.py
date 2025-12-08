"""Session management endpoints.

Uses the server's s_session table for session data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from dataagent_server.auth import get_api_key
from dataagent_server.database.factory import get_db_session
from dataagent_server.database.models import SSession, SMessage, SSessionMessageRel
from dataagent_server.models import (
    MessageInfo,
    MessageListResponse,
    SessionInfo,
    SessionListResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: str | None = Query(None, description="Filter by user ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    _api_key: str | None = Depends(get_api_key),
) -> SessionListResponse:
    """List all sessions.
    
    Args:
        user_id: Optional user ID to filter sessions.
        limit: Maximum number of sessions to return (1-100).
        offset: Number of sessions to skip for pagination.
        
    Returns:
        A list of session information.
    """
    async with get_db_session() as db:
        # Build base query
        base_query = select(SSession)
        if user_id:
            base_query = base_query.where(SSession.user_id == user_id)
        
        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get paginated results
        query = base_query.order_by(SSession.last_active.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        sessions = result.scalars().all()
        
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
        
        return SessionListResponse(sessions=session_infos, total=total)


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
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
    async with get_db_session() as db:
        result = await db.execute(
            select(SSession).where(SSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
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
    session_id: str,
    _api_key: str | None = Depends(get_api_key),
) -> None:
    """Delete a session by ID.
    
    Args:
        session_id: The session ID to delete.
        
    Raises:
        HTTPException: If session not found.
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(SSession).where(SSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        await db.delete(session)
        await db.commit()


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
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
    async with get_db_session() as db:
        # Verify session exists
        result = await db.execute(
            select(SSession).where(SSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Get messages through relationship table
        query = (
            select(SMessage)
            .join(SSessionMessageRel, SMessage.message_id == SSessionMessageRel.message_id)
            .where(SSessionMessageRel.session_id == session_id)
            .order_by(SSessionMessageRel.sequence_number)
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Count total messages
        count_query = (
            select(func.count())
            .select_from(SSessionMessageRel)
            .where(SSessionMessageRel.session_id == session_id)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        message_infos = [
            MessageInfo(
                message_id=m.message_id,
                session_id=session_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                metadata=None,  # extra_data is JSON string, would need parsing
            )
            for m in messages
        ]
        
        return MessageListResponse(
            messages=message_infos,
            total=total,
            limit=limit,
            offset=offset,
        )
