"""WebSocket HITL handler."""

import time
from typing import Any

from dataagent_server.ws.manager import ConnectionManager


class WebSocketHITLHandler:
    """HITL handler that uses WebSocket for user interaction.
    
    Implements the HITLHandler protocol from dataagent-core,
    sending approval requests via WebSocket and waiting for
    user decisions.
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        timeout: float = 300,
    ):
        """Initialize WebSocket HITL handler.
        
        Args:
            connection_manager: Connection manager for WebSocket communication.
            timeout: Timeout in seconds for waiting for user decision.
        """
        self.connections = connection_manager
        self.timeout = timeout
    
    async def request_approval(
        self,
        action_request: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """Request user approval for an action.
        
        Sends a HITL request event via WebSocket and waits for
        the user's decision. If timeout is reached, automatically
        rejects the action.
        
        Args:
            action_request: Action request containing name, args, description.
            session_id: Session ID for the request.
            
        Returns:
            Decision dict with type (approve/reject) and optional message.
        """
        # Send HITL request to client
        await self.connections.send(session_id, {
            "event_type": "hitl_request",
            "data": {
                "action_request": action_request,
            },
            "timestamp": time.time(),
        })
        
        # Wait for decision with timeout
        decision = await self.connections.wait_for_decision(
            session_id,
            timeout=self.timeout,
        )
        
        # If no decision (timeout or cancelled), reject
        if decision is None:
            return {
                "type": "reject",
                "message": "Approval timeout - automatically rejected",
            }
        
        return decision
