"""Workspaces Management page for DataAgent Server Demo."""

import asyncio
import streamlit as st
import httpx

st.set_page_config(page_title="工作空间 - DataAgent", page_icon="📁", layout="wide")


def get_server_url() -> str:
    """Get server URL from session state."""
    return st.session_state.get("server_url", "http://localhost:8000")


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


def format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


async def get_memory_status() -> dict:
    """Get user memory status."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_server_url()}/api/v1/users/{get_user_id()}/memory/status",
                headers=get_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"exists": False, "size_bytes": 0, "file_count": 0}


async def delete_memory() -> tuple[bool, str]:
    """Delete user memory."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{get_server_url()}/api/v1/users/{get_user_id()}/memory",
                headers=get_headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                return True, response.json().get("message", "删除成功")
            return False, f"删除失败: {response.status_code}"
    except Exception as e:
        return False, f"删除失败: {e}"


def main():
    """Main workspaces page."""
    st.title("📁 工作空间管理")
    
    user_id = get_user_id()
    st.caption(f"用户: `{user_id}`")
    
    # Memory status section
    st.subheader("💾 Agent 记忆存储")
    
    memory_status = asyncio.run(get_memory_status())
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("状态", "存在" if memory_status.get("exists") else "不存在")
        
        with col2:
            st.metric("大小", format_bytes(memory_status.get("size_bytes", 0)))
        
        with col3:
            st.metric("文件数", memory_status.get("file_count", 0))
        
        if memory_status.get("path"):
            st.caption(f"路径: `{memory_status['path']}`")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 刷新", use_container_width=True):
                st.rerun()
        with col2:
            if memory_status.get("exists"):
                if st.button("🗑️ 清除记忆", type="secondary", use_container_width=True):
                    success, msg = asyncio.run(delete_memory())
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    
    st.divider()
    
    # Workspaces section (placeholder)
    st.subheader("📂 工作空间列表")
    
    st.info("""
    工作空间功能正在开发中...
    
    计划功能：
    - 创建和管理多个工作空间
    - 设置默认工作空间
    - 配额管理（大小限制、文件数限制）
    - 工作空间共享
    """)
    
    # Example workspace card
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown("**默认工作空间** 🏠")
            st.caption(f"路径: `~/.dataagent/workspaces/{user_id}/default`")
            
            # Quota progress bar (example)
            usage_pct = 0.45
            st.progress(usage_pct)
            st.caption(f"已使用: 450 MB / 1 GB ({usage_pct*100:.0f}%)")
        
        with col2:
            st.button("⚙️ 设置", disabled=True, use_container_width=True)


if __name__ == "__main__":
    main()
