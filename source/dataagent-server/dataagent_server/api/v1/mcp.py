"""MCP configuration REST API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from dataagent_core.mcp import MCPServerConfig

from dataagent_server.api.deps import get_mcp_store, get_current_user_id
from dataagent_server.models.mcp import (
    MCPServerConfigRequest,
    MCPServerConfigResponse,
    MCPServerListResponse,
    MCPServerDeleteResponse,
    MCPServerStatusResponse,
    MCPServerToggleRequest,
    MCPServerConnectResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/{user_id}/mcp-servers", tags=["MCP"])


def _check_user_access(user_id: str, current_user_id: str) -> None:
    """Check if current user can access the target user's resources."""
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's MCP configuration",
        )


def _get_mcp_connection_manager(request: Request):
    """Get MCP connection manager from app state."""
    return getattr(request.app.state, "mcp_connection_manager", None)


@router.get("", response_model=MCPServerListResponse)
async def list_mcp_servers(
    user_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerListResponse:
    """List all MCP servers for a user with connection status."""
    _check_user_access(user_id, current_user_id)

    config = await mcp_store.get_user_config(user_id)
    mcp_manager = _get_mcp_connection_manager(request)

    # Get connection status
    connection_status = {}
    if mcp_manager:
        connection_status = mcp_manager.get_connection_status(user_id)

    servers = []
    for server in config.servers.values():
        conn_info = connection_status.get(server.name, {})
        connected = conn_info.get("connected", False)
        tools_count = conn_info.get("tools_count", 0)
        error = conn_info.get("error")

        if server.disabled:
            status_str = "disabled"
        elif connected:
            status_str = "connected"
        elif error:
            status_str = "error"
        else:
            status_str = "disconnected"

        servers.append(
            MCPServerConfigResponse(
                name=server.name,
                command=server.command,
                args=server.args,
                env=server.env,
                url=server.url,
                disabled=server.disabled,
                auto_approve=server.auto_approve,
                status=status_str,
                connected=connected,
                tools_count=tools_count,
                error=error,
            )
        )

    return MCPServerListResponse(servers=servers)


@router.post("", response_model=MCPServerConfigResponse, status_code=status.HTTP_201_CREATED)
async def add_mcp_server(
    user_id: str,
    request_body: MCPServerConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Add a new MCP server for a user."""
    _check_user_access(user_id, current_user_id)

    server = MCPServerConfig(
        name=request_body.name,
        command=request_body.command,
        args=request_body.args,
        env=request_body.env,
        url=request_body.url,
        transport=request_body.transport,
        headers=request_body.headers,
        disabled=request_body.disabled,
        auto_approve=request_body.auto_approve,
    )

    await mcp_store.add_server(user_id, server)

    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        url=server.url,
        transport=server.transport,
        headers=server.headers,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status="disabled" if server.disabled else "disconnected",
        connected=False,
        tools_count=0,
    )


@router.get("/{server_name}", response_model=MCPServerConfigResponse)
async def get_mcp_server(
    user_id: str,
    server_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Get a specific MCP server configuration with status."""
    _check_user_access(user_id, current_user_id)

    server = await mcp_store.get_server(user_id, server_name)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )

    # Get connection status
    mcp_manager = _get_mcp_connection_manager(request)
    conn_info = {}
    if mcp_manager:
        status_dict = mcp_manager.get_connection_status(user_id)
        conn_info = status_dict.get(server_name, {})

    connected = conn_info.get("connected", False)
    tools_count = conn_info.get("tools_count", 0)
    error = conn_info.get("error")

    if server.disabled:
        status_str = "disabled"
    elif connected:
        status_str = "connected"
    elif error:
        status_str = "error"
    else:
        status_str = "disconnected"

    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        url=server.url,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status=status_str,
        connected=connected,
        tools_count=tools_count,
        error=error,
    )


