"""MCP Server Management page for DataAgent Server Demo."""

import asyncio
import json
import streamlit as st
import httpx

st.set_page_config(page_title="MCP 管理 - DataAgent", page_icon="🔌", layout="wide")


def get_server_url() -> str:
    """Get server URL from session state."""
    return st.session_state.get("server_url", "http://localhost:8000")


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return bool(st.session_state.get("auth_token"))


def get_user_id() -> str:
    """Get current user ID."""
    user = st.session_state.get("auth_user", {})
    return user.get("user_id", st.session_state.get("user_id", "dataagent"))


def get_headers() -> dict:
    """Get request headers."""
    headers = {"X-User-ID": get_user_id()}
    if st.session_state.get("auth_token"):
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
    return headers


async def load_mcp_servers() -> list[dict]:
    """Load MCP servers from server."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_server_url()}/api/v1/users/{get_user_id()}/mcp-servers",
                headers=get_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json().get("servers", [])
    except Exception:
        pass
    return []


async def save_mcp_server(server_config: dict) -> tuple[bool, str]:
    """Save MCP server configuration."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_server_url()}/api/v1/users/{get_user_id()}/mcp-servers",
                headers=get_headers(),
                json=server_config,
                timeout=10.0,
            )
            if response.status_code in (200, 201):
                return True, "保存成功"
            return False, f"保存失败: {response.status_code}"
    except Exception as e:
        return False, f"保存失败: {e}"


