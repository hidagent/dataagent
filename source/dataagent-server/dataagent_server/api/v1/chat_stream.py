"""Streaming chat endpoints using Server-Sent Events (SSE).

Supports HITL (Human-in-the-Loop) via:
1. Sending hitl_request events when approval is needed
2. Receiving hitl_response in subsequent chat requests to continue execution
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from dataagent_server.auth import get_api_key
from dataagent_server.api.deps import get_current_user_id
from dataagent_server.models import ChatRequest
from dataagent_server.hitl import SSEHITLHandler

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


async def _event_generator_with_hitl(
    executor,
    message: str,
    session_id: str,
    hitl_handler: SSEHITLHandler,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from agent execution with HITL support.
    
    This generator supports HITL by:
    1. Yielding hitl_request events when the handler sends them
    2. The execution will pause waiting for user response
    3. User sends a new request with hitl_response to continue
    
    Args:
        executor: AgentExecutor instance.
        message: User message.
        session_id: Session ID.
        hitl_handler: SSE HITL handler for sending events.
        
    Yields:
        SSE formatted event strings.
    """
    # Queue for events from HITL handler
    event_queue: asyncio.Queue = asyncio.Queue()
    
    async def send_event(event_data: dict):
        """Callback for HITL handler to send events."""
        await event_queue.put(event_data)
    
    # Update handler's send_event callback
    hitl_handler.send_event = send_event
    
    async def execute_agent():
        """Run agent execution and put events in queue."""
        try:
            async for event in executor.execute(message, session_id):
                event_data = event.to_dict()
                await event_queue.put(event_data)
        except Exception as e:
            logger.exception("Error during streaming execution")
            await event_queue.put({
                "event_type": "error",
                "data": {
                    "error_code": "EXECUTION_ERROR",
                    "message": str(e),
                    "recoverable": False,
                },
            })
        finally:
            # Signal completion
            await event_queue.put(None)
    
    # Start agent execution in background
    execution_task = asyncio.create_task(execute_agent())
    
    try:
        while True:
            event_data = await event_queue.get()
            
            if event_data is None:
                # Execution completed
                break
            
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            
            # If this is a hitl_request, the execution will pause
            # waiting for SSEHITLHandler.resolve_request to be called
            if event_data.get("event_type") == "hitl_request":
                logger.info(f"HITL request sent, waiting for user response: {event_data.get('interrupt_id')}")
    
    except asyncio.CancelledError:
        execution_task.cancel()
        raise
    finally:
        # Ensure task is cleaned up
        if not execution_task.done():
            execution_task.cancel()
            try:
                await execution_task
            except asyncio.CancelledError:
                pass
        
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
    
    HITL (Human-in-the-Loop) Support:
    - When agent needs user approval, a hitl_request event is sent
    - User responds by sending a new request with hitl_response field
    - The hitl_response contains: type, request_id, and response data
    
    Args:
        request: Chat request with message and optional session/assistant IDs.
        user_id: Current user ID from header.
        
    Returns:
        StreamingResponse with SSE events.
        
    Example:
        ```javascript
        // Normal chat
        fetch('/api/v1/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: 'Hello'})
        });
        
        // HITL response
        fetch('/api/v1/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: '',
                session_id: 'xxx',
                hitl_response: {
                    type: 'human_response',
                    request_id: 'hitl-xxx',
                    response: {type: 'confirm', confirmed: true}
                }
            })
        });
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
    
    # Check if this is a HITL response
    if request.hitl_response:
        return await _handle_hitl_response(request, session_id)
    
    # Check if message contains embedded HITL response (JSON format)
    hitl_from_message = _extract_hitl_from_message(request.message)
    if hitl_from_message:
        return await _handle_hitl_response_data(
            hitl_from_message, 
            session_id,
            request.message,
        )
    
    # Create agent config - enable HITL
    config = AgentConfig(
        assistant_id=request.assistant_id or f"stream-{session_id[:8]}",
        auto_approve=False,  # Enable HITL for SSE
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
    
    # Create HITL handler for SSE
    hitl_handler = SSEHITLHandler(
        session_id=session_id,
        send_event=lambda x: None,  # Will be set by generator
        timeout=300,
    )
    
    try:
        agent, backend = agent_factory.create_agent(config)
        executor = AgentExecutor(
            agent=agent,
            backend=backend,
            hitl_handler=hitl_handler,
            assistant_id=config.assistant_id,
        )
    except Exception as e:
        logger.exception("Failed to create executor")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent executor: {e}",
        )
    
    return StreamingResponse(
        _event_generator_with_hitl(executor, request.message, session_id, hitl_handler),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id,
        },
    )


def _extract_hitl_from_message(message: str) -> dict | None:
    """Extract HITL response from message if it's JSON format.
    
    Supports messages like:
    {"type": "human_response", "requestId": "xxx", "response": {...}}
    
    Args:
        message: User message.
        
    Returns:
        Extracted HITL data or None.
    """
    if not message:
        return None
    
    message = message.strip()
    if not message.startswith("{"):
        return None
    
    try:
        data = json.loads(message)
        if data.get("type") == "human_response" and "requestId" in data:
            return data
    except json.JSONDecodeError:
        pass
    
    return None


async def _handle_hitl_response(
    request: ChatRequest,
    session_id: str,
) -> StreamingResponse:
    """Handle HITL response from user.
    
    Resolves the pending HITL request and returns a simple acknowledgment.
    
    Args:
        request: Chat request with hitl_response.
        session_id: Session ID.
        
    Returns:
        StreamingResponse with acknowledgment.
    """
    hitl_response = request.hitl_response
    interrupt_id = hitl_response.request_id
    response_data = hitl_response.response
    
    # Convert response to decision format
    decision = _convert_response_to_decision(response_data)
    
    # Resolve the pending request
    resolved = await SSEHITLHandler.resolve_request(
        session_id,
        interrupt_id,
        decision,
    )
    
    async def response_generator():
        if resolved:
            event = {
                "event_type": "hitl_resolved",
                "interrupt_id": interrupt_id,
                "decision": decision.get("type"),
            }
        else:
            event = {
                "event_type": "error",
                "error": "NO_PENDING_REQUEST",
                "message": f"No pending HITL request found for {interrupt_id}",
            }
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'event_type': 'stream_end'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id,
        },
    )


async def _handle_hitl_response_data(
    hitl_data: dict,
    session_id: str,
    original_message: str,
) -> StreamingResponse:
    """Handle HITL response extracted from message.
    
    This function resolves the pending HITL request and waits for the agent
    to continue execution. The agent's subsequent output is streamed back
    to the client.
    
    Args:
        hitl_data: Extracted HITL data.
        session_id: Session ID.
        original_message: Original message.
        
    Returns:
        StreamingResponse with agent's continued output.
    """
    interrupt_id = hitl_data.get("requestId", "")
    response_data = hitl_data.get("response", {})
    
    logger.info(f"Handling HITL response for session {session_id}, interrupt {interrupt_id}")
    
    # Convert response to decision format
    decision = _convert_response_to_decision(response_data)
    
    # Resolve the pending request
    resolved = await SSEHITLHandler.resolve_request(
        session_id,
        interrupt_id,
        decision,
    )
    
    async def response_generator():
        # First, send acknowledgment
        if resolved:
            event = {
                "event_type": "hitl_resolved",
                "interrupt_id": interrupt_id,
                "decision": decision.get("type"),
            }
            logger.info(f"HITL request {interrupt_id} resolved successfully")
        else:
            event = {
                "event_type": "error",
                "error": "NO_PENDING_REQUEST",
                "message": f"No pending HITL request found for {interrupt_id}",
            }
            logger.warning(f"No pending HITL request found for {interrupt_id}")
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        # Note: The agent's continued output will be sent through the original SSE stream
        # that is still waiting. This response just acknowledges the HITL resolution.
        # The frontend should continue listening to the original stream for agent output.
        
        yield f"data: {json.dumps({'event_type': 'stream_end'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id,
        },
    )


def _convert_response_to_decision(response_data: dict) -> dict:
    """Convert frontend response format to backend decision format.
    
    Frontend format:
    {
        "type": "confirm",
        "confirmed": true,
        "respondedAt": 1234567890,
        "cancelled": false
    }
    
    Backend format:
    {
        "type": "approve" | "reject",
        "message": "optional message"
    }
    
    Args:
        response_data: Frontend response data.
        
    Returns:
        Backend decision format.
    """
    # Check if cancelled
    if response_data.get("cancelled"):
        return {"type": "reject", "message": "User cancelled"}
    
    response_type = response_data.get("type", "")
    
    if response_type == "confirm":
        if response_data.get("confirmed"):
            return {"type": "approve", "message": None}
        else:
            return {"type": "reject", "message": "User rejected"}
    
    elif response_type == "choice":
        # For choice, we consider any selection as approval
        selected_id = response_data.get("selectedOptionId")
        selected_value = response_data.get("selectedOptionValue")
        return {
            "type": "approve",
            "message": f"Selected: {selected_value or selected_id}",
        }
    
    elif response_type == "input":
        input_value = response_data.get("inputValue", "")
        return {
            "type": "approve",
            "message": input_value,
        }
    
    elif response_type == "form":
        form_values = response_data.get("formValues", {})
        return {
            "type": "approve",
            "message": json.dumps(form_values),
        }
    
    # Default: treat as approval
    return {"type": "approve", "message": None}