@router.put("/{server_name}", response_model=MCPServerConfigResponse)
async def update_mcp_server(
    user_id: str,
    server_name: str,
    request_body: MCPServerConfigRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Update an MCP server configuration."""
    _check_user_access(user_id, current_user_id)

    existing = await mcp_store.get_server(user_id, server_name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )

    # If name changed, remove old
    if request_body.name != server_name:
        await mcp_store.remove_server(user_id, server_name)
        # Disconnect old server
        mcp_manager = _get_mcp_connection_manager(request)
        if mcp_manager:
            await mcp_manager.disconnect(user_id, server_name)

    server = MCPServerConfig(
        name=request_body.name,
        command=request_body.command,
        args=request_body.args,
        env=request_body.env,
        url=request_body.url,
        transport=request_body.transport,
        headers=request_body.headers,
        disabled=request_body.disabled,
        auto_approve=request_body.auto_approve,
    )

    await mcp_store.add_server(user_id, server)

    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        url=server.url,
        transport=server.transport,
        headers=server.headers,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status="disabled" if server.disabled else "disconnected",
        connected=False,
        tools_count=0,
    )


@router.delete("/{server_name}", response_model=MCPServerDeleteResponse)
async def delete_mcp_server(
    user_id: str,
    server_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerDeleteResponse:
    """Delete an MCP server configuration."""
    _check_user_access(user_id, current_user_id)

    # Disconnect first
    mcp_manager = _get_mcp_connection_manager(request)
    if mcp_manager:
        await mcp_manager.disconnect(user_id, server_name)

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


@router.get("/{server_name}/status", response_model=MCPServerStatusResponse)
async def get_mcp_server_status(
    user_id: str,
    server_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerStatusResponse:
    """Get connection status for a specific MCP server."""
    _check_user_access(user_id, current_user_id)

    server = await mcp_store.get_server(user_id, server_name)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )

    mcp_manager = _get_mcp_connection_manager(request)
    if not mcp_manager:
        return MCPServerStatusResponse(
            name=server_name,
            status="disabled" if server.disabled else "disconnected",
            connected=False,
            tools_count=0,
            tools=[],
            error=None,
            disabled=server.disabled,
        )

    conn_status = mcp_manager.get_connection_status(user_id)
    conn_info = conn_status.get(server_name, {})

    connected = conn_info.get("connected", False)
    tools_count = conn_info.get("tools_count", 0)
    error = conn_info.get("error")

    # Get tool names
    tools = []
    if connected and user_id in mcp_manager._connections:
        conn = mcp_manager._connections[user_id].get(server_name)
        if conn and conn.tools:
            tools = [t.name for t in conn.tools]

    if server.disabled:
        status_str = "disabled"
    elif connected:
        status_str = "connected"
    elif error:
        status_str = "error"
    else:
        status_str = "disconnected"

    return MCPServerStatusResponse(
        name=server_name,
        status=status_str,
        connected=connected,
        tools_count=tools_count,
        tools=tools,
        error=error,
        disabled=server.disabled,
    )


@router.post("/{server_name}/toggle", response_model=MCPServerConfigResponse)
async def toggle_mcp_server(
    user_id: str,
    server_name: str,
    request_body: MCPServerToggleRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConfigResponse:
    """Enable or disable an MCP server."""
    _check_user_access(user_id, current_user_id)

    server = await mcp_store.get_server(user_id, server_name)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )

    # Update disabled status
    server.disabled = request_body.disabled
    await mcp_store.add_server(user_id, server)

    # If disabling, disconnect
    mcp_manager = _get_mcp_connection_manager(request)
    if request_body.disabled and mcp_manager:
        await mcp_manager.disconnect(user_id, server_name)

    return MCPServerConfigResponse(
        name=server.name,
        command=server.command,
        args=server.args,
        env=server.env,
        url=server.url,
        disabled=server.disabled,
        auto_approve=server.auto_approve,
        status="disabled" if server.disabled else "disconnected",
        connected=False,
        tools_count=0,
    )


@router.post("/{server_name}/connect", response_model=MCPServerConnectResponse)
async def connect_mcp_server(
    user_id: str,
    server_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConnectResponse:
    """Connect to an MCP server (test connection)."""
    _check_user_access(user_id, current_user_id)

    # 使用 print 确保输出到控制台
    print(f"\n{'='*60}")
    print(f"[MCP Connect] user={user_id}, server={server_name}")
    logger.info(f"[MCP Connect] user={user_id}, server={server_name}")

    server = await mcp_store.get_server(user_id, server_name)
    if not server:
        logger.warning(f"[MCP Connect] Server not found: {server_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )

    logger.info(
        f"[MCP Connect] Server config: name={server.name}, "
        f"command={server.command}, args={server.args}, "
        f"url={server.url}, disabled={server.disabled}"
    )

    if server.disabled:
        logger.warning(f"[MCP Connect] Server is disabled: {server_name}")
        return MCPServerConnectResponse(
            success=False,
            status="disabled",
            tools_count=0,
            tools=[],
            error="Server is disabled. Enable it first.",
        )

    mcp_manager = _get_mcp_connection_manager(request)
    if not mcp_manager:
        logger.error("[MCP Connect] MCP connection manager not available in app state")
        return MCPServerConnectResponse(
            success=False,
            status="error",
            tools_count=0,
            tools=[],
            error="MCP connection manager not available",
        )

    # Create a single-server config and connect
    from dataagent_core.mcp import MCPConfig

    single_config = MCPConfig(servers={server_name: server})
    mcp_client_config = server.to_mcp_client_config()
    logger.info(f"[MCP Connect] MCP client config: {mcp_client_config}")

    try:
        print(f"[MCP Connect] Calling mcp_manager.connect()...")
        connections = await mcp_manager.connect(user_id, single_config)
        conn = connections.get(server_name)

        if conn and conn.connected:
            tools = [t.name for t in conn.tools]
            print(f"[MCP Connect] SUCCESS: {server_name} connected, tools={tools}")
            
            # Check if transport was auto-detected and update database
            detected_transport = conn.server_config.transport
            if server.url and detected_transport != server.transport:
                print(f"[MCP Connect] Auto-detected transport: {detected_transport} (was: {server.transport})")
                server.transport = detected_transport
                await mcp_store.add_server(user_id, server)
                print(f"[MCP Connect] Saved auto-detected transport to database")
            
            print(f"{'='*60}\n")
            return MCPServerConnectResponse(
                success=True,
                status="connected",
                tools_count=len(tools),
                tools=tools,
                error=None,
            )
        else:
            error = conn.error if conn else "Connection failed (no connection object)"
            print(f"[MCP Connect] FAILED: {server_name}, error={error}")
            print(f"{'='*60}\n")
            return MCPServerConnectResponse(
                success=False,
                status="error",
                tools_count=0,
                tools=[],
                error=error,
            )
    except Exception as e:
        import traceback
        print(f"[MCP Connect] EXCEPTION: {server_name}")
        print(traceback.format_exc())
        print(f"{'='*60}\n")
        return MCPServerConnectResponse(
            success=False,
            status="error",
            tools_count=0,
            tools=[],
            error=str(e),
        )


@router.post("/{server_name}/disconnect", response_model=MCPServerConnectResponse)
async def disconnect_mcp_server(
    user_id: str,
    server_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    mcp_store=Depends(get_mcp_store),
) -> MCPServerConnectResponse:
    """Disconnect from an MCP server."""
    _check_user_access(user_id, current_user_id)

    server = await mcp_store.get_server(user_id, server_name)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )

    mcp_manager = _get_mcp_connection_manager(request)
    if mcp_manager:
        await mcp_manager.disconnect(user_id, server_name)

    return MCPServerConnectResponse(
        success=True,
        status="disconnected",
        tools_count=0,
        tools=[],
        error=None,
    )
