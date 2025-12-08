"""Dashboard page for DataAgent Server Demo."""

import asyncio
import streamlit as st
import httpx

st.set_page_config(page_title="仪表板 - DataAgent", page_icon="📊", layout="wide")


def get_server_url() -> str:
    """Get server URL from session state."""
    return st.session_state.get("server_url", "http://localhost:8000")


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return bool(st.session_state.get("auth_token"))


def get_current_user() -> dict:
    """Get current user info."""
    return st.session_state.get("auth_user", {})


async def fetch_stats(user_id: str) -> dict:
    """Fetch user statistics."""
    stats = {
        "sessions": 0,
        "messages": 0,
        "mcp_servers": 0,
        "workspaces": 0,
    }
    
    headers = {"X-User-ID": user_id}
    if st.session_state.get("auth_token"):
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
    
    try:
        async with httpx.AsyncClient() as client:
            # Get sessions count
            response = await client.get(
                f"{get_server_url()}/api/v1/sessions",
                headers=headers,
                params={"user_id": user_id, "limit": 1},
                timeout=5.0,
            )
            if response.status_code == 200:
                stats["sessions"] = response.json().get("total", 0)
            
            # Get MCP servers count
            response = await client.get(
                f"{get_server_url()}/api/v1/users/{user_id}/mcp-servers",
                headers=headers,
                timeout=5.0,
            )
            if response.status_code == 200:
                stats["mcp_servers"] = len(response.json().get("servers", []))
    except Exception:
        pass
    
    return stats


def main():
    """Main dashboard page."""
    st.title("📊 用户仪表板")
    
    # Check login
    if not is_logged_in():
        st.warning("请先登录")
        if st.button("前往登录", use_container_width=True):
            st.switch_page("pages/1_🔐_Login.py")
        return
    
    user = get_current_user()
    user_id = user.get("user_id", "")
    
    # User info header
    st.markdown(f"### 👋 欢迎, {user.get('display_name', user.get('username', ''))}")
    
    # Stats cards
    stats = asyncio.run(fetch_stats(user_id))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💬 会话数", stats["sessions"])
    with col2:
        st.metric("📝 消息数", stats["messages"])
    with col3:
        st.metric("🔌 MCP 服务器", stats["mcp_servers"])
    with col4:
        st.metric("📁 工作空间", stats["workspaces"])
    
    st.divider()
    
    # User profile section
    with st.expander("👤 个人信息", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**用户 ID**: `{user.get('user_id', '-')}`")
            st.write(f"**用户名**: {user.get('username', '-')}")
            st.write(f"**显示名称**: {user.get('display_name', '-')}")
        
        with col2:
            st.write(f"**邮箱**: {user.get('email', '-')}")
            st.write(f"**部门**: {user.get('department', '-')}")
            st.write(f"**角色**: {user.get('role', '-')}")
    
    st.divider()
    
    # Quick actions
    st.subheader("🚀 快速操作")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💬 开始对话", use_container_width=True):
            st.switch_page("app.py")
    
    with col2:
        if st.button("🔌 配置 MCP", use_container_width=True):
            st.switch_page("pages/3_🔌_MCP.py")
    
    with col3:
        if st.button("📁 工作空间", use_container_width=True):
            st.switch_page("pages/4_📁_Workspaces.py")
    
    with col4:
        if st.button("📜 会话历史", use_container_width=True):
            st.switch_page("pages/5_💬_Sessions.py")
    
    st.divider()
    
    # Logout button
    if st.button("🚪 退出登录", type="secondary"):
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_user", None)
        st.success("已退出登录")
        st.switch_page("pages/1_🔐_Login.py")


if __name__ == "__main__":
    main()
