"""Streamlit demo application for DataAgent Server."""

import asyncio
import json
import uuid

import httpx
import streamlit as st
import websocket


# Page config
st.set_page_config(
    page_title="DataAgent Demo",
    page_icon="🤖",
    layout="wide",
)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "user_id" not in st.session_state:
        st.session_state.user_id = "dataagent"
    if "mcp_servers" not in st.session_state:
        st.session_state.mcp_servers = []
    # User profile fields
    if "user_display_name" not in st.session_state:
        st.session_state.user_display_name = ""
    if "user_department" not in st.session_state:
        st.session_state.user_department = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ""


def get_server_url(host: str, port: int, use_ssl: bool = False) -> tuple[str, str]:
    """Get HTTP and WebSocket URLs for the server."""
    protocol = "https" if use_ssl else "http"
    ws_protocol = "wss" if use_ssl else "ws"
    http_url = f"{protocol}://{host}:{port}"
    ws_url = f"{ws_protocol}://{host}:{port}"
    return http_url, ws_url


async def check_health(http_url: str, api_key: str | None = None) -> dict | None:
    """Check server health status."""
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/api/v1/health", headers=headers, timeout=5.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


# MCP API functions
async def load_mcp_servers(
    http_url: str, user_id: str, api_key: str | None = None
) -> list[dict]:
    """Load MCP servers with status from server."""
    headers = {"X-User-ID": user_id}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/api/v1/users/{user_id}/mcp-servers",
                headers=headers,
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json().get("servers", [])
    except Exception:
        pass
    return []


async def save_mcp_server(
    http_url: str, user_id: str, server_config: dict, api_key: str | None = None
) -> tuple[bool, str]:
    """Save MCP server configuration."""
    headers = {"X-User-ID": user_id, "Content-Type": "application/json"}
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
            if response.status_code in (200, 201):
                return True, "保存成功"
            return False, f"保存失败: {response.status_code}"
    except Exception as e:
        return False, f"保存失败: {e}"


async def delete_mcp_server(
    http_url: str, user_id: str, server_name: str, api_key: str | None = None
) -> tuple[bool, str]:
    """Delete MCP server."""
    headers = {"X-User-ID": user_id}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{http_url}/api/v1/users/{user_id}/mcp-servers/{server_name}",
                headers=headers,
                timeout=5.0,
            )
            if response.status_code == 200:
                return True, "删除成功"
            return False, f"删除失败: {response.status_code}"
    except Exception as e:
        return False, f"删除失败: {e}"


async def toggle_mcp_server(
    http_url: str,
    user_id: str,
    server_name: str,
    disabled: bool,
    api_key: str | None = None,
) -> tuple[bool, str]:
    """Enable or disable MCP server."""
    headers = {"X-User-ID": user_id, "Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{http_url}/api/v1/users/{user_id}/mcp-servers/{server_name}/toggle",
                headers=headers,
                json={"disabled": disabled},
                timeout=5.0,
            )
            if response.status_code == 200:
                return True, "已禁用" if disabled else "已启用"
            return False, f"操作失败: {response.status_code}"
    except Exception as e:
        return False, f"操作失败: {e}"