async def delete_mcp_server(server_name: str) -> tuple[bool, str]:
    """Delete MCP server."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{get_server_url()}/api/v1/users/{get_user_id()}/mcp-servers/{server_name}",
                headers=get_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return True, "删除成功"
            return False, f"删除失败: {response.status_code}"
    except Exception as e:
        return False, f"删除失败: {e}"


async def connect_mcp_server(server_name: str) -> dict:
    """Connect to MCP server."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_server_url()}/api/v1/users/{get_user_id()}/mcp-servers/{server_name}/connect",
                headers=get_headers(),
                timeout=30.0,
            )
            if response.status_code == 200:
                return response.json()
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def render_server_card(server: dict):
    """Render a single MCP server card."""
    name = server.get("name", "unknown")
    status = server.get("status", "unknown")
    disabled = server.get("disabled", False)
    tools_count = server.get("tools_count", 0)
    
    # Status indicator
    if status == "connected":
        status_icon = "🟢"
        status_text = f"{tools_count} tools"
    elif disabled:
        status_icon = "⚪"
        status_text = "已禁用"
    elif status == "error":
        status_icon = "🔴"
        status_text = "错误"
    else:
        status_icon = "🟡"
        status_text = "未连接"
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            st.markdown(f"**{name}** {status_icon} {status_text}")
            if server.get("url"):
                st.caption(f"URL: {server['url']}")
            elif server.get("command"):
                st.caption(f"Command: {server['command']}")
        
        with col2:
            if not disabled:
                if st.button("🔗 连接", key=f"conn_{name}"):
                    with st.spinner("连接中..."):
                        result = asyncio.run(connect_mcp_server(name))
                    if result.get("success"):
                        st.success(f"连接成功，{result.get('tools_count', 0)} 个工具")
                        st.rerun()
                    else:
                        st.error(f"连接失败: {result.get('error')}")
        
        with col3:
            if st.button("🗑️ 删除", key=f"del_{name}"):
                success, msg = asyncio.run(delete_mcp_server(name))
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def main():
    """Main MCP management page."""
    st.title("🔌 MCP 服务器管理")
    
    # Check login (optional for this page)
    user_id = get_user_id()
    st.caption(f"用户: `{user_id}`")
    
    # Load servers
    if "mcp_servers_cache" not in st.session_state:
        st.session_state.mcp_servers_cache = []
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 服务器列表", "➕ 添加服务器", "📝 JSON 配置"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 刷新", use_container_width=True):
                st.session_state.mcp_servers_cache = asyncio.run(load_mcp_servers())
                st.rerun()
        with col2:
            if st.button("🔗 连接全部", use_container_width=True):
                servers = st.session_state.mcp_servers_cache
                with st.spinner("连接中..."):
                    for server in servers:
                        if not server.get("disabled"):
                            asyncio.run(connect_mcp_server(server["name"]))
                st.session_state.mcp_servers_cache = asyncio.run(load_mcp_servers())
                st.rerun()
        
        # Load servers if cache is empty
        if not st.session_state.mcp_servers_cache:
            st.session_state.mcp_servers_cache = asyncio.run(load_mcp_servers())
        
        servers = st.session_state.mcp_servers_cache
        
        if servers:
            for server in servers:
                render_server_card(server)
        else:
            st.info("暂无 MCP 服务器，请添加")
    
    with tab2:
        st.subheader("添加新服务器")
        
        server_type = st.radio("服务器类型", ["HTTP/SSE", "命令行 (stdio)"], horizontal=True)
        
        with st.form("add_server_form"):
            name = st.text_input("服务器名称 *", placeholder="my-server")
            
            if server_type == "HTTP/SSE":
                url = st.text_input("URL *", placeholder="http://localhost:8080/mcp")
                transport = st.selectbox("传输协议", ["sse", "streamable_http"])
                headers_json = st.text_area("Headers (JSON)", placeholder='{"X-API-Key": "xxx"}')
                command = None
                args = None
            else:
                url = None
                transport = "stdio"
                command = st.text_input("命令 *", placeholder="uvx")
                args_str = st.text_input("参数", placeholder="mcp-server-filesystem /workspace")
                args = args_str.split() if args_str else []
                headers_json = None
            
            env_json = st.text_area("环境变量 (JSON)", placeholder='{"API_KEY": "xxx"}')
            disabled = st.checkbox("禁用")
            
            submitted = st.form_submit_button("添加", use_container_width=True)
            
            if submitted:
                if not name:
                    st.error("请输入服务器名称")
                elif server_type == "HTTP/SSE" and not url:
                    st.error("请输入 URL")
                elif server_type != "HTTP/SSE" and not command:
                    st.error("请输入命令")
                else:
                    server_config = {
                        "name": name,
                        "disabled": disabled,
                    }
                    
                    if url:
                        server_config["url"] = url
                        server_config["transport"] = transport
                        if headers_json:
                            try:
                                server_config["headers"] = json.loads(headers_json)
                            except json.JSONDecodeError:
                                st.error("Headers JSON 格式错误")
                                st.stop()
                    else:
                        server_config["command"] = command
                        server_config["args"] = args or []
                    
                    if env_json:
                        try:
                            server_config["env"] = json.loads(env_json)
                        except json.JSONDecodeError:
                            st.error("环境变量 JSON 格式错误")
                            st.stop()
                    
                    success, msg = asyncio.run(save_mcp_server(server_config))
                    if success:
                        st.success(msg)
                        st.session_state.mcp_servers_cache = []
                        st.rerun()
                    else:
                        st.error(msg)
    
    with tab3:
        st.subheader("JSON 配置")
        st.caption("直接编辑 JSON 配置")
        
        # Convert servers to JSON
        servers = st.session_state.mcp_servers_cache or asyncio.run(load_mcp_servers())
        mcp_config = {"mcpServers": {}}
        for s in servers:
            config = {}
            if s.get("url"):
                config["url"] = s["url"]
                if s.get("transport") and s["transport"] != "sse":
                    config["transport"] = s["transport"]
                if s.get("headers"):
                    config["headers"] = s["headers"]
            else:
                if s.get("command"):
                    config["command"] = s["command"]
                if s.get("args"):
                    config["args"] = s["args"]
            if s.get("env"):
                config["env"] = s["env"]
            if s.get("disabled"):
                config["disabled"] = True
            mcp_config["mcpServers"][s["name"]] = config
        
        json_text = st.text_area(
            "mcp.json",
            value=json.dumps(mcp_config, indent=2, ensure_ascii=False),
            height=300,
        )
        
        if st.button("💾 保存配置", use_container_width=True):
            try:
                new_config = json.loads(json_text)
                new_servers = new_config.get("mcpServers", {})
                
                # Delete all existing
                for s in servers:
                    asyncio.run(delete_mcp_server(s["name"]))
                
                # Add new servers
                for name, cfg in new_servers.items():
                    server_data = {
                        "name": name,
                        "command": cfg.get("command", ""),
                        "args": cfg.get("args", []),
                        "env": cfg.get("env", {}),
                        "url": cfg.get("url"),
                        "transport": cfg.get("transport", "sse"),
                        "headers": cfg.get("headers", {}),
                        "disabled": cfg.get("disabled", False),
                    }
                    asyncio.run(save_mcp_server(server_data))
                
                st.success("配置已保存")
                st.session_state.mcp_servers_cache = []
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"JSON 格式错误: {e}")


if __name__ == "__main__":
    main()
