"""HITL protocol definition."""

from typing import Protocol, TypedDict


class ActionRequest(TypedDict):
    """Action request for HITL approval."""
    name: str
    args: dict
    description: str


class Decision(TypedDict):
    """User decision."""
    type: str  # approve, reject
    message: str | None


class HITLHandler(Protocol):
    """HITL handler protocol."""

    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """Request user approval for an action."""
        ...


class AutoApproveHandler:
    """Auto-approve handler - approves all requests."""

    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        return {"type": "approve", "message": None}
