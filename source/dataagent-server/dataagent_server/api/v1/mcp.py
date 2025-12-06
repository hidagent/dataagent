"""MCP configuration REST API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from dataagent_core.mcp import MCPServerConfig, MCPConfig

from dataagent_server.api.deps import get_mcp_store, get_current_user_id
from dataagent_server.models.mcp import (
    MCPServerConfigRequest,
    MCPServerConfigResponse,
    MCPServerListResponse,
    MCPServerDeleteResponse,
)

router = APIRouter(prefix="/users/{user_id}/mcp-servers", tags=["MCP"])


def _check_user_access(user_id: str, current_user_id: str) -> None:
    """Check if current user can access the target user's resources."""
    # For now, users can only access their own resources
    # Admin check can be added later
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's MCP configuration",
        )


@router.get("", response_model=MCPServerListResponse)
async def list_mcp_servers(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerListResponse:
    """List all MCP servers for a user."""
    _check_user_access(user_id, current_user_id)
    
    config = await mcp_store.get_user_config(user_id)
    
    servers = [
        MCPServerConfigResponse(
            name=server.name,
            command=server.command,
            args=server.args,
            env=server.env,
            disabled=server.disabled,
            auto_approve=server.auto_approve,
            status="configured",  # Connection status would come from MCPConnectionManager
        )
        for server in config.servers.values()
    ]
    
    return MCPServerListResponse(servers=servers)


@router.post("", response_model=MCPServerConfigResponse, status_code=status.HTTP_201_CREATED)
async def add_mcp_server(
    user_id: str,
    request: MCPServerConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Add a new MCP server for a user."""
    _check_user_access(user_id, current_user_id)
    
    server = MCPServerConfig(
        name=request.name,
        command=request.command,
        args=request.args,
        env=request.env,
        disabled=request.disabled,
        auto_approve=request.auto_approve,
    )
    
    await mcp_store.add_server(user_id, server)
    
    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status="configured",
    )


@router.get("/{server_name}", response_model=MCPServerConfigResponse)
async def get_mcp_server(
    user_id: str,
    server_name: str,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Get a specific MCP server configuration."""
    _check_user_access(user_id, current_user_id)
    
    server = await mcp_store.get_server(user_id, server_name)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    
    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status="configured",
    )


@router.put("/{server_name}", response_model=MCPServerConfigResponse)
async def update_mcp_server(
    user_id: str,
    server_name: str,
    request: MCPServerConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Update an MCP server configuration."""
    _check_user_access(user_id, current_user_id)
    
    # Check if server exists
    existing = await mcp_store.get_server(user_id, server_name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    
    # If name changed, remove old and add new
    if request.name != server_name:
        await mcp_store.remove_server(user_id, server_name)
    
    server = MCPServerConfig(
        name=request.name,
        command=request.command,
        args=request.args,
        env=request.env,
        disabled=request.disabled,
        auto_approve=request.auto_approve,
    )
    
    await mcp_store.add_server(user_id, server)
    
    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status="configured",
    )


@router.delete("/{server_name}", response_model=MCPServerDeleteResponse)
async def delete_mcp_server(
    user_id: str,
    server_name: str,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerDeleteResponse:
    """Delete an MCP server configuration."""
    _check_user_access(user_id, current_user_id)
    
    removed = await mcp_store.remove_server(user_id, server_name)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    
    return MCPServerDeleteResponse(
        success=True,
        message=f"MCP server '{server_name}' deleted successfully",
    )
