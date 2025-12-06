"""MCP configuration Pydantic models for API."""

from pydantic import BaseModel, Field


class MCPServerConfigRequest(BaseModel):
    """Request model for creating/updating MCP server configuration."""

    name: str = Field(..., description="Unique identifier for the MCP server")
    command: str = Field(
        default="", description="Command to execute (e.g., 'uvx', 'npx', 'python')"
    )
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    url: str | None = Field(default=None, description="HTTP/SSE URL for MCP server")
    transport: str = Field(
        default="sse", description="Transport type: 'sse' or 'streamable_http'"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers for HTTP transport"
    )
    disabled: bool = Field(default=False, description="Whether the server is disabled")
    auto_approve: list[str] = Field(
        default_factory=list,
        alias="autoApprove",
        description="List of tool names to auto-approve",
    )

    model_config = {"populate_by_name": True}


class MCPServerStatusResponse(BaseModel):
    """Response model for MCP server status."""

    name: str = Field(..., description="Server name")
    status: str = Field(
        ..., description="Connection status: connected, disconnected, error, disabled"
    )
    connected: bool = Field(default=False, description="Whether connected")
    tools_count: int = Field(default=0, description="Number of available tools")
    tools: list[str] = Field(default_factory=list, description="List of tool names")
    error: str | None = Field(default=None, description="Error message if any")
    disabled: bool = Field(default=False, description="Whether the server is disabled")


class MCPServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    name: str = Field(..., description="Unique identifier for the MCP server")
    command: str = Field(default="", description="Command to execute")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    url: str | None = Field(default=None, description="HTTP/SSE URL for MCP server")
    transport: str = Field(
        default="sse", description="Transport type: 'sse' or 'streamable_http'"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers for HTTP transport"
    )
    disabled: bool = Field(default=False, description="Whether the server is disabled")
    auto_approve: list[str] = Field(
        default_factory=list,
        alias="autoApprove",
        description="List of tool names to auto-approve",
    )
    status: str = Field(default="unknown", description="Connection status")
    connected: bool = Field(default=False, description="Whether connected")
    tools_count: int = Field(default=0, description="Number of available tools")
    error: str | None = Field(default=None, description="Error message if any")

    model_config = {"populate_by_name": True}


class MCPServerListResponse(BaseModel):
    """Response model for listing MCP servers."""

    servers: list[MCPServerConfigResponse] = Field(
        default_factory=list, description="List of MCP server configurations"
    )


class MCPServerDeleteResponse(BaseModel):
    """Response model for deleting MCP server."""

    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")


class MCPServerToggleRequest(BaseModel):
    """Request model for enabling/disabling MCP server."""

    disabled: bool = Field(..., description="Whether to disable the server")


class MCPServerConnectResponse(BaseModel):
    """Response model for connect/disconnect operations."""

    success: bool = Field(..., description="Whether operation was successful")
    status: str = Field(..., description="New connection status")
    tools_count: int = Field(default=0, description="Number of available tools")
    tools: list[str] = Field(default_factory=list, description="List of tool names")
    error: str | None = Field(default=None, description="Error message if any")
