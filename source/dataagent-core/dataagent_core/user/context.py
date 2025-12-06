"""User context manager for LLM integration."""

from __future__ import annotations

from typing import Any

from dataagent_core.user.profile import UserProfile
from dataagent_core.user.store import UserProfileStore


class UserContextManager:
    """用户上下文管理器。
    
    负责获取用户档案并构建 System Prompt 中的用户信息部分。
    """
    
    def __init__(self, profile_store: UserProfileStore) -> None:
        """Initialize the context manager.
        
        Args:
            profile_store: User profile storage backend.
        """
        self._store = profile_store
    
    async def get_user_context(self, user_id: str) -> dict[str, Any]:
        """获取用户上下文，用于注入到 System Prompt。
        
        Args:
            user_id: 用户唯一标识。
            
        Returns:
            用户上下文字典。如果用户不存在，返回匿名用户上下文。
        """
        profile = await self._store.get_profile(user_id)
        
        if profile is None:
            return {
                "user_id": user_id,
                "is_anonymous": True,
            }
        
        # Use to_context() which excludes sensitive fields by default
        context = profile.to_context(include_sensitive=False)
        context["is_anonymous"] = False
        return context
    
    async def get_user_profile(self, user_id: str) -> UserProfile | None:
        """获取用户档案。
        
        Args:
            user_id: 用户唯一标识。
            
        Returns:
            用户档案，如果不存在则返回 None。
        """
        return await self._store.get_profile(user_id)
    
    async def save_user_profile(self, profile: UserProfile) -> None:
        """保存用户档案。
        
        Args:
            profile: 用户档案。
        """
        await self._store.save_profile(profile)
    
    def build_system_prompt_section(self, context: dict[str, Any]) -> str:
        """构建 System Prompt 中的用户信息部分。
        
        Args:
            context: 用户上下文字典（来自 get_user_context）。
            
        Returns:
            System Prompt 中的用户信息部分。
        """
        if context.get("is_anonymous", True):
            return self._build_anonymous_section(context)
        
        return self._build_user_section(context)
    
    def _build_anonymous_section(self, context: dict[str, Any]) -> str:
        """构建匿名用户的 System Prompt 部分。"""
        user_id = context.get("user_id", "unknown")
        return f"""## 当前用户信息
用户ID: {user_id}
注意: 该用户的详细信息尚未配置。如果用户询问"我是谁"，请告知用户其身份信息尚未设置。"""
    
    def _build_user_section(self, context: dict[str, Any]) -> str:
        """构建已知用户的 System Prompt 部分。"""
        user_id = context.get("user_id", "unknown")
        username = context.get("username", "未知")
        display_name = context.get("display_name", "未知")
        department = context.get("department") or "未知"
        role = context.get("role") or "未知"
        
        # Build custom fields section
        custom_section = ""
        custom_fields = context.get("custom_fields", {})
        if custom_fields:
            custom_items = [f"- {k}: {v}" for k, v in custom_fields.items()]
            custom_section = "\n其他信息:\n" + "\n".join(custom_items)
        
        return f"""## 当前用户信息
你正在与以下用户对话：
- 用户ID: {user_id}
- 用户名: {username}
- 姓名: {display_name}
- 部门: {department}
- 角色: {role}{custom_section}

重要提示：
- 当用户说"我"、"我的"、"本人"时，指的是上述用户（{display_name}）
- 在查询数据时，请使用用户的真实姓名（{display_name}）或用户名（{username}）
- 回答用户身份相关问题时，使用上述信息
- 如果用户问"我是谁"，请回复用户的姓名、部门等信息"""


def build_user_context_prompt(
    user_context: dict[str, Any] | None,
) -> str:
    """便捷函数：构建用户上下文的 System Prompt 部分。
    
    Args:
        user_context: 用户上下文字典，可以是：
            - None: 返回空字符串
            - 包含 user_id 的字典: 构建用户信息部分
            
    Returns:
        System Prompt 中的用户信息部分。
    """
    if not user_context:
        return ""
    
    # Check if anonymous
    if user_context.get("is_anonymous", True):
        user_id = user_context.get("user_id", "unknown")
        return f"""## 当前用户信息
用户ID: {user_id}
注意: 该用户的详细信息尚未配置。"""
    
    # Build full user section
    user_id = user_context.get("user_id", "unknown")
    username = user_context.get("username", "未知")
    display_name = user_context.get("display_name", "未知")
    department = user_context.get("department") or "未知"
    role = user_context.get("role") or "未知"
    
    return f"""## 当前用户信息
你正在与以下用户对话：
- 用户ID: {user_id}
- 用户名: {username}
- 姓名: {display_name}
- 部门: {department}
- 角色: {role}

重要提示：
- 当用户说"我"、"我的"、"本人"时，指的是上述用户（{display_name}）
- 在查询数据时，请使用用户的真实姓名（{display_name}）或用户名（{username}）
- 回答用户身份相关问题时，使用上述信息"""
