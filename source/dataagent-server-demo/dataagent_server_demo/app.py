"""Streamlit demo application for DataAgent Server."""

import asyncio
import json
import time
import uuid
import threading
from typing import Generator

import httpx
import streamlit as st
import websocket


# Page config
st.set_page_config(
    page_title="DataAgent Server Demo",
    page_icon="🤖",
    layout="wide",
)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "connected" not in st.session_state:
        st.session_state.connected = False


def get_server_url(host: str, port: int, use_ssl: bool = False) -> tuple[str, str]:
    """Get HTTP and WebSocket URLs for the server."""
    protocol = "https" if use_ssl else "http"
    ws_protocol = "wss" if use_ssl else "ws"
    http_url = f"{protocol}://{host}:{port}"
    ws_url = f"{ws_protocol}://{host}:{port}"
    return http_url, ws_url


async def check_health(http_url: str, api_key: str | None = None) -> dict | None:
    """Check server health status."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/api/v1/health",
                headers=headers,
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        st.error(f"Health check failed: {e}")
    return None


async def get_sessions(http_url: str, api_key: str | None = None) -> list:
    """Get list of sessions from server."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/api/v1/sessions",
                headers=headers,
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("sessions", [])
    except Exception as e:
        st.error(f"Failed to get sessions: {e}")
    return []


async def get_messages(
    http_url: str,
    session_id: str,
    api_key: str | None = None,
    limit: int = 100,
) -> list:
    """Get messages for a session."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/api/v1/sessions/{session_id}/messages",
                headers=headers,
                params={"limit": limit},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("messages", [])
    except Exception as e:
        st.error(f"Failed to get messages: {e}")
    return []


async def send_chat_rest(
    http_url: str,
    message: str,
    session_id: str,
    api_key: str | None = None,
) -> dict | None:
    """Send chat message via REST API."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{http_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": message,
                    "session_id": session_id,
                },
                timeout=60.0,
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Chat failed: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Chat request failed: {e}")
    return None


def chat_websocket_sync(
    ws_url: str,
    session_id: str,
    message: str,
) -> str:
    """Send chat message via WebSocket and collect response (sync version)."""
    uri = f"{ws_url}/ws/chat/{session_id}"
    full_response = ""
    events = []
    
    try:
        ws = websocket.create_connection(uri, timeout=10)
        
        # Wait for connected event
        connected_msg = ws.recv()
        connected_data = json.loads(connected_msg)
        
        if connected_data.get("event_type") != "connected":
            return f"❌ Unexpected connection response: {connected_data}"
        
        # Send chat message
        ws.send(json.dumps({
            "type": "chat",
            "payload": {"message": message},
        }))
        
        # Receive events
        while True:
            try:
                msg = ws.recv()
                event = json.loads(msg)
                event_type = event.get("event_type")
                data = event.get("data", {})
                events.append(event)
                
                if event_type == "text":
                    content = data.get("content", "")
                    full_response += content
                    
                elif event_type == "tool_call":
                    tool_name = data.get("tool_name", "unknown")
                    tool_args = data.get("tool_args", {})
                    full_response += f"\n\n🔧 **Tool Call**: `{tool_name}`\n```json\n{json.dumps(tool_args, indent=2)}\n```\n"
                    
                elif event_type == "tool_result":
                    result = data.get("result", "")
                    status = data.get("status", "unknown")
                    icon = "✅" if status == "success" else "❌"
                    full_response += f"\n{icon} **Result**: {str(result)[:200]}{'...' if len(str(result)) > 200 else ''}\n"
                    
                elif event_type == "hitl":
                    action = data.get("action", {})
                    full_response += f"\n\n⚠️ **Human Approval Required**\n```json\n{json.dumps(action, indent=2)}\n```\n"
                    # Auto-approve for demo
                    ws.send(json.dumps({
                        "type": "hitl_decision",
                        "payload": {"decisions": [{"type": "approve"}]},
                    }))
                    
                elif event_type == "error":
                    error_msg = data.get("message", "Unknown error")
                    full_response += f"\n\n❌ **Error**: {error_msg}\n"
                    
                elif event_type == "done":
                    cancelled = data.get("cancelled", False)
                    if cancelled:
                        full_response += "\n\n⏹️ *Cancelled*"
                    break
                    
            except websocket.WebSocketTimeoutException:
                full_response += "\n\n⚠️ *Response timeout*"
                break
        
        ws.close()
        
    except websocket.WebSocketException as e:
        full_response = f"❌ WebSocket error: {e}"
    except Exception as e:
        full_response = f"❌ Error: {e}"
    
    return full_response


