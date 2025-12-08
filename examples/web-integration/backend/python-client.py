#!/usr/bin/env python3
"""DataAgent Python 客户端示例。

演示如何使用 Python 与 DataAgent Server 进行交互，
包括 REST API、SSE 流式和 WebSocket 三种方式。

使用方法:
    pip install httpx websockets
    python python-client.py
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator

import httpx


class DataAgentClient:
    """DataAgent API 客户端。"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        user_id: str = "python-client",
    ):
        """初始化客户端。
        
        Args:
            base_url: 服务器地址
            api_key: API Key（可选）
            user_id: 用户 ID
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user_id = user_id
        self.session_id: str | None = None
    
    def _get_headers(self) -> dict:
        """获取请求头。"""
        headers = {
            "Content-Type": "application/json",
            "X-User-ID": self.user_id,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def health_check(self) -> dict:
        """健康检查。
        
        Returns:
            健康状态信息
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/health",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def chat(self, message: str, session_id: str | None = None) -> dict:
        """发送消息（同步方式）。
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选）
            
        Returns:
            包含 session_id 和 events 的响应
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/chat",
                headers=self._get_headers(),
                json={
                    "message": message,
                    "session_id": session_id or self.session_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            self.session_id = data.get("session_id")
            return data
    
    async def chat_stream(
        self,
        message: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """发送消息（SSE 流式方式）。
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选）
            
        Yields:
            事件字典
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/v1/chat/stream",
                headers=self._get_headers(),
                json={
                    "message": message,
                    "session_id": session_id or self.session_id,
                },
            ) as response:
                response.raise_for_status()
                
                # 获取 session_id
                new_session_id = response.headers.get("X-Session-ID")
                if new_session_id:
                    self.session_id = new_session_id
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            yield event
                        except json.JSONDecodeError:
                            continue
    
    async def list_sessions(self) -> dict:
        """列出用户的所有会话。
        
        Returns:
            会话列表
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions",
                headers=self._get_headers(),
                params={"user_id": self.user_id},
            )
            response.raise_for_status()
            return response.json()
    
    async def get_session(self, session_id: str) -> dict:
        """获取会话详情。
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话信息
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """获取会话的消息历史。
        
        Args:
            session_id: 会话 ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            消息列表
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/messages",
                headers=self._get_headers(),
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话。
        
        Args:
            session_id: 会话 ID
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
    
    async def list_assistants(self) -> dict:
        """列出所有助手。
        
        Returns:
            助手列表
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/assistants",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    # ============ 用户档案管理 ============
    
    async def list_user_profiles(self) -> dict:
        """列出所有用户档案。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/user-profiles",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_profile(self, user_id: str) -> dict:
        """获取用户档案。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/user-profiles/{user_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def create_user_profile(self, profile: dict) -> dict:
        """创建用户档案。
        
        Args:
            profile: 用户档案信息，包含 user_id, username, display_name 等
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/user-profiles",
                headers=self._get_headers(),
                json=profile,
            )
            response.raise_for_status()
            return response.json()
    
    async def update_user_profile(self, user_id: str, profile: dict) -> dict:
        """更新用户档案。"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/api/v1/user-profiles/{user_id}",
                headers=self._get_headers(),
                json=profile,
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_user_profile(self, user_id: str) -> dict:
        """删除用户档案。"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/user-profiles/{user_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    # ============ MCP 服务器管理 ============
    
    async def list_mcp_servers(self) -> dict:
        """列出用户的 MCP 服务器。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def add_mcp_server(self, server_config: dict) -> dict:
        """添加 MCP 服务器。
        
        Args:
            server_config: 服务器配置，包含 name, command, args 或 url 等
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers",
                headers=self._get_headers(),
                json=server_config,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_mcp_server(self, server_name: str) -> dict:
        """获取 MCP 服务器详情。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers/{server_name}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def get_mcp_server_status(self, server_name: str) -> dict:
        """获取 MCP 服务器状态。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers/{server_name}/status",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def connect_mcp_server(self, server_name: str) -> dict:
        """连接 MCP 服务器。"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers/{server_name}/connect",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def disconnect_mcp_server(self, server_name: str) -> dict:
        """断开 MCP 服务器。"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers/{server_name}/disconnect",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def toggle_mcp_server(self, server_name: str, disabled: bool) -> dict:
        """启用/禁用 MCP 服务器。"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers/{server_name}/toggle",
                headers=self._get_headers(),
                json={"disabled": disabled},
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_mcp_server(self, server_name: str) -> dict:
        """删除 MCP 服务器。"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/users/{self.user_id}/mcp-servers/{server_name}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    # ============ 规则管理 ============
    
    async def list_rules(self, scope: str | None = None) -> dict:
        """列出用户的规则。
        
        Args:
            scope: 可选，过滤范围 (global, user, project, session)
        """
        params = {}
        if scope:
            params["scope"] = scope
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()
    
    async def create_rule(self, rule: dict) -> dict:
        """创建规则。
        
        Args:
            rule: 规则配置，包含 name, description, content, scope 等
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules",
                headers=self._get_headers(),
                json=rule,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_rule(self, rule_name: str) -> dict:
        """获取规则详情。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules/{rule_name}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def update_rule(self, rule_name: str, updates: dict) -> dict:
        """更新规则。"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules/{rule_name}",
                headers=self._get_headers(),
                json=updates,
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_rule(self, rule_name: str) -> dict:
        """删除规则。"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules/{rule_name}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def validate_rule(self, content: str) -> dict:
        """验证规则内容。"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules/validate",
                headers=self._get_headers(),
                json={"content": content},
            )
            response.raise_for_status()
            return response.json()
    
    async def list_rule_conflicts(self) -> dict:
        """检测规则冲突。"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules/conflicts/list",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
    
    async def reload_rules(self) -> dict:
        """重新加载规则。"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/{self.user_id}/rules/reload",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()


