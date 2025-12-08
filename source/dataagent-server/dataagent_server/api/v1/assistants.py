"""Assistant management REST API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from dataagent_server.auth import get_api_key
from dataagent_server.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistants", tags=["Assistants"])


class AssistantConfig(BaseModel):
    """Assistant configuration model."""
    
    assistant_id: str = Field(..., description="Unique assistant identifier")
    name: str = Field(..., description="Display name")
    description: str | None = Field(None, description="Assistant description")
    model: str | None = Field(None, description="LLM model to use")
    system_prompt: str | None = Field(None, description="Custom system prompt")
    tools: list[str] | None = Field(None, description="Enabled tool names")
    auto_approve: bool = Field(False, description="Auto-approve HITL actions")
    metadata: dict[str, Any] | None = Field(None, description="Custom metadata")


class AssistantCreateRequest(BaseModel):
    """Request model for creating an assistant."""
    
    name: str = Field(..., description="Display name")
    description: str | None = Field(None, description="Assistant description")
    model: str | None = Field(None, description="LLM model to use")
    system_prompt: str | None = Field(None, description="Custom system prompt")
    tools: list[str] | None = Field(None, description="Enabled tool names")
    auto_approve: bool = Field(False, description="Auto-approve HITL actions")
    metadata: dict[str, Any] | None = Field(None, description="Custom metadata")


class AssistantListResponse(BaseModel):
    """Response model for listing assistants."""
    
    assistants: list[AssistantConfig] = Field(default_factory=list)
    total: int = Field(0)


# In-memory assistant store (for demo purposes)
# In production, this should be persisted to database
_assistants: dict[str, AssistantConfig] = {
    "default": AssistantConfig(
        assistant_id="default",
        name="Default Assistant",
        description="Default DataAgent assistant",
        auto_approve=False,
    ),
}


@router.get("", response_model=AssistantListResponse)
async def list_assistants(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    _api_key: str | None = Depends(get_api_key),
) -> AssistantListResponse:
    """List all available assistants.
    
    Returns:
        List of assistant configurations.
    """
    assistants = list(_assistants.values())
    return AssistantListResponse(assistants=assistants, total=len(assistants))


@router.get("/{assistant_id}", response_model=AssistantConfig)
async def get_assistant(
    assistant_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    _api_key: str | None = Depends(get_api_key),
) -> AssistantConfig:
    """Get assistant configuration by ID.
    
    Args:
        assistant_id: The assistant ID to retrieve.
        
    Returns:
        Assistant configuration.
        
    Raises:
        HTTPException: If assistant not found.
    """
    if assistant_id not in _assistants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assistant {assistant_id} not found",
        )
    return _assistants[assistant_id]


@router.post("", response_model=AssistantConfig, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    config: AssistantCreateRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    _api_key: str | None = Depends(get_api_key),
) -> AssistantConfig:
    """Create a new assistant.
    
    Args:
        config: Assistant configuration.
        
    Returns:
        Created assistant configuration.
    """
    import uuid
    
    assistant_id = str(uuid.uuid4())[:8]
    
    assistant = AssistantConfig(
        assistant_id=assistant_id,
        name=config.name,
        description=config.description,
        model=config.model,
        system_prompt=config.system_prompt,
        tools=config.tools,
        auto_approve=config.auto_approve,
        metadata=config.metadata,
    )
    
    _assistants[assistant_id] = assistant
    logger.info(f"Created assistant: {assistant_id}")
    
    return assistant


@router.put("/{assistant_id}", response_model=AssistantConfig)
async def update_assistant(
    assistant_id: str,
    config: AssistantCreateRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    _api_key: str | None = Depends(get_api_key),
) -> AssistantConfig:
    """Update an existing assistant.
    
    Args:
        assistant_id: The assistant ID to update.
        config: New assistant configuration.
        
    Returns:
        Updated assistant configuration.
        
    Raises:
        HTTPException: If assistant not found.
    """
    if assistant_id not in _assistants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assistant {assistant_id} not found",
        )
    
    assistant = AssistantConfig(
        assistant_id=assistant_id,
        name=config.name,
        description=config.description,
        model=config.model,
        system_prompt=config.system_prompt,
        tools=config.tools,
        auto_approve=config.auto_approve,
        metadata=config.metadata,
    )
    
    _assistants[assistant_id] = assistant
    logger.info(f"Updated assistant: {assistant_id}")
    
    return assistant


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    _api_key: str | None = Depends(get_api_key),
) -> None:
    """Delete an assistant.
    
    Args:
        assistant_id: The assistant ID to delete.
        
    Raises:
        HTTPException: If assistant not found or is the default assistant.
    """
    if assistant_id == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default assistant",
        )
    
    if assistant_id not in _assistants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assistant {assistant_id} not found",
        )
    
    del _assistants[assistant_id]
    logger.info(f"Deleted assistant: {assistant_id}")
