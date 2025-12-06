"""MCP configuration Pydantic models for API."""

from pydantic import BaseModel, Field


class MCPServerConfigRequest(BaseModel):
    """Request model for creating/updating MCP server configuration."""
    
    name: str = Field(..., description="Unique identifier for the MCP server")
    command: str = Field(..., description="Command to execute (e.g., 'uvx', 'npx', 'python')")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    disabled: bool = Field(default=False, description="Whether the server is disabled")
    auto_approve: list[str] = Field(
        default_factory=list,
        alias="autoApprove",
        description="List of tool names to auto-approve"
    )
    
    model_config = {"populate_by_name": True}


class MCPServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""
    
    name: str = Field(..., description="Unique identifier for the MCP server")
    command: str = Field(..., description="Command to execute")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    disabled: bool = Field(default=False, description="Whether the server is disabled")
    auto_approve: list[str] = Field(
        default_factory=list,
        alias="autoApprove",
        description="List of tool names to auto-approve"
    )
    status: str = Field(default="unknown", description="Connection status")
    
    model_config = {"populate_by_name": True}


class MCPServerListResponse(BaseModel):
    """Response model for listing MCP servers."""
    
    servers: list[MCPServerConfigResponse] = Field(
        default_factory=list,
        description="List of MCP server configurations"
    )


class MCPServerDeleteResponse(BaseModel):
    """Response model for deleting MCP server."""
    
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")
