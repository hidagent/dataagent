"""API dependencies and exception handlers."""

import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI, Request, status, Header
from fastapi.responses import JSONResponse

from dataagent_server.models import ErrorResponse

# Context variable for request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Global stores (set during app startup)
_session_manager = None
_mcp_store = None


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_ctx.get()


class DataAgentException(Exception):
    """Base exception for DataAgent Server."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class SessionNotFoundError(DataAgentException):
    """Session not found error."""
    
    def __init__(self, session_id: str):
        super().__init__(
            error_code="SESSION_NOT_FOUND",
            message=f"Session {session_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"session_id": session_id},
        )


class ServiceUnavailableError(DataAgentException):
    """Service unavailable error."""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance.
    """
    
    @app.exception_handler(DataAgentException)
    async def dataagent_exception_handler(
        request: Request,
        exc: DataAgentException,
    ) -> JSONResponse:
        """Handle DataAgent exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            ).model_dump(),
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"error": str(exc)} if str(exc) else None,
            ).model_dump(),
        )


async def request_id_middleware(request: Request, call_next):
    """Middleware to generate and track request IDs.
    
    Args:
        request: FastAPI request object.
        call_next: Next middleware/handler in chain.
        
    Returns:
        Response with X-Request-ID header.
    """
    # Generate or get request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Set in context
    token = request_id_ctx.set(request_id)
    
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)


def set_session_manager(manager) -> None:
    """Set the global session manager."""
    global _session_manager
    _session_manager = manager


def get_session_manager():
    """Get the global session manager."""
    if _session_manager is None:
        raise ServiceUnavailableError("Session manager not initialized")
    return _session_manager


def set_mcp_store(store) -> None:
    """Set the global MCP config store."""
    global _mcp_store
    _mcp_store = store


def get_mcp_store():
    """Get the global MCP config store."""
    if _mcp_store is None:
        raise ServiceUnavailableError("MCP store not initialized")
    return _mcp_store


def get_current_user_id(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> str:
    """Get current user ID from request header.
    
    For now, uses X-User-ID header. In production, this would
    be extracted from authentication token.
    
    Args:
        x_user_id: User ID from header.
        
    Returns:
        User ID string, defaults to "anonymous" if not provided.
    """
    return x_user_id or "anonymous"
