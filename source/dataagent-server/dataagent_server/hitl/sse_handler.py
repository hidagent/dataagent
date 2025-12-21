"""SSE HITL handler for streaming chat endpoints.

This handler sends HITL requests via SSE events and stores pending requests
for later resolution via HTTP endpoints.
"""

import asyncio
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SSEHITLHandler:
    """HITL handler for SSE streaming mode.
    
    Instead of waiting for user response in real-time (like WebSocket),
    this handler:
    1. Sends a hitl_request event via SSE
    2. Stores the pending request
    3. Waits for the user to send a new message with hitl_response
    
    The response is resolved when the user sends a new chat request
    with the hitl_response field populated.
    """
    
    # Class-level storage for pending HITL requests
    # Key: (session_id, interrupt_id) -> Future
    _pending_requests: dict[tuple[str, str], asyncio.Future] = {}
    _lock = asyncio.Lock()
    
    def __init__(
        self,
        session_id: str,
        send_event: Callable[[dict], Any],
        timeout: float = 300,
    ):
        """Initialize SSE HITL handler.
        
        Args:
            session_id: Session ID for this handler.
            send_event: Callback to send SSE events.
            timeout: Timeout in seconds for waiting for user decision.
        """
        self.session_id = session_id
        self.send_event = send_event
        self.timeout = timeout
        self._current_interrupt_id: str | None = None
    
    async def request_approval(
        self,
        action_request: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """Request user approval for an action via SSE.
        
        Sends a hitl_request event and waits for the user to respond
        via a new chat request with hitl_response.
        
        Args:
            action_request: Action request details (name, args, description).
            session_id: Session ID (may differ from handler's session_id).
            
        Returns:
            Decision dict with type (approve/reject) and optional message.
        """
        import uuid
        
        # Generate interrupt ID
        interrupt_id = f"hitl-{uuid.uuid4().hex[:8]}"
        self._current_interrupt_id = interrupt_id
        
        # Create future for this request
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        
        async with self._lock:
            self._pending_requests[(self.session_id, interrupt_id)] = future
        
        # Send HITL request event via SSE
        # Check if this is a human tool call with custom UI parameters
        tool_name = action_request.get("name", "")
        tool_args = action_request.get("args", {})
        
        # For human tool, extract the UI parameters directly
        if tool_name == "human":
            hitl_args = self._build_human_tool_args(tool_args)
        else:
            # For other tools, build a confirm-style approval request
            hitl_args = self._build_tool_approval_args(action_request)
        
        hitl_event = {
            "event_type": "hitl_request",
            "interrupt_id": interrupt_id,
            "action_requests": [action_request],
            "hitl_args": hitl_args,  # Frontend-friendly UI parameters
            "timestamp": time.time(),
        }
        
        logger.info(f"Sending HITL request: {interrupt_id} for session {self.session_id}, tool: {tool_name}")
        await self.send_event(hitl_event)
        
        try:
            # Wait for user response with timeout
            decision = await asyncio.wait_for(future, timeout=self.timeout)
            logger.info(f"HITL request {interrupt_id} resolved: {decision.get('type')}")
            return decision
        except asyncio.TimeoutError:
            logger.warning(f"HITL request {interrupt_id} timed out")
            return {"type": "reject", "message": "Approval timeout - automatically rejected"}
        except asyncio.CancelledError:
            logger.info(f"HITL request {interrupt_id} cancelled")
            return {"type": "reject", "message": "Request cancelled"}
        finally:
            async with self._lock:
                self._pending_requests.pop((self.session_id, interrupt_id), None)
    
    @classmethod
    async def resolve_request(
        cls,
        session_id: str,
        interrupt_id: str,
        decision: dict[str, Any],
    ) -> bool:
        """Resolve a pending HITL request.
        
        Called when user sends a new chat request with hitl_response.
        
        Args:
            session_id: Session ID.
            interrupt_id: Interrupt ID to resolve.
            decision: User's decision (type: approve/reject, message: optional).
            
        Returns:
            True if request was resolved, False if no pending request found.
        """
        async with cls._lock:
            future = cls._pending_requests.get((session_id, interrupt_id))
            
            if future is None:
                logger.warning(f"No pending HITL request found: {session_id}/{interrupt_id}")
                return False
            
            if future.done():
                logger.warning(f"HITL request already resolved: {session_id}/{interrupt_id}")
                return False
            
            future.set_result(decision)
            logger.info(f"HITL request resolved: {session_id}/{interrupt_id}")
            return True
    
    @classmethod
    async def has_pending_request(cls, session_id: str) -> bool:
        """Check if session has any pending HITL requests.
        
        Args:
            session_id: Session ID to check.
            
        Returns:
            True if there are pending requests.
        """
        async with cls._lock:
            return any(
                key[0] == session_id 
                for key in cls._pending_requests.keys()
            )
    
    @classmethod
    async def cancel_pending_requests(cls, session_id: str) -> int:
        """Cancel all pending HITL requests for a session.
        
        Args:
            session_id: Session ID.
            
        Returns:
            Number of cancelled requests.
        """
        cancelled = 0
        async with cls._lock:
            keys_to_remove = [
                key for key in cls._pending_requests.keys()
                if key[0] == session_id
            ]
            
            for key in keys_to_remove:
                future = cls._pending_requests.pop(key, None)
                if future and not future.done():
                    future.cancel()
                    cancelled += 1
        
        if cancelled:
            logger.info(f"Cancelled {cancelled} pending HITL requests for session {session_id}")
        
        return cancelled
    
    @staticmethod
    def _build_human_tool_args(tool_args: dict[str, Any]) -> dict[str, Any]:
        """Build frontend-friendly args from human tool parameters.
        
        The human tool allows agents to specify custom UI components.
        This method converts the tool arguments to the format expected
        by the frontend HumanInteractionCard component.
        
        Args:
            tool_args: Arguments passed to the human tool.
            
        Returns:
            Frontend-friendly hitl_args dict.
        """
        interaction_type = tool_args.get("interaction_type", "confirm")
        
        hitl_args = {
            "type": interaction_type,
            "title": tool_args.get("title", "用户交互"),
            "message": tool_args.get("message", ""),
        }
        
        if interaction_type == "choice":
            hitl_args["options"] = tool_args.get("options", [])
            
        elif interaction_type == "confirm":
            hitl_args["confirmText"] = tool_args.get("confirm_text", "确认")
            hitl_args["cancelText"] = tool_args.get("cancel_text", "取消")
            
        elif interaction_type == "input":
            if tool_args.get("placeholder"):
                hitl_args["placeholder"] = tool_args["placeholder"]
            if tool_args.get("default_value"):
                hitl_args["defaultValue"] = tool_args["default_value"]
                
        elif interaction_type == "form":
            hitl_args["fields"] = tool_args.get("fields", [])
        
        if tool_args.get("timeout"):
            hitl_args["timeout"] = tool_args["timeout"]
        
        return hitl_args
    
    @staticmethod
    def _build_tool_approval_args(action_request: dict[str, Any]) -> dict[str, Any]:
        """Build frontend-friendly args for tool approval requests.
        
        For non-human tools that require approval (like shell, write_file),
        this builds a confirm-style UI.
        
        Args:
            action_request: The action request from the agent.
            
        Returns:
            Frontend-friendly hitl_args dict.
        """
        tool_name = action_request.get("name", "unknown")
        tool_args = action_request.get("args", {})
        description = action_request.get("description", "")
        
        # Build a readable description of the tool call
        if tool_name == "shell":
            command = tool_args.get("command", "")
            detail_message = f"命令: `{command}`"
        elif tool_name in ("write_file", "edit_file"):
            file_path = tool_args.get("file_path", "")
            detail_message = f"文件: `{file_path}`"
        else:
            # Generic format for other tools
            detail_message = description or f"参数: {tool_args}"
        
        return {
            "type": "confirm",
            "title": f"工具审批: {tool_name}",
            "message": f"Agent 请求执行以下操作:\n\n{detail_message}\n\n是否允许执行？",
            "confirmText": "允许执行",
            "cancelText": "拒绝",
        }
