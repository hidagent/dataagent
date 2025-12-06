"""Human-in-the-loop protocol for DataAgent Core."""

from typing import Protocol, TypedDict
from abc import abstractmethod


class ActionRequest(TypedDict):
    """Action request for HITL approval."""
    name: str
    args: dict
    description: str


class Decision(TypedDict):
    """User decision for HITL approval."""
    type: str  # approve, reject
    message: str | None


class HITLHandler(Protocol):
    """Protocol for HITL handlers."""

    @abstractmethod
    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        """Request user approval for an action."""
        ...


class AutoApproveHandler:
    """Auto-approve handler that approves all actions."""

    async def request_approval(
        self,
        action_request: ActionRequest,
        session_id: str,
    ) -> Decision:
        return {"type": "approve", "message": None}


__all__ = ["HITLHandler", "ActionRequest", "Decision", "AutoApproveHandler"]
