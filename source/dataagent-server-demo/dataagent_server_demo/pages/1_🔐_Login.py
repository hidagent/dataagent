"""Login page for DataAgent Server Demo."""

import asyncio
import streamlit as st
import httpx

st.set_page_config(page_title="登录 - DataAgent", page_icon="🔐", layout="centered")


def init_session_state():
    """Initialize session state."""
    if "server_url" not in st.session_state:
        st.session_state.server_url = "http://localhost:8000"


def get_server_url() -> str:
    """Get server URL from session state."""
    return st.session_state.get("server_url", "http://localhost:8000")


async def do_login(username: str, password: str) -> dict | None:
    """Perform login request."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_server_url()}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                st.error("用户名或密码错误")
            else:
                st.error(f"登录失败: {response.status_code}")
    except httpx.ConnectError:
        st.error("无法连接到服务器，请检查服务器地址")
    except Exception as e:
        st.error(f"登录失败: {e}")
    return None


async def do_register(
    username: str,
    password: str,
    display_name: str,
    email: str | None,
    department: str | None,
    role: str | None,
) -> dict | None:
    """Perform registration request."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_server_url()}/api/v1/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "display_name": display_name,
                    "email": email or None,
                    "department": department or None,
                    "role": role or None,
                    "user_source": "local",
                },
                timeout=10.0,
            )
            if response.status_code == 201:
                return response.json()
            elif response.status_code == 409:
                st.error("用户名已存在")
            else:
                st.error(f"注册失败: {response.status_code}")
    except httpx.ConnectError:
        st.error("无法连接到服务器")
    except Exception as e:
        st.error(f"注册失败: {e}")
    return None


def main():
    """Main login page."""
    init_session_state()
    
    st.title("🔐 用户登录")
    
    # Check if already logged in
    if st.session_state.get("auth_token"):
        user = st.session_state.get("auth_user", {})
        st.success(f"已登录: {user.get('display_name', user.get('username', ''))}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("前往仪表板", use_container_width=True):
                st.switch_page("pages/2_📊_Dashboard.py")
        with col2:
            if st.button("退出登录", use_container_width=True):
                st.session_state.pop("auth_token", None)
                st.session_state.pop("auth_user", None)
                st.rerun()
        return
    
    # Server URL configuration
    with st.expander("⚙️ 服务器设置", expanded=False):
        server_url = st.text_input(
            "服务器地址",
            value=st.session_state.server_url,
            help="DataAgent Server 的地址",
        )
        if server_url != st.session_state.server_url:
            st.session_state.server_url = server_url
    
    # Login / Register tabs
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            remember = st.checkbox("记住我")
            
            submitted = st.form_submit_button("登录", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    with st.spinner("登录中..."):
                        result = asyncio.run(do_login(username, password))
                        if result:
                            st.session_state.auth_token = result["access_token"]
                            st.session_state.auth_user = result["user"]
                            # Also set user_id for compatibility with existing app
                            st.session_state.user_id = result["user"]["user_id"]
                            st.success("登录成功！")
                            st.balloons()
                            st.switch_page("pages/2_📊_Dashboard.py")
    
    with tab2:
        with st.form("register_form"):
            reg_username = st.text_input("用户名 *", placeholder="3-64 字符", key="reg_username")
            reg_password = st.text_input("密码 *", type="password", placeholder="至少 6 字符", key="reg_password")
            reg_password2 = st.text_input("确认密码 *", type="password", placeholder="再次输入密码", key="reg_password2")
            reg_display_name = st.text_input("显示名称 *", placeholder="您的姓名", key="reg_display_name")
            reg_email = st.text_input("邮箱", placeholder="可选", key="reg_email")
            reg_department = st.text_input("部门", placeholder="可选", key="reg_department")
            reg_role = st.text_input("角色", placeholder="可选", key="reg_role")
            
            reg_submitted = st.form_submit_button("注册", use_container_width=True)
            
            if reg_submitted:
                if not reg_username or not reg_password or not reg_display_name:
                    st.error("请填写必填字段")
                elif len(reg_username) < 3:
                    st.error("用户名至少 3 个字符")
                elif len(reg_password) < 6:
                    st.error("密码至少 6 个字符")
                elif reg_password != reg_password2:
                    st.error("两次输入的密码不一致")
                else:
                    with st.spinner("注册中..."):
                        result = asyncio.run(do_register(
                            reg_username,
                            reg_password,
                            reg_display_name,
                            reg_email,
                            reg_department,
                            reg_role,
                        ))
                        if result:
                            st.success("注册成功！请登录")
                            st.balloons()


if __name__ == "__main__":
    main()
