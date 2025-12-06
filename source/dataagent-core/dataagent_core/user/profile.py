"""User profile data model."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class UserProfile:
    """用户档案信息。
    
    Attributes:
        user_id: 用户唯一标识
        username: 登录用户名
        display_name: 显示名称（中文名）
        email: 邮箱（敏感信息，不会注入到 prompt）
        department: 部门
        role: 角色
        custom_fields: 自定义字段
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    user_id: str
    username: str
    display_name: str
    email: str | None = None
    department: str | None = None
    role: str | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    def __post_init__(self):
        """Set default timestamps."""
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
        if self.custom_fields is None:
            self.custom_fields = {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation of the profile.
        """
        result = asdict(self)
        # Convert datetime to ISO format strings
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        """Create from dictionary.
        
        Args:
            data: Dictionary with profile fields.
            
        Returns:
            UserProfile instance.
        """
        # Parse datetime strings
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            display_name=data["display_name"],
            email=data.get("email"),
            department=data.get("department"),
            role=data.get("role"),
            custom_fields=data.get("custom_fields", {}),
            created_at=created_at,
            updated_at=updated_at,
        )
    
    def to_context(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert to context dictionary for LLM.
        
        This method returns a sanitized version suitable for injection
        into system prompts. Sensitive fields like email are excluded
        by default.
        
        Args:
            include_sensitive: Whether to include sensitive fields.
            
        Returns:
            Context dictionary for LLM.
        """
        context = {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "department": self.department,
            "role": self.role,
        }
        
        if include_sensitive and self.email:
            context["email"] = self.email
        
        # Add custom fields
        if self.custom_fields:
            context["custom_fields"] = self.custom_fields
        
        return context
    
    def update(self, **kwargs) -> None:
        """Update profile fields.
        
        Args:
            **kwargs: Fields to update.
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ("user_id", "created_at"):
                setattr(self, key, value)
        self.updated_at = datetime.now()
