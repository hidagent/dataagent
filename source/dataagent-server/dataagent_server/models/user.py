"""User-related Pydantic models."""

from typing import Any

from pydantic import BaseModel, Field


class UserContextRequest(BaseModel):
    """用户上下文请求模型。
    
    用于在 API 请求中传递用户上下文信息。
    """
    
    user_id: str = Field(..., description="用户唯一标识")
    username: str | None = Field(None, description="登录用户名")
    display_name: str | None = Field(None, description="显示名称（中文名）")
    email: str | None = Field(None, description="邮箱")
    department: str | None = Field(None, description="部门")
    role: str | None = Field(None, description="角色")
    custom_fields: dict[str, Any] | None = Field(None, description="自定义字段")
    
    def to_context_dict(self) -> dict[str, Any]:
        """转换为上下文字典，用于注入到 System Prompt。
        
        Returns:
            上下文字典，不包含敏感信息（如 email）。
        """
        context = {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "department": self.department,
            "role": self.role,
            "is_anonymous": self.display_name is None,
        }
        
        if self.custom_fields:
            context["custom_fields"] = self.custom_fields
        
        return context


class UserProfileRequest(BaseModel):
    """用户档案请求模型。
    
    用于创建或更新用户档案。
    """
    
    user_id: str = Field(..., description="用户唯一标识")
    username: str = Field(..., description="登录用户名")
    display_name: str = Field(..., description="显示名称（中文名）")
    email: str | None = Field(None, description="邮箱")
    department: str | None = Field(None, description="部门")
    role: str | None = Field(None, description="角色")
    custom_fields: dict[str, Any] | None = Field(None, description="自定义字段")


class UserProfileResponse(BaseModel):
    """用户档案响应模型。"""
    
    user_id: str = Field(..., description="用户唯一标识")
    username: str = Field(..., description="登录用户名")
    display_name: str = Field(..., description="显示名称（中文名）")
    email: str | None = Field(None, description="邮箱")
    department: str | None = Field(None, description="部门")
    role: str | None = Field(None, description="角色")
    custom_fields: dict[str, Any] | None = Field(None, description="自定义字段")
    created_at: str | None = Field(None, description="创建时间")
    updated_at: str | None = Field(None, description="更新时间")


class UserProfileListResponse(BaseModel):
    """用户档案列表响应模型。"""
    
    profiles: list[UserProfileResponse] = Field(default_factory=list, description="用户档案列表")
    total: int = Field(0, description="总数")
