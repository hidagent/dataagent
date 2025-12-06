"""Chat endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from dataagent_server.auth import get_api_key
from dataagent_server.models import CancelResponse, ChatRequest, ChatResponse
from dataagent_core.engine import AgentExecutor, AgentConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Store executors for REST API sessions
_rest_executors: dict[str, AgentExecutor] = {}


def _get_or_create_executor(
    session_id: str,
    agent_factory,
) -> AgentExecutor:
    """Get or create an AgentExecutor for the session.
    
    Args:
        session_id: Session ID.
        agent_factory: AgentFactory instance.
        
    Returns:
        AgentExecutor instance.
    """
    if session_id in _rest_executors:
        return _rest_executors[session_id]
    
    # Create agent config
    config = AgentConfig(
        assistant_id=f"rest-{session_id[:8]}",
        auto_approve=True,  # Auto-approve for REST API (no HITL support)
    )
    
    # Create agent and backend
    agent, backend = agent_factory.create_agent(config)
    
    # Create executor (no HITL handler for REST API)
    executor = AgentExecutor(
        agent=agent,
        backend=backend,
        hitl_handler=None,
        assistant_id=config.assistant_id,
    )
    
    _rest_executors[session_id] = executor
    return executor


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    http_request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> ChatResponse:
    """Send a message to the agent (synchronous).
    
    This endpoint processes the message and returns all events
    once the agent completes its response.
    
    Args:
        request: Chat request with message and optional session/assistant IDs.
        
    Returns:
        Chat response with session ID and list of events.
    """
    # Get agent factory from app state
    agent_factory = getattr(http_request.app.state, "agent_factory", None)
    
    if agent_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent factory not initialized",
        )
    
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get or create executor
    try:
        executor = _get_or_create_executor(session_id, agent_factory)
    except Exception as e:
        logger.exception("Failed to create executor")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent executor: {e}",
        )
    
    # Execute and collect all events
    events = []
    try:
        async for event in executor.execute(request.message, session_id):
            events.append(event.to_dict())
    except Exception as e:
        logger.exception("Error during agent execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e}",
        )
    
    return ChatResponse(
        session_id=session_id,
        events=events,
    )


@router.post("/{session_id}/cancel", response_model=CancelResponse)
async def cancel_chat(
    session_id: str,
    http_request: Request,
    _api_key: str | None = Depends(get_api_key),
) -> CancelResponse:
    """Cancel an ongoing chat session.
    
    This endpoint terminates any active agent execution for the
    specified session.
    
    Args:
        session_id: The session ID to cancel.
        
    Returns:
        Cancellation status.
        
    Raises:
        HTTPException: If no active chat found for the session.
    """
    # Get connection manager from app state
    connection_manager = getattr(http_request.app.state, "connection_manager", None)
    
    if connection_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    
    # Try to cancel the task
    cancelled = await connection_manager.cancel_task(session_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active chat found for session {session_id}",
        )
    
    return CancelResponse(
        status="cancelled",
        session_id=session_id,
    )
