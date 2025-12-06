"""User profile store interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dataagent_core.user.profile import UserProfile


class UserProfileStore(ABC):
    """用户档案存储接口。
    
    Abstract base class for user profile storage implementations.
    """
    
    @abstractmethod
    async def get_profile(self, user_id: str) -> UserProfile | None:
        """获取用户档案。
        
        Args:
            user_id: 用户唯一标识。
            
        Returns:
            用户档案，如果不存在则返回 None。
        """
        pass
    
    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> None:
        """保存用户档案。
        
        如果用户已存在则更新，否则创建新档案。
        
        Args:
            profile: 用户档案。
        """
        pass
    
    @abstractmethod
    async def delete_profile(self, user_id: str) -> bool:
        """删除用户档案。
        
        Args:
            user_id: 用户唯一标识。
            
        Returns:
            是否删除成功。
        """
        pass
    
    @abstractmethod
    async def update_profile(
        self, user_id: str, updates: dict[str, Any]
    ) -> UserProfile | None:
        """更新用户档案。
        
        Args:
            user_id: 用户唯一标识。
            updates: 要更新的字段。
            
        Returns:
            更新后的用户档案，如果用户不存在则返回 None。
        """
        pass
    
    @abstractmethod
    async def list_profiles(self) -> list[UserProfile]:
        """列出所有用户档案。
        
        Returns:
            用户档案列表。
        """
        pass


class MemoryUserProfileStore(UserProfileStore):
    """内存用户档案存储。
    
    用于测试和开发环境。
    """
    
    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
    
    async def get_profile(self, user_id: str) -> UserProfile | None:
        """获取用户档案。"""
        return self._profiles.get(user_id)
    
    async def save_profile(self, profile: UserProfile) -> None:
        """保存用户档案。"""
        self._profiles[profile.user_id] = profile
    
    async def delete_profile(self, user_id: str) -> bool:
        """删除用户档案。"""
        if user_id in self._profiles:
            del self._profiles[user_id]
            return True
        return False
    
    async def update_profile(
        self, user_id: str, updates: dict[str, Any]
    ) -> UserProfile | None:
        """更新用户档案。"""
        profile = self._profiles.get(user_id)
        if profile is None:
            return None
        
        profile.update(**updates)
        return profile
    
    async def list_profiles(self) -> list[UserProfile]:
        """列出所有用户档案。"""
        return list(self._profiles.values())
    
    def clear(self) -> None:
        """清空所有档案（仅用于测试）。"""
        self._profiles.clear()