class DataAgentWebSocketClient:
    """DataAgent WebSocket 客户端。"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        user_id: str = "ws-client",
    ):
        """初始化 WebSocket 客户端。
        
        Args:
            base_url: 服务器地址
            user_id: 用户 ID
        """
        self.ws_url = base_url.replace("http", "ws").rstrip("/")
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self._ws = None
    
    async def connect(self) -> None:
        """建立 WebSocket 连接。"""
        import websockets
        
        url = f"{self.ws_url}/ws/chat/{self.session_id}"
        self._ws = await websockets.connect(url)
        
        # 等待连接确认
        response = await self._ws.recv()
        data = json.loads(response)
        if data.get("event_type") == "connected":
            print(f"WebSocket 已连接，会话 ID: {data['data']['session_id']}")
    
    async def send_message(self, message: str) -> AsyncGenerator[dict, None]:
        """发送消息并接收响应流。
        
        Args:
            message: 用户消息
            
        Yields:
            服务器事件
        """
        if not self._ws:
            raise RuntimeError("WebSocket 未连接")
        
        # 发送消息
        await self._ws.send(json.dumps({
            "type": "chat",
            "payload": {
                "message": message,
                "user_id": self.user_id,
            }
        }))
        
        # 接收响应
        while True:
            response = await self._ws.recv()
            data = json.loads(response)
            yield data
            
            if data.get("event_type") == "done":
                break
    
    async def send_hitl_decision(self, decision: str) -> None:
        """发送 HITL 决定。
        
        Args:
            decision: "approve" 或 "reject"
        """
        if not self._ws:
            raise RuntimeError("WebSocket 未连接")
        
        await self._ws.send(json.dumps({
            "type": "hitl_decision",
            "payload": {
                "decisions": [{"type": decision}]
            }
        }))
    
    async def cancel(self) -> None:
        """取消当前操作。"""
        if not self._ws:
            return
        
        await self._ws.send(json.dumps({
            "type": "cancel",
            "payload": {}
        }))
    
    async def close(self) -> None:
        """关闭连接。"""
        if self._ws:
            await self._ws.close()
            self._ws = None


# ============ 使用示例 ============

async def demo_rest_api():
    """演示 REST API 使用。"""
    print("\n" + "=" * 50)
    print("REST API 示例")
    print("=" * 50)
    
    client = DataAgentClient()
    
    # 健康检查
    print("\n1. 健康检查:")
    try:
        health = await client.health_check()
        print(f"   状态: {health['status']}, 版本: {health['version']}")
    except Exception as e:
        print(f"   错误: {e}")
        return
    
    # 发送消息
    print("\n2. 发送消息 (同步):")
    try:
        response = await client.chat("你好，请介绍一下你自己")
        print(f"   会话 ID: {response['session_id']}")
        
        for event in response["events"]:
            if event.get("event_type") == "text":
                content = event.get("content", "")
                if content:
                    print(f"   回复: {content[:100]}...")
    except Exception as e:
        print(f"   错误: {e}")


async def demo_sse_stream():
    """演示 SSE 流式 API 使用。"""
    print("\n" + "=" * 50)
    print("SSE 流式 API 示例")
    print("=" * 50)
    
    client = DataAgentClient()
    
    print("\n发送消息 (流式):")
    try:
        full_content = ""
        async for event in client.chat_stream("请用一句话介绍 Python"):
            event_type = event.get("event_type")
            
            if event_type == "text":
                content = event.get("data", {}).get("content", "") or event.get("content", "")
                full_content += content
                print(content, end="", flush=True)
            elif event_type == "tool_call":
                tool_name = event.get("data", {}).get("tool_name", "")
                print(f"\n   [工具调用: {tool_name}]")
            elif event_type == "done":
                print("\n   [完成]")
        
        print(f"\n   完整回复: {full_content[:100]}...")
    except Exception as e:
        print(f"   错误: {e}")


async def demo_websocket():
    """演示 WebSocket 使用。"""
    print("\n" + "=" * 50)
    print("WebSocket 示例")
    print("=" * 50)
    
    try:
        import websockets
    except ImportError:
        print("   请先安装 websockets: pip install websockets")
        return
    
    client = DataAgentWebSocketClient()
    
    try:
        print("\n1. 建立连接:")
        await client.connect()
        
        print("\n2. 发送消息:")
        async for event in client.send_message("1+1等于几？"):
            event_type = event.get("event_type")
            data = event.get("data", {})
            
            if event_type == "text":
                content = data.get("content", "")
                print(f"   {content}", end="", flush=True)
            elif event_type == "hitl":
                print(f"\n   [HITL 请求: {data.get('action', {})}]")
                # 自动批准（演示用）
                await client.send_hitl_decision("approve")
            elif event_type == "done":
                print("\n   [完成]")
        
    except Exception as e:
        print(f"   错误: {e}")
    finally:
        await client.close()


async def demo_session_management():
    """演示会话管理。"""
    print("\n" + "=" * 50)
    print("会话管理示例")
    print("=" * 50)
    
    client = DataAgentClient()
    
    # 列出会话
    print("\n1. 列出会话:")
    try:
        sessions = await client.list_sessions()
        print(f"   共 {sessions['total']} 个会话")
        for s in sessions["sessions"][:3]:
            print(f"   - {s['session_id'][:8]}... ({s['assistant_id']})")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 列出助手
    print("\n2. 列出助手:")
    try:
        assistants = await client.list_assistants()
        print(f"   共 {assistants['total']} 个助手")
        for a in assistants["assistants"]:
            print(f"   - {a['assistant_id']}: {a['name']}")
    except Exception as e:
        print(f"   错误: {e}")


async def demo_user_profile_management():
    """演示用户档案管理。"""
    print("\n" + "=" * 50)
    print("用户档案管理示例")
    print("=" * 50)
    
    client = DataAgentClient()
    
    # 创建用户档案
    print("\n1. 创建用户档案:")
    try:
        profile = await client.create_user_profile({
            "user_id": "demo-user-001",
            "username": "demo",
            "display_name": "演示用户",
            "department": "技术部",
            "role": "开发工程师",
        })
        print(f"   创建成功: {profile['user_id']} - {profile['display_name']}")
    except Exception as e:
        print(f"   错误 (可能已存在): {e}")
    
    # 列出用户档案
    print("\n2. 列出用户档案:")
    try:
        profiles = await client.list_user_profiles()
        print(f"   共 {profiles['total']} 个用户档案")
        for p in profiles["profiles"][:3]:
            print(f"   - {p['user_id']}: {p.get('display_name', 'N/A')}")
    except Exception as e:
        print(f"   错误: {e}")


async def demo_mcp_management():
    """演示 MCP 服务器管理。"""
    print("\n" + "=" * 50)
    print("MCP 服务器管理示例")
    print("=" * 50)
    
    client = DataAgentClient()
    
    # 列出 MCP 服务器
    print("\n1. 列出 MCP 服务器:")
    try:
        servers = await client.list_mcp_servers()
        print(f"   共 {len(servers.get('servers', []))} 个 MCP 服务器")
        for s in servers.get("servers", []):
            status = "✓" if s.get("connected") else "✗"
            print(f"   - [{status}] {s['name']}: {s.get('tools_count', 0)} 个工具")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 添加 MCP 服务器示例（注释掉以避免实际添加）
    print("\n2. 添加 MCP 服务器 (示例代码):")
    print("   # 命令行方式:")
    print("   # await client.add_mcp_server({")
    print('   #     "name": "aws-docs",')
    print('   #     "command": "uvx",')
    print('   #     "args": ["awslabs.aws-documentation-mcp-server@latest"],')
    print("   # })")
    print("   # HTTP/SSE 方式:")
    print("   # await client.add_mcp_server({")
    print('   #     "name": "remote-mcp",')
    print('   #     "url": "http://localhost:3000/mcp",')
    print('   #     "transport": "sse",')
    print("   # })")


async def demo_rules_management():
    """演示规则管理。"""
    print("\n" + "=" * 50)
    print("规则管理示例")
    print("=" * 50)
    
    client = DataAgentClient()
    
    # 列出规则
    print("\n1. 列出规则:")
    try:
        rules = await client.list_rules()
        print(f"   共 {rules['total']} 条规则")
        for r in rules["rules"][:5]:
            status = "✓" if r.get("enabled") else "✗"
            print(f"   - [{status}] {r['name']} ({r['scope']})")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 验证规则内容
    print("\n2. 验证规则内容:")
    try:
        result = await client.validate_rule("这是一条测试规则内容")
        valid = "✓ 有效" if result["valid"] else "✗ 无效"
        print(f"   {valid}")
        if result.get("warnings"):
            print(f"   警告: {result['warnings']}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 检测规则冲突
    print("\n3. 检测规则冲突:")
    try:
        conflicts = await client.list_rule_conflicts()
        print(f"   共 {conflicts['total_conflicts']} 个冲突")
        for c in conflicts.get("conflicts", [])[:3]:
            print(f"   - {c['rule1_name']} vs {c['rule2_name']}: {c['conflict_type']}")
    except Exception as e:
        print(f"   错误: {e}")


async def main():
    """运行所有示例。"""
    print("DataAgent Python 客户端示例")
    print("请确保 DataAgent Server 正在运行 (http://localhost:8000)")
    
    await demo_rest_api()
    await demo_sse_stream()
    await demo_websocket()
    await demo_session_management()
    await demo_user_profile_management()
    await demo_mcp_management()
    await demo_rules_management()
    
    print("\n" + "=" * 50)
    print("示例完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
