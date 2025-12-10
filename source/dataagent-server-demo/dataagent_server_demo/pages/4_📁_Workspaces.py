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


async def get_workspaces() -> list[dict]:
    """Get user workspaces from API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_server_url()}/api/v1/workspaces",
                headers=get_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("workspaces", [])
    except Exception as e:
        st.error(f"获取工作空间失败: {e}")
    return []


async def get_default_workspace() -> dict | None:
    """Get user's default workspace."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_server_url()}/api/v1/workspaces/default",
                headers=get_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


async def set_default_workspace(workspace_id: str) -> tuple[bool, str]:
    """Set a workspace as default."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_server_url()}/api/v1/workspaces/{workspace_id}/set-default",
                headers=get_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return True, "设置成功"
            return False, f"设置失败: {response.status_code}"
    except Exception as e:
        return False, f"设置失败: {e}"


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
    
    # Default workspace section
    st.subheader("🏠 当前工作空间")
    
    default_workspace = asyncio.run(get_default_workspace())
    
    with st.container(border=True):
        if default_workspace:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("名称", default_workspace.get("name", "未命名"))
            
            with col2:
                current_size = default_workspace.get("current_size_bytes", 0)
                max_size = default_workspace.get("max_size_bytes", 1073741824)
                st.metric("已用空间", format_bytes(current_size))
            
            with col3:
                current_files = default_workspace.get("current_file_count", 0)
                max_files = default_workspace.get("max_files", 10000)
                st.metric("文件数", f"{current_files} / {max_files}")
            
            st.caption(f"路径: `{default_workspace.get('path', '未知')}`")
            
            # Usage progress bar
            if max_size > 0:
                usage_pct = current_size / max_size
                st.progress(min(usage_pct, 1.0))
                st.caption(f"配额: {format_bytes(current_size)} / {format_bytes(max_size)} ({usage_pct*100:.1f}%)")
        else:
            st.info("暂无默认工作空间，将在首次聊天时自动创建")
        
        if st.button("🔄 刷新", key="refresh_default", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # All workspaces section
    st.subheader("📂 工作空间列表")
    
    workspaces = asyncio.run(get_workspaces())
    
    if workspaces:
        for ws in workspaces:
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 1, 1])
                
                with col1:
                    name = ws.get("name", "未命名")
                    is_default = ws.get("is_default", False)
                    if is_default:
                        st.markdown(f"**{name}** 🏠 (默认)")
                    else:
                        st.markdown(f"**{name}**")
                    st.caption(f"路径: `{ws.get('path', '未知')}`")
                    
                    # Usage info
                    current_size = ws.get("current_size_bytes", 0)
                    max_size = ws.get("max_size_bytes", 1073741824)
                    st.caption(f"使用: {format_bytes(current_size)} / {format_bytes(max_size)}")
                
                with col2:
                    if not is_default:
                        if st.button("设为默认", key=f"default_{ws.get('workspace_id')}"):
                            success, msg = asyncio.run(set_default_workspace(ws.get("workspace_id")))
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                
                with col3:
                    st.caption(f"权限: {ws.get('permission', 'unknown')}")
    else:
        st.info("暂无工作空间")
    
    st.divider()
    
    # Memory status section (Agent memory, separate from workspace)
    st.subheader("💾 Agent 记忆存储")
    st.caption("Agent 记忆存储与工作空间是独立的，用于存储 Agent 的学习记忆")
    
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
            if st.button("🔄 刷新", key="refresh_memory", use_container_width=True):
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


if __name__ == "__main__":
    main()