async def get_mcp_servers(
    http_url: str,
    user_id: str,
    api_key: str | None = None,
) -> list:
    """Get MCP servers for a user."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/api/v1/users/{user_id}/mcp-servers",
                headers=headers,
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return []  # API not implemented yet
    except Exception:
        pass  # API not implemented yet
    return []


async def add_mcp_server(
    http_url: str,
    user_id: str,
    server_config: dict,
    api_key: str | None = None,
) -> bool:
    """Add MCP server for a user."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{http_url}/api/v1/users/{user_id}/mcp-servers",
                headers=headers,
                json=server_config,
                timeout=10.0,
            )
            return response.status_code in (200, 201)
    except Exception:
        return False


async def delete_mcp_server(
    http_url: str,
    user_id: str,
    server_name: str,
    api_key: str | None = None,
) -> bool:
    """Delete MCP server for a user."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{http_url}/api/v1/users/{user_id}/mcp-servers/{server_name}",
                headers=headers,
                timeout=10.0,
            )
            return response.status_code in (200, 204)
    except Exception:
        return False


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Server settings
        st.subheader("Server")
        host = st.text_input("Host", value="localhost")
        port = st.number_input("Port", value=8000, min_value=1, max_value=65535)
        use_ssl = st.checkbox("Use SSL", value=False)
        api_key = st.text_input("API Key (optional)", type="password")

        http_url, ws_url = get_server_url(host, port, use_ssl)

        # Connection test
        if st.button("🔍 Check Health"):
            with st.spinner("Checking..."):
                health = asyncio.run(check_health(http_url, api_key))
                if health:
                    st.success(f"✅ Server healthy: v{health.get('version', 'unknown')}")
                else:
                    st.error("❌ Server unreachable")

        st.divider()

        # Session settings
        st.subheader("Session")
        st.text_input(
            "Session ID",
            value=st.session_state.session_id,
            key="session_id_input",
            on_change=lambda: setattr(
                st.session_state,
                "session_id",
                st.session_state.session_id_input,
            ),
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Session"):
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.messages = []
                st.rerun()

        st.divider()

        # Communication mode
        st.subheader("Mode")
        mode = st.radio(
            "Communication",
            ["WebSocket (Streaming)", "REST API"],
            index=0,
        )

        st.divider()

        # Session browser
        st.subheader("📋 Sessions")
        if st.button("Load Sessions"):
            with st.spinner("Loading..."):
                sessions = asyncio.run(get_sessions(http_url, api_key))
                if sessions:
                    for s in sessions[:10]:
                        sid = s.get("session_id", "")[:8]
                        if st.button(f"📝 {sid}...", key=f"session_{sid}"):
                            st.session_state.session_id = s.get("session_id")
                            st.session_state.messages = []
                            st.rerun()
                else:
                    st.info("No sessions found")

        return http_url, ws_url, api_key, mode


def render_mcp_config(http_url: str, api_key: str | None):
    """Render MCP configuration panel."""
    st.subheader("🔌 MCP Server 配置")
    st.caption("配置 Model Context Protocol 服务器以扩展 Agent 工具能力")

    # User ID for MCP config (using session_id as user_id for demo)
    user_id = st.session_state.get("user_id", "demo-user")

    # Load existing MCP servers
    with st.spinner("加载 MCP 配置..."):
        mcp_servers = asyncio.run(get_mcp_servers(http_url, user_id, api_key))

    if mcp_servers:
        st.write("**已配置的 MCP Servers:**")
        for server in mcp_servers:
            with st.expander(f"🔧 {server.get('name', 'unknown')}", expanded=False):
                st.code(json.dumps(server, indent=2, ensure_ascii=False), language="json")
                status = server.get("status", "unknown")
                status_icon = "🟢" if status == "connected" else "🔴"
                st.caption(f"状态: {status_icon} {status}")
                if st.button(f"删除 {server.get('name')}", key=f"del_{server.get('name')}"):
                    if asyncio.run(delete_mcp_server(http_url, user_id, server.get("name"), api_key)):
                        st.success("已删除")
                        st.rerun()
                    else:
                        st.error("删除失败")
    else:
        st.info("暂无 MCP Server 配置（API 功能开发中）")

    st.divider()

    # Add new MCP server
    st.write("**添加新的 MCP Server:**")

    with st.form("add_mcp_server"):
        name = st.text_input("名称", placeholder="例如: filesystem, database")
        command = st.text_input("命令", placeholder="例如: uvx, npx, python")
        args = st.text_input("参数 (JSON 数组)", placeholder='["mcp-server-filesystem", "/workspace"]')
        env_str = st.text_input("环境变量 (JSON 对象)", placeholder='{"KEY": "value"}')
        disabled = st.checkbox("禁用")

        submitted = st.form_submit_button("➕ 添加 MCP Server")
        if submitted:
            if not name or not command:
                st.error("名称和命令为必填项")
            else:
                try:
                    args_list = json.loads(args) if args else []
                    env_dict = json.loads(env_str) if env_str else {}

                    server_config = {
                        "name": name,
                        "command": command,
                        "args": args_list,
                        "env": env_dict,
                        "disabled": disabled,
                    }

                    if asyncio.run(add_mcp_server(http_url, user_id, server_config, api_key)):
                        st.success(f"已添加 MCP Server: {name}")
                        st.rerun()
                    else:
                        st.warning("添加失败（API 功能开发中）")
                except json.JSONDecodeError as e:
                    st.error(f"JSON 格式错误: {e}")

    # Example configurations
    with st.expander("📖 配置示例"):
        st.markdown("""
