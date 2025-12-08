"""Sessions History page for DataAgent Server Demo."""

import asyncio
from datetime import datetime
import streamlit as st
import httpx

st.set_page_config(page_title="会话历史 - DataAgent", page_icon="💬", layout="wide")


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


async def load_sessions(limit: int = 20, offset: int = 0) -> dict:
    """Load user sessions."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_server_url()}/api/v1/sessions",
                headers=get_headers(),
                params={"user_id": get_user_id(), "limit": limit, "offset": offset},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"sessions": [], "total": 0}


async def load_session_messages(session_id: str) -> list[dict]:
    """Load messages for a session."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_server_url()}/api/v1/sessions/{session_id}/messages",
                headers=get_headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json().get("messages", [])
    except Exception:
        pass
    return []


async def delete_session(session_id: str) -> tuple[bool, str]:
    """Delete a session."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{get_server_url()}/api/v1/sessions/{session_id}",
                headers=get_headers(),
                timeout=10.0,
            )
            if response.status_code in (200, 204):
                return True, "删除成功"
            return False, f"删除失败: {response.status_code}"
    except Exception as e:
        return False, f"删除失败: {e}"


def format_datetime(dt_str: str | None) -> str:
    """Format datetime string."""
    if not dt_str:
        return "-"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def render_session_card(session: dict):
    """Render a session card."""
    session_id = session.get("session_id", "")
    title = session.get("title") or f"会话 {session_id[:8]}..."
    created_at = format_datetime(session.get("created_at"))
    last_active = format_datetime(session.get("last_active"))
    message_count = session.get("message_count", 0)
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            st.markdown(f"**{title}**")
            st.caption(f"ID: `{session_id[:16]}...` | 创建: {created_at} | 最后活动: {last_active}")
            st.caption(f"消息数: {message_count}")
        
        with col2:
            if st.button("👁️ 查看", key=f"view_{session_id}"):
                st.session_state.selected_session = session_id
                st.rerun()
        
        with col3:
            if st.button("🗑️ 删除", key=f"del_{session_id}"):
                success, msg = asyncio.run(delete_session(session_id))
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render_message(msg: dict):
    """Render a single message."""
    role = msg.get("role", "unknown")
    content = msg.get("content", "")
    created_at = format_datetime(msg.get("created_at"))
    
    if role == "user":
        icon = "👤"
        role_name = "用户"
    elif role == "assistant":
        icon = "🤖"
        role_name = "助手"
    elif role == "system":
        icon = "⚙️"
        role_name = "系统"
    elif role == "tool":
        icon = "🔧"
        role_name = "工具"
    else:
        icon = "❓"
        role_name = role
    
    with st.chat_message(role if role in ["user", "assistant"] else "assistant"):
        st.markdown(f"**{icon} {role_name}** _{created_at}_")
        st.markdown(content)


def main():
    """Main sessions page."""
    st.title("💬 会话历史")
    
    user_id = get_user_id()
    st.caption(f"用户: `{user_id}`")
    
    # Initialize state
    if "selected_session" not in st.session_state:
        st.session_state.selected_session = None
    
    # Session detail view
    if st.session_state.selected_session:
        session_id = st.session_state.selected_session
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← 返回列表"):
                st.session_state.selected_session = None
                st.rerun()
        with col2:
            st.subheader(f"会话: {session_id[:16]}...")
        
        st.divider()
        
        # Load and display messages
        messages = asyncio.run(load_session_messages(session_id))
        
        if messages:
            for msg in messages:
                render_message(msg)
        else:
            st.info("此会话暂无消息")
        
        return
    
    # Sessions list view
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Pagination
    page_size = 10
    if "sessions_page" not in st.session_state:
        st.session_state.sessions_page = 0
    
    offset = st.session_state.sessions_page * page_size
    
    # Load sessions
    result = asyncio.run(load_sessions(limit=page_size, offset=offset))
    sessions = result.get("sessions", [])
    total = result.get("total", 0)
    
    if sessions:
        for session in sessions:
            render_session_card(session)
        
        # Pagination controls
        st.divider()
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.session_state.sessions_page > 0:
                if st.button("← 上一页"):
                    st.session_state.sessions_page -= 1
                    st.rerun()
        
        with col2:
            total_pages = (total + page_size - 1) // page_size
            st.caption(f"第 {st.session_state.sessions_page + 1} / {total_pages} 页 (共 {total} 条)")
        
        with col3:
            if offset + page_size < total:
                if st.button("下一页 →"):
                    st.session_state.sessions_page += 1
                    st.rerun()
    else:
        st.info("暂无会话记录")
        st.caption("开始一个新对话后，会话将显示在这里")


if __name__ == "__main__":
    main()
