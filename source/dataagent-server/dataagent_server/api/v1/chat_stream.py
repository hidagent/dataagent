"""Streaming chat endpoints using Server-Sent Events (SSE)."""

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from dataagent_server.auth import get_api_key
from dataagent_server.api.deps import get_current_user_id
from dataagent_server.models import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


async def _event_generator(
    executor,
    message: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from agent execution.
    
    Args:
        executor: AgentExecutor instance.
        message: User message.
        session_id: Session ID.
        
    Yields:
        SSE formatted event strings.
    """
    try:
        async for event in executor.execute(message, session_id):
            event_data = event.to_dict()
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.exception("Error during streaming execution")
        error_event = {
            "event_type": "error",
            "data": {
                "error_code": "EXECUTION_ERROR",
                "message": str(e),
                "recoverable": False,
            },
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    finally:
        # Send done event
        done_event = {"event_type": "stream_end", "data": {}}
        yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
    _api_key: str | None = Depends(get_api_key),
) -> StreamingResponse:
    """Stream chat responses using Server-Sent Events (SSE).
    
    This endpoint provides real-time streaming of agent responses,
    suitable for web frontends that need progressive updates.
    
    Args:
        request: Chat request with message and optional session/assistant IDs.
        user_id: Current user ID from header.
        
    Returns:
        StreamingResponse with SSE events.
        
    Example:
        ```javascript
        const eventSource = new EventSource('/api/v1/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: 'Hello'})
        });
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
        ```
    """
    from dataagent_core.engine import AgentExecutor, AgentConfig
    
    agent_factory = getattr(http_request.app.state, "agent_factory", None)
    mcp_store = getattr(http_request.app.state, "mcp_store", None)
    mcp_connection_manager = getattr(http_request.app.state, "mcp_connection_manager", None)
    
    if agent_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent factory not initialized",
        )
    
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # Create agent config
    config = AgentConfig(
        assistant_id=request.assistant_id or f"stream-{session_id[:8]}",
        auto_approve=True,  # Auto-approve for SSE (no HITL support in SSE)
        user_id=user_id,  # Set user_id for multi-tenant isolation
    )
    
    # Get user's workspace path for multi-tenant isolation
    try:
        from dataagent_server.api.v1.workspaces import (
            get_user_default_workspace_path,
            ensure_user_default_workspace,
        )
        
        workspace_path = await get_user_default_workspace_path(user_id)
        if not workspace_path:
            from dataagent_server.config import get_settings
            settings = get_settings()
            workspace_path = await ensure_user_default_workspace(
                user_id, settings.workspace_base_path
            )
        
        if workspace_path:
            config.workspace_path = workspace_path
            logger.info(f"Using workspace path for user {user_id}: {workspace_path}")
    except Exception as e:
        logger.warning(f"Failed to get workspace path for user {user_id}: {e}")
    
    # Load MCP tools for the user
    extra_tools = []
    if mcp_store and mcp_connection_manager:
        try:
            mcp_config = await mcp_store.get_user_config(user_id)
            if mcp_config.servers:
                await mcp_connection_manager.connect(user_id, mcp_config)
                extra_tools = mcp_connection_manager.get_tools(user_id)
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")
    
    if extra_tools:
        config.extra_tools = extra_tools
    
    # Set user context if provided
    if request.user_context:
        config.user_context = request.user_context.to_context_dict()
    
    try:
        agent, backend = agent_factory.create_agent(config)
        executor = AgentExecutor(
            agent=agent,
            backend=backend,
            hitl_handler=None,
            assistant_id=config.assistant_id,
        )
    except Exception as e:
        logger.exception("Failed to create executor")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent executor: {e}",
        )
    
    return StreamingResponse(
        _event_generator(executor, request.message, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id,
        },
    )
