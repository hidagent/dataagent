"""WebSocket message handlers."""

import asyncio
import logging
import time
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from dataagent_server.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketChatHandler:
    """Handler for WebSocket chat connections.
    
    Processes client messages and manages chat sessions.
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        agent_factory: Any | None = None,
        settings: Any | None = None,
        mcp_store: Any | None = None,
        mcp_connection_manager: Any | None = None,
    ):
        """Initialize chat handler.
        
        Args:
            connection_manager: Connection manager instance.
            agent_factory: AgentFactory instance for creating agents.
            settings: Core settings for agent configuration.
            mcp_store: MCP configuration store.
            mcp_connection_manager: MCP connection manager.
        """
        self.connections = connection_manager
        self.agent_factory = agent_factory
        self.settings = settings
        self.mcp_store = mcp_store
        self.mcp_connection_manager = mcp_connection_manager
        self._executors: dict[str, Any] = {}  # session_id -> AgentExecutor
        self._session_users: dict[str, str] = {}  # session_id -> user_id
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """Handle a WebSocket connection.
        
        Args:
            websocket: WebSocket connection.
            session_id: Session ID for the connection.
        """
        # Try to connect
        if not await self.connections.connect(websocket, session_id):
            await websocket.close(code=1013, reason="Service at capacity")
            return
        
        # Send connected message
        await self.connections.send(session_id, {
            "event_type": "connected",
            "data": {"session_id": session_id},
            "timestamp": time.time(),
        })
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                
                # Validate message format
                if not self._validate_message(data):
                    await self._send_error(
                        session_id,
                        "INVALID_MESSAGE",
                        "Message must contain 'type' and 'payload' fields",
                    )
                    continue
                
                # Handle message
                await self._handle_message(data, session_id)
                
        except WebSocketDisconnect:
            pass
        except Exception as e:
            await self._send_error(session_id, "INTERNAL_ERROR", str(e))
        finally:
            await self.connections.disconnect(session_id)
    
    def _validate_message(self, data: Any) -> bool:
        """Validate message format.
        
        Args:
            data: Message data to validate.
            
        Returns:
            True if message is valid.
        """
        if not isinstance(data, dict):
            return False
        if "type" not in data:
            return False
        if "payload" not in data:
            return False
        return True
    
    async def _handle_message(
        self,
        data: dict,
        session_id: str,
    ) -> None:
        """Handle a validated message.
        
        Args:
            data: Message data.
            session_id: Session ID.
        """
        msg_type = data.get("type")
        payload = data.get("payload", {})
        
        if msg_type == "chat":
            await self._handle_chat(payload, session_id)
        elif msg_type == "hitl_decision":
            await self._handle_hitl_decision(payload, session_id)
        elif msg_type == "cancel":
            await self._handle_cancel(session_id)
        elif msg_type == "ping":
            await self._handle_ping(session_id)
        else:
            await self._send_error(
                session_id,
                "UNKNOWN_MESSAGE_TYPE",
                f"Unknown message type: {msg_type}",
            )
    
    async def _get_or_create_executor(self, session_id: str, user_id: str = "anonymous") -> Any:
        """Get or create an AgentExecutor for the session.
        
        Args:
            session_id: Session ID.
            user_id: User ID for MCP configuration.
            
        Returns:
            AgentExecutor instance.
        """
        if session_id in self._executors:
            return self._executors[session_id]
        
        if self.agent_factory is None:
            return None
        
        # Import here to avoid circular imports
        from dataagent_core.engine import AgentExecutor, AgentConfig
        from dataagent_core.hitl import HITLHandler
        
        # Create a HITL handler that uses the connection manager
        hitl_handler = WebSocketHITLHandler(
            connection_manager=self.connections,
            session_id=session_id,
        )
        
        # Create agent config - use session_id as assistant_id for isolation
        config = AgentConfig(
            assistant_id=f"server-{session_id[:8]}",
            auto_approve=False,  # Enable HITL
        )
        
        # Load MCP tools for the user
        extra_tools = []
        if self.mcp_store and self.mcp_connection_manager:
            try:
                mcp_config = await self.mcp_store.get_user_config(user_id)
                if mcp_config.servers:
                    await self.mcp_connection_manager.connect(user_id, mcp_config)
                    extra_tools = self.mcp_connection_manager.get_tools(user_id)
                    if extra_tools:
                        logger.info(f"Loaded {len(extra_tools)} MCP tools for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to load MCP tools for user {user_id}: {e}")
        
        if extra_tools:
            config.extra_tools = extra_tools
        
        # Create agent and backend
        agent, backend = self.agent_factory.create_agent(config)
        
        # Create executor
        executor = AgentExecutor(
            agent=agent,
            backend=backend,
            hitl_handler=hitl_handler,
            assistant_id=config.assistant_id,
        )
        
        self._executors[session_id] = executor
        self._session_users[session_id] = user_id
        return executor

    async def _handle_chat(
        self,
        payload: dict,
        session_id: str,
    ) -> None:
        """Handle chat message.
        
        Args:
            payload: Chat payload with message.
            session_id: Session ID.
        """
        message = payload.get("message", "")
        if not message:
            await self._send_error(
                session_id,
                "EMPTY_MESSAGE",
                "Message cannot be empty",
            )
            return
        
        # Check if agent factory is configured
        if self.agent_factory is None:
            logger.warning("AgentFactory not configured, using placeholder response")
            await self.connections.send(session_id, {
                "event_type": "text",
                "data": {
                    "content": "Agent not configured. Please configure the server with an AgentFactory.",
                    "is_final": True,
                },
                "timestamp": time.time(),
            })
            await self.connections.send(session_id, {
                "event_type": "done",
                "data": {"cancelled": False, "token_usage": None},
                "timestamp": time.time(),
            })
            return
        
        # Get user_id from payload or use default
        user_id = payload.get("user_id", "anonymous")
        
        # Get or create executor for this session
        try:
            executor = await self._get_or_create_executor(session_id, user_id)
            if executor is None:
                await self._send_error(
                    session_id,
                    "EXECUTOR_ERROR",
                    "Failed to create agent executor",
                )
                return
        except Exception as e:
            logger.exception("Failed to create executor")
            await self._send_error(
                session_id,
                "EXECUTOR_ERROR",
                f"Failed to create agent executor: {e}",
            )
            return
        
        # Execute the agent and stream events
        try:
            async for event in executor.execute(message, session_id):
                # Send event to client
                await self.connections.send_event(session_id, event)
        except asyncio.CancelledError:
            await self.connections.send(session_id, {
                "event_type": "done",
                "data": {"cancelled": True, "reason": "task_cancelled"},
                "timestamp": time.time(),
            })
        except Exception as e:
            logger.exception("Error during agent execution")
            await self._send_error(
                session_id,
                "EXECUTION_ERROR",
                f"Agent execution failed: {e}",
            )
            await self.connections.send(session_id, {
                "event_type": "done",
                "data": {"cancelled": False, "token_usage": None},
                "timestamp": time.time(),
            })
    
    async def _handle_hitl_decision(
        self,
        payload: dict,
        session_id: str,
    ) -> None:
        """Handle HITL decision message.
        
        Args:
            payload: Decision payload.
            session_id: Session ID.
        """
        decisions = payload.get("decisions", [])
        if not decisions:
            await self._send_error(
                session_id,
                "EMPTY_DECISION",
                "Decision list cannot be empty",
            )
            return
        
        # Resolve the pending decision
        decision = decisions[0] if decisions else {"type": "reject"}
        resolved = self.connections.resolve_decision(session_id, decision)
        
        if not resolved:
            await self._send_error(
                session_id,
                "NO_PENDING_DECISION",
                "No pending HITL decision to resolve",
            )
    
    async def _handle_cancel(self, session_id: str) -> None:
        """Handle cancel message.
        
        Args:
            session_id: Session ID.
        """
        cancelled = await self.connections.cancel_task(session_id)
        
        # Send done event with cancelled=True
        await self.connections.send(session_id, {
            "event_type": "done",
            "data": {
                "cancelled": True,
                "reason": "user_cancelled" if cancelled else "no_active_task",
            },
            "timestamp": time.time(),
        })
    
    async def _handle_ping(self, session_id: str) -> None:
        """Handle ping message.
        
        Args:
            session_id: Session ID.
        """
        await self.connections.send(session_id, {
            "event_type": "pong",
            "data": {},
            "timestamp": time.time(),
        })
    
    async def _send_error(
        self,
        session_id: str,
        error_code: str,
        message: str,
    ) -> None:
        """Send error message to client.
        
        Args:
            session_id: Session ID.
            error_code: Error code.
            message: Error message.
        """
        await self.connections.send(session_id, {
            "event_type": "error",
            "data": {
                "error_code": error_code,
                "message": message,
                "recoverable": True,
            },
            "timestamp": time.time(),
        })


class WebSocketHITLHandler:
    """HITL handler that uses WebSocket for user approval.
    
    Sends HITL requests to the client via WebSocket and waits
    for the user's decision.
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        session_id: str,
        timeout: float = 300,
    ):
        """Initialize WebSocket HITL handler.
        
        Args:
            connection_manager: Connection manager for WebSocket communication.
            session_id: Session ID for this handler.
            timeout: Timeout in seconds for waiting for user decision.
        """
        self.connections = connection_manager
        self.session_id = session_id
        self.timeout = timeout
    
    async def request_approval(
        self,
        action_request: dict,
        session_id: str,
    ) -> dict:
        """Request user approval for an action via WebSocket.
        
        Args:
            action_request: Action request details.
            session_id: Session ID (may differ from handler's session_id).
            
        Returns:
            Decision dict with type and optional message.
        """
        # Send HITL request to client
        await self.connections.send(self.session_id, {
            "event_type": "hitl",
            "data": {
                "action": action_request,
            },
            "timestamp": time.time(),
        })
        
        # Wait for user decision
        decision = await self.connections.wait_for_decision(
            self.session_id,
            timeout=self.timeout,
        )
        
        if decision is None:
            # Timeout or cancelled - reject by default
            return {"type": "reject", "message": "Timeout waiting for approval"}
        
        return decision