async def connect_mcp_server(
    http_url: str, user_id: str, server_name: str, api_key: str | None = None
) -> dict:
    """Connect to MCP server and get status."""
    import traceback

    url = f"{http_url}/api/v1/users/{user_id}/mcp-servers/{server_name}/connect"
    headers = {"X-User-ID": user_id}
    if api_key:
        headers["X-API-Key"] = api_key

    # 打印请求信息
    print(f"\n{'='*60}")
    print(f"[Demo MCP Connect] POST {url}")
    print(f"[Demo MCP Connect] Headers: {headers}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, timeout=30.0)
            print(f"[Demo MCP Connect] Response Status: {response.status_code}")
            print(f"[Demo MCP Connect] Response Body: {response.text}")
            print(f"{'='*60}\n")

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
    except httpx.ConnectError as e:
        error_msg = f"无法连接到服务器 {http_url}，请确认 Server 已启动"
        print(f"[Demo MCP Connect] ConnectError: {e}")
        print(f"{'='*60}\n")
        return {"success": False, "error": error_msg}
    except httpx.TimeoutException as e:
        error_msg = f"请求超时: {e}"
        print(f"[Demo MCP Connect] Timeout: {e}")
        print(f"{'='*60}\n")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        print(f"[Demo MCP Connect] Exception: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        print(f"{'='*60}\n")
        return {"success": False, "error": error_msg}


async def connect_all_mcp_servers(
    http_url: str, user_id: str, servers: list[dict], api_key: str | None = None
) -> dict[str, dict]:
    """Connect to all enabled MCP servers."""
    results = {}
    for server in servers:
        name = server.get("name")
        disabled = server.get("disabled", False)
        if not disabled and name:
            result = await connect_mcp_server(http_url, user_id, name, api_key)
            results[name] = result
    return results


# Chat functions
def chat_websocket_sync(ws_url: str, session_id: str, user_id: str, message: str) -> str:
    """Send chat message via WebSocket and collect response (non-streaming)."""
    uri = f"{ws_url}/ws/chat/{session_id}"
    full_response = ""

    try:
        ws = websocket.create_connection(uri, timeout=60)

        connected_msg = ws.recv()
        connected_data = json.loads(connected_msg)
        if connected_data.get("event_type") != "connected":
            return f"Connection failed: {connected_data}"

        ws.send(
            json.dumps(
                {"type": "chat", "payload": {"message": message, "user_id": user_id}}
            )
        )

        while True:
            try:
                msg = ws.recv()
                event = json.loads(msg)
                event_type = event.get("event_type")
                data = event.get("data", {})

                if event_type == "text":
                    full_response += data.get("content", "")
                elif event_type == "tool_call":
                    tool_name = data.get("tool_name", "unknown")
                    full_response += f"\n\n🔧 `{tool_name}`\n"
                elif event_type == "tool_result":
                    status = data.get("status", "unknown")
                    icon = "✅" if status == "success" else "❌"
                    result = str(data.get("result", ""))[:200]
                    full_response += f"{icon} {result}\n"
                elif event_type == "hitl":
                    ws.send(
                        json.dumps(
                            {
                                "type": "hitl_decision",
                                "payload": {"decisions": [{"type": "approve"}]},
                            }
                        )
                    )
                elif event_type == "error":
                    full_response += f"\n\n❌ {data.get('message', 'Error')}\n"
                elif event_type == "done":
                    break

            except websocket.WebSocketTimeoutException:
                full_response += "\n\n⚠️ *Timeout*"
                break

        ws.close()

    except Exception as e:
        full_response = f"❌ Error: {e}"

    return full_response


def chat_websocket_streaming(
    ws_url: str, session_id: str, user_id: str, message: str, placeholder,
    user_context: dict | None = None
) -> str:
    """Send chat message via WebSocket with real-time streaming display.
    
    Args:
        ws_url: WebSocket server URL
        session_id: Session ID
        user_id: User ID
        message: User message
        placeholder: Streamlit placeholder for real-time updates
        user_context: Optional user context for personalization
        
    Returns:
        Final response string
    """
    uri = f"{ws_url}/ws/chat/{session_id}"
    full_response = ""
    current_status = ""

    def update_display():
        """Update the placeholder with current content."""
        display_content = full_response
        if current_status:
            display_content += f"\n\n⏳ *{current_status}*"
        placeholder.markdown(display_content + "▌")

    try:
        ws = websocket.create_connection(uri, timeout=120)

        connected_msg = ws.recv()
        connected_data = json.loads(connected_msg)
        if connected_data.get("event_type") != "connected":
            return f"Connection failed: {connected_data}"

        # Build chat payload with user context
        chat_payload = {"message": message, "user_id": user_id}
        if user_context:
            chat_payload["user_context"] = user_context
        
        ws.send(json.dumps({"type": "chat", "payload": chat_payload}))

        current_status = "正在思考..."
        update_display()

        while True:
            try:
                msg = ws.recv()
                event = json.loads(msg)
                event_type = event.get("event_type")
                data = event.get("data", {})

                if event_type == "text":
                    content = data.get("content", "")
                    full_response += content
                    current_status = ""
                    update_display()
                    
                elif event_type == "tool_call":
                    tool_name = data.get("tool_name", "unknown")
                    tool_args = data.get("arguments", {})
                    # 显示工具调用
                    full_response += f"\n\n🔧 **调用工具**: `{tool_name}`\n"
                    # 简化显示参数
                    if tool_args:
                        args_str = json.dumps(tool_args, ensure_ascii=False)
                        if len(args_str) > 100:
                            args_str = args_str[:100] + "..."
                        full_response += f"   参数: `{args_str}`\n"
                    current_status = f"执行 {tool_name}..."
                    update_display()
                    
                elif event_type == "tool_result":
                    status = data.get("status", "unknown")
                    result = data.get("result", "")
                    icon = "✅" if status == "success" else "❌"
                    
                    # 格式化结果显示
                    result_str = str(result)
                    if len(result_str) > 300:
                        result_str = result_str[:300] + "..."
                    
                    full_response += f"{icon} {result_str}\n"
                    current_status = ""
                    update_display()
                    
                elif event_type == "hitl":
                    # 自动批准
                    current_status = "等待审批..."
                    update_display()
                    ws.send(
                        json.dumps(
                            {
                                "type": "hitl_decision",
                                "payload": {"decisions": [{"type": "approve"}]},
                            }
                        )
                    )
                    current_status = ""
                    
                elif event_type == "error":
                    error_msg = data.get("message", "Unknown error")
                    full_response += f"\n\n❌ **错误**: {error_msg}\n"
                    current_status = ""
                    update_display()
                    
                elif event_type == "done":
                    current_status = ""
                    break

            except websocket.WebSocketTimeoutException:
                full_response += "\n\n⚠️ *请求超时*"
                break

        ws.close()

    except Exception as e:
        full_response = f"❌ 连接错误: {e}"

    # Final update without cursor
    placeholder.markdown(full_response)
    return full_response


def send_chat_rest(
    http_url: str,
    session_id: str,
    user_id: str,
    message: str,
    api_key: str | None = None,
) -> str:
    """Send chat message via REST API."""
    headers = {"Content-Type": "application/json", "X-User-ID": user_id}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{http_url}/api/v1/chat",
                headers=headers,
                json={"session_id": session_id, "message": message},
            )
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                text_parts = []
                for event in events:
                    if event.get("event_type") == "text":
                        text_parts.append(event.get("data", {}).get("content", ""))
                return "".join(text_parts) or "No response"
            return f"❌ Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"❌ Error: {e}"


def render_mcp_server_row(server: dict, http_url: str, api_key: str | None):
    """Render a single MCP server row (Cursor style)."""
    name = server.get("name", "unknown")
    status = server.get("status", "unknown")
    disabled = server.get("disabled", False)
    tools_count = server.get("tools_count", 0)
    error = server.get("error")

    # Status indicator
    if status == "connected":
        status_icon = "🟢"
        status_text = f"{tools_count} tools"
    elif status == "disabled":
        status_icon = "⚪"
        status_text = "Disabled"
    elif status == "error":
        status_icon = "🔴"
        status_text = "Error"
    else:
        status_icon = "🟡"
        status_text = "Disconnected"

    # Row layout: [name + status] [connect] [delete] [toggle]
    col1, col2, col3, col4 = st.columns([4, 1, 1, 1])

    with col1:
        # Name with first letter as icon
        first_letter = name[0].upper() if name else "M"
        st.markdown(f"**{first_letter}** &nbsp; {name}")
        # Status with error expandable
        if error and status == "error":
            with st.expander(f"{status_icon} {status_text} - Show Output", expanded=False):
                st.code(error, language=None)
        else:
            st.caption(f"{status_icon} {status_text}")

    with col2:
        # Test connection button
        if not disabled:
            if st.button("🔗", key=f"conn_{name}", help="测试连接"):
                with st.spinner("连接中..."):
                    # 构建请求 URL 用于显示
                    connect_url = f"{http_url}/api/v1/users/{st.session_state.user_id}/mcp-servers/{name}/connect"
                    st.info(f"📡 请求: POST {connect_url}")

                    result = asyncio.run(
                        connect_mcp_server(
                            http_url, st.session_state.user_id, name, api_key
                        )
                    )

                    # 显示完整响应
                    st.code(json.dumps(result, indent=2, ensure_ascii=False), language="json")

                if result.get("success"):
                    st.success(f"✅ {name} 连接成功，{result.get('tools_count', 0)} 个工具")
                    st.session_state.mcp_servers = []
                    st.rerun()
                else:
                    st.error(f"❌ {name} 连接失败: {result.get('error', 'Unknown error')}")

    with col3:
        # Delete button
        if st.button("🗑️", key=f"del_{name}", help="删除"):
            success, msg = asyncio.run(
                delete_mcp_server(http_url, st.session_state.user_id, name, api_key)
            )
            if success:
                st.session_state.mcp_servers = []
                st.rerun()

    with col4:
        # Toggle switch
        is_enabled = not disabled
        new_enabled = st.toggle(
            "启用",
            value=is_enabled,
            key=f"toggle_{name}",
            label_visibility="collapsed",
        )
        if new_enabled != is_enabled:
            success, _ = asyncio.run(
                toggle_mcp_server(
                    http_url, st.session_state.user_id, name, not new_enabled, api_key
                )
            )
            if success:
                st.session_state.mcp_servers = []
                st.rerun()


def servers_to_json(servers: list[dict]) -> str:
    """Convert server list to JSON config format."""
    mcp_servers = {}
    for s in servers:
        config = {}
        if s.get("url"):
            config["url"] = s["url"]
            # 添加 transport 类型
            if s.get("transport") and s.get("transport") != "sse":
                config["transport"] = s["transport"]
        else:
            if s.get("command"):
                config["command"] = s["command"]
            if s.get("args"):
                config["args"] = s["args"]
        if s.get("env"):
            config["env"] = s["env"]
        if s.get("headers"):
            config["headers"] = s["headers"]
        if s.get("disabled"):
            config["disabled"] = True
        mcp_servers[s["name"]] = config
    return json.dumps({"mcpServers": mcp_servers}, indent=2, ensure_ascii=False)


def render_mcp_management(http_url: str, api_key: str | None):
    """Render MCP management section (Cursor style)."""
    st.subheader("🔌 MCP Servers")

    # Load servers
    if not st.session_state.mcp_servers:
        st.session_state.mcp_servers = asyncio.run(
            load_mcp_servers(http_url, st.session_state.user_id, api_key)
        )

    servers = st.session_state.mcp_servers

    # Tab: List view / JSON config
    tab1, tab2 = st.tabs(["📋 服务器列表", "📝 JSON 配置"])

    with tab1:
        # Buttons row
        col_refresh, col_connect_all = st.columns(2)
        with col_refresh:
            if st.button("🔄 刷新状态", key="refresh_mcp", use_container_width=True):
                st.session_state.mcp_servers = asyncio.run(
                    load_mcp_servers(http_url, st.session_state.user_id, api_key)
                )
                st.rerun()
        with col_connect_all:
            if st.button("🔗 连接全部", key="connect_all_mcp", use_container_width=True):
                with st.spinner("正在连接所有服务器..."):
                    results = asyncio.run(
                        connect_all_mcp_servers(
                            http_url, st.session_state.user_id, servers, api_key
                        )
                    )
                    success_count = sum(1 for r in results.values() if r.get("success"))
                    total = len(results)
                    if success_count == total and total > 0:
                        st.success(f"✅ 全部连接成功 ({success_count}/{total})")
                    elif success_count > 0:
                        st.warning(f"⚠️ 部分连接成功 ({success_count}/{total})")
                    elif total > 0:
                        st.error(f"❌ 连接失败 (0/{total})")
                    st.session_state.mcp_servers = asyncio.run(
                        load_mcp_servers(http_url, st.session_state.user_id, api_key)
                    )
                    st.rerun()

        # Server list
        if servers:
            for server in servers:
                render_mcp_server_row(server, http_url, api_key)
        else:
            st.info("暂无 MCP 服务器，请在 JSON 配置中添加")

    with tab2:
        st.caption("使用 JSON 格式配置 MCP 服务器")

        # Initialize mcp_json in session state
        if "mcp_json" not in st.session_state:
            st.session_state.mcp_json = servers_to_json(servers) if servers else '{\n  "mcpServers": {}\n}'

        # Load from server button
        if st.button("📥 从服务器加载", key="load_json"):
            servers = asyncio.run(
                load_mcp_servers(http_url, st.session_state.user_id, api_key)
            )
            st.session_state.mcp_json = servers_to_json(servers)
            st.session_state.mcp_servers = servers
            st.rerun()

        # JSON editor
        mcp_json = st.text_area(
            "mcp.json",
            value=st.session_state.mcp_json,
            height=300,
            key="mcp_json_editor",
            label_visibility="collapsed",
        )

        # Save button
        if st.button("💾 保存配置", key="save_json", use_container_width=True):
            try:
                config = json.loads(mcp_json)
                mcp_servers = config.get("mcpServers", {})

                if not mcp_servers:
                    st.warning("配置为空")
                else:
                    # Delete all existing servers first
                    for s in st.session_state.mcp_servers:
                        asyncio.run(
                            delete_mcp_server(
                                http_url, st.session_state.user_id, s["name"], api_key
                            )
                        )

                    # Save new servers
                    success_count = 0
                    for name, cfg in mcp_servers.items():
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
                        success, _ = asyncio.run(
                            save_mcp_server(
                                http_url, st.session_state.user_id, server_data, api_key
                            )
                        )
                        if success:
                            success_count += 1

                    st.success(f"✅ 已保存 {success_count} 个服务器")
                    st.session_state.mcp_json = mcp_json
                    st.session_state.mcp_servers = []
                    st.info("💡 新建会话后生效")
                    st.rerun()

            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 格式错误: {e}")

        # Example
        with st.expander("📖 配置示例"):
            st.code(
                """{
  "mcpServers": {
    "my-server": {
      "url": "http://localhost:9042/mcp",
      "transport": "streamable_http",
      "headers": {
        "X-API-Key": "your-api-key",
        "X-Custom-Header": "value"
      }
    },
    "sse-server": {
      "url": "http://localhost:8080/sse"
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/workspace"]
    }
  }
}""",
                language="json",
            )
            st.caption("transport: 'sse'(默认) 或 'streamable_http'")


def render_sidebar():
    """Render sidebar with server config and session controls."""
    with st.sidebar:
        st.title("⚙️ 设置")

        # Server Configuration
        st.subheader("服务器配置")
        host = st.text_input("Host", value="localhost")
        port = st.number_input("Port", value=8000, min_value=1, max_value=65535)
        use_ssl = st.checkbox("使用 SSL", value=False)
        api_key = st.text_input("API Key (可选)", type="password")

        http_url, ws_url = get_server_url(host, port, use_ssl)

        if st.button("🔍 检查连接"):
            health = asyncio.run(check_health(http_url, api_key))
            if health:
                st.success(f"✅ 服务器正常")
            else:
                st.error("❌ 无法连接服务器")

        st.divider()

        # User Profile Configuration
        st.subheader("👤 用户信息")
        user_id = st.text_input("User ID", value=st.session_state.user_id)
        if user_id != st.session_state.user_id:
            st.session_state.user_id = user_id
            st.session_state.mcp_servers = []  # Reset MCP servers
        
        # User profile fields for personalization
        with st.expander("📝 个人信息（用于AI个性化）", expanded=False):
            display_name = st.text_input(
                "姓名", 
                value=st.session_state.user_display_name,
                placeholder="例如：张三",
                help="AI将使用此姓名来识别'我'指代的用户"
            )
            if display_name != st.session_state.user_display_name:
                st.session_state.user_display_name = display_name
            
            department = st.text_input(
                "部门",
                value=st.session_state.user_department,
                placeholder="例如：数据部",
            )
            if department != st.session_state.user_department:
                st.session_state.user_department = department
            
            role = st.text_input(
                "角色",
                value=st.session_state.user_role,
                placeholder="例如：数据工程师",
            )
            if role != st.session_state.user_role:
                st.session_state.user_role = role
            
            st.caption("💡 设置后，AI将能够回答'我是谁'并理解'我的'指代")

        st.divider()

        # Session Controls
        st.subheader("会话管理")
        st.text_input("Session ID", value=st.session_state.session_id, disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 新建会话"):
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🗑️ 清空消息"):
                st.session_state.messages = []
                st.rerun()

        st.divider()

        # Communication Mode
        st.subheader("通信模式")
        mode = st.radio("选择模式", ["WebSocket", "REST API"], horizontal=True)

        st.divider()

        # MCP Management
        render_mcp_management(http_url, api_key)

    return http_url, ws_url, api_key, mode


def main():
    """Main application entry point."""
    init_session_state()

    # Render sidebar and get config
    http_url, ws_url, api_key, mode = render_sidebar()

    # Main chat area
    st.title("🤖 DataAgent Demo")

    # Show session info with user display name if set
    user_info = st.session_state.user_id
    if st.session_state.user_display_name:
        user_info = f"{st.session_state.user_display_name} ({st.session_state.user_id})"
    st.caption(f"📍 Session: `{st.session_state.session_id[:8]}...` | User: `{user_info}`")

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("输入消息..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build user context if profile is configured
        user_context = None
        if st.session_state.user_display_name:
            user_context = {
                "user_id": st.session_state.user_id,
                "username": st.session_state.user_id,
                "display_name": st.session_state.user_display_name,
                "department": st.session_state.user_department or None,
                "role": st.session_state.user_role or None,
                "is_anonymous": False,
            }

        with st.chat_message("assistant"):
            if mode == "WebSocket":
                # 使用流式显示
                response_placeholder = st.empty()
                response = chat_websocket_streaming(
                    ws_url, st.session_state.session_id, st.session_state.user_id, 
                    prompt, response_placeholder, user_context
                )
            else:
                # REST API 模式使用 spinner
                with st.spinner("思考中..."):
                    response = send_chat_rest(
                        http_url, st.session_state.session_id, st.session_state.user_id, prompt, api_key
                    )
                st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