**文件系统 MCP Server:**
```json
{
  "name": "filesystem",
  "command": "uvx",
  "args": ["mcp-server-filesystem", "/workspace"],
  "env": {},
  "disabled": false
}
```

**数据库 MCP Server:**
```json
{
  "name": "mysql",
  "command": "uvx",
  "args": ["mcp-server-mysql"],
  "env": {
    "MYSQL_HOST": "localhost",
    "MYSQL_USER": "root",
    "MYSQL_PASSWORD": "password"
  },
  "disabled": false
}
```

**自定义 Python MCP Server:**
```json
{
  "name": "custom",
  "command": "python",
  "args": ["-m", "my_mcp_server"],
  "env": {"API_KEY": "xxx"},
  "disabled": false
}
```
        """)


def render_chat(http_url: str, ws_url: str, api_key: str | None, mode: str):
    """Render main chat interface."""
    st.title("🤖 DataAgent Server Demo")

    # Tabs for Chat and MCP Config
    tab_chat, tab_mcp = st.tabs(["💬 对话", "🔌 MCP 配置"])

    with tab_chat:
        st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

        # Display chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Type your message..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()

                if mode == "WebSocket (Streaming)":
                    message_placeholder.markdown("Connecting...")
                    response = chat_websocket_sync(
                        ws_url,
                        st.session_state.session_id,
                        prompt,
                    )
                    message_placeholder.markdown(response)
                else:
                    message_placeholder.markdown("Thinking...")
                    result = asyncio.run(
                        send_chat_rest(
                            http_url,
                            prompt,
                            st.session_state.session_id,
                            api_key,
                        )
                    )
                    if result:
                        events = result.get("events", [])
                        response = ""
                        for event in events:
                            if event.get("event_type") == "text":
                                response += event.get("data", {}).get("content", "")
                        message_placeholder.markdown(response or "No response")
                    else:
                        response = "Failed to get response"
                        message_placeholder.markdown(response)

                if response:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                    })

    with tab_mcp:
        render_mcp_config(http_url, api_key)


def main():
    """Main entry point."""
    init_session_state()
    http_url, ws_url, api_key, mode = render_sidebar()
    render_chat(http_url, ws_url, api_key, mode)


if __name__ == "__main__":
    main()
