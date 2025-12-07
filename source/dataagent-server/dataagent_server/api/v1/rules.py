"""Rules REST API endpoints.

**Feature: agent-rules**
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.2, 8.5, 13.6, 14.3**
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from dataagent_server.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/{user_id}/rules", tags=["Rules"])


# ============================================================================
# Pydantic Models
# ============================================================================


class RuleResponse(BaseModel):
    """Response model for a single rule."""
    name: str
    description: str
    content: str
    scope: str
    inclusion: str
    file_match_pattern: str | None = None
    priority: int = 50
    override: bool = False
    enabled: bool = True
    source_path: str | None = None


class RuleListResponse(BaseModel):
    """Response model for listing rules."""
    rules: list[RuleResponse]
    total: int


class RuleCreateRequest(BaseModel):
    """Request model for creating a rule."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    scope: str = Field(default="user")
    inclusion: str = Field(default="always")
    file_match_pattern: str | None = None
    priority: int = Field(default=50, ge=1, le=100)
    override: bool = False
    enabled: bool = True


class RuleUpdateRequest(BaseModel):
    """Request model for updating a rule."""
    description: str | None = None
    content: str | None = None
    inclusion: str | None = None
    file_match_pattern: str | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
    override: bool | None = None
    enabled: bool | None = None


class RuleValidateRequest(BaseModel):
    """Request model for validating rule content."""
    content: str


class RuleValidateResponse(BaseModel):
    """Response model for rule validation."""
    valid: bool
    errors: list[str]
    warnings: list[str]


class RuleConflictResponse(BaseModel):
    """Response model for a rule conflict."""
    rule1_name: str
    rule1_scope: str
    rule2_name: str
    rule2_scope: str
    conflict_type: str
    resolution: str
    details: str = ""


class RuleConflictsResponse(BaseModel):
    """Response model for listing conflicts."""
    conflicts: list[RuleConflictResponse]
    warnings: list[str]
    total_conflicts: int


class RuleReloadResponse(BaseModel):
    """Response model for rule reload."""
    success: bool
    rules_count: int
    message: str


class RuleDeleteResponse(BaseModel):
    """Response model for rule deletion."""
    success: bool
    message: str


# ============================================================================
# Helper Functions
# ============================================================================


def _check_user_access(user_id: str, current_user_id: str) -> None:
    """Check if current user can access the target user's resources."""
    if user_id != current_user_id and current_user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other user's rules",
        )


def _get_rule_store(request: Request, user_id: str):
    """Get or create a rule store for the user."""
    from pathlib import Path
    from dataagent_core.rules import FileRuleStore
    from dataagent_core.config import Settings
    
    settings = Settings()
    
    global_rules_dir = settings.user_deepagents_dir / "rules"
    user_rules_dir = settings.user_deepagents_dir / "users" / user_id / "rules"
    project_rules_dir = None
    if settings.project_root:
        project_rules_dir = settings.project_root / ".dataagent" / "rules"
    
    return FileRuleStore(
        global_dir=global_rules_dir,
        user_dir=user_rules_dir,
        project_dir=project_rules_dir,
    )


def _rule_to_response(rule) -> RuleResponse:
    """Convert a Rule to RuleResponse."""
    return RuleResponse(
        name=rule.name,
        description=rule.description,
        content=rule.content,
        scope=rule.scope.value,
        inclusion=rule.inclusion.value,
        file_match_pattern=rule.file_match_pattern,
        priority=rule.priority,
        override=rule.override,
        enabled=rule.enabled,
        source_path=rule.source_path,
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("", response_model=RuleListResponse)
async def list_rules(
    user_id: str,
    request: Request,
    scope: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleListResponse:
    """List all rules for a user.
    
    Optionally filter by scope (global, user, project).
    """
    _check_user_access(user_id, current_user_id)
    
    store = _get_rule_store(request, user_id)
    
    if scope:
        from dataagent_core.rules import RuleScope
        try:
            rule_scope = RuleScope(scope)
            rules = store.list_rules(rule_scope)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}. Valid values: global, user, project, session",
            )
    else:
        rules = store.list_rules()
    
    return RuleListResponse(
        rules=[_rule_to_response(r) for r in rules],
        total=len(rules),
    )


@router.get("/{rule_name}", response_model=RuleResponse)
async def get_rule(
    user_id: str,
    rule_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleResponse:
    """Get a specific rule by name."""
    _check_user_access(user_id, current_user_id)
    
    store = _get_rule_store(request, user_id)
    rule = store.get_rule(rule_name)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_name}' not found",
        )
    
    return _rule_to_response(rule)


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    user_id: str,
    request_body: RuleCreateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleResponse:
    """Create a new rule."""
    _check_user_access(user_id, current_user_id)
    
    from dataagent_core.rules import Rule, RuleScope, RuleInclusion
    
    store = _get_rule_store(request, user_id)
    
    # Check if rule already exists
    existing = store.get_rule(request_body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule '{request_body.name}' already exists",
        )
    
    # Parse scope and inclusion
    try:
        rule_scope = RuleScope(request_body.scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request_body.scope}",
        )
    
    try:
        rule_inclusion = RuleInclusion(request_body.inclusion)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid inclusion: {request_body.inclusion}",
        )
    
    rule = Rule(
        name=request_body.name,
        description=request_body.description,
        content=request_body.content,
        scope=rule_scope,
        inclusion=rule_inclusion,
        file_match_pattern=request_body.file_match_pattern,
        priority=request_body.priority,
        override=request_body.override,
        enabled=request_body.enabled,
    )
    
    store.save_rule(rule)
    
    return _rule_to_response(rule)


@router.put("/{rule_name}", response_model=RuleResponse)
async def update_rule(
    user_id: str,
    rule_name: str,
    request_body: RuleUpdateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleResponse:
    """Update an existing rule."""
    _check_user_access(user_id, current_user_id)
    
    from dataagent_core.rules import RuleInclusion
    
    store = _get_rule_store(request, user_id)
    rule = store.get_rule(rule_name)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_name}' not found",
        )
    
    # Update fields
    if request_body.description is not None:
        rule.description = request_body.description
    if request_body.content is not None:
        rule.content = request_body.content
    if request_body.inclusion is not None:
        try:
            rule.inclusion = RuleInclusion(request_body.inclusion)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid inclusion: {request_body.inclusion}",
            )
    if request_body.file_match_pattern is not None:
        rule.file_match_pattern = request_body.file_match_pattern
    if request_body.priority is not None:
        rule.priority = request_body.priority
    if request_body.override is not None:
        rule.override = request_body.override
    if request_body.enabled is not None:
        rule.enabled = request_body.enabled
    
    store.save_rule(rule)
    
    return _rule_to_response(rule)


@router.delete("/{rule_name}", response_model=RuleDeleteResponse)
async def delete_rule(
    user_id: str,
    rule_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleDeleteResponse:
    """Delete a rule."""
    _check_user_access(user_id, current_user_id)
    
    store = _get_rule_store(request, user_id)
    rule = store.get_rule(rule_name)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_name}' not found",
        )
    
    success = store.delete_rule(rule_name, rule.scope)
    
    if success:
        return RuleDeleteResponse(
            success=True,
            message=f"Rule '{rule_name}' deleted successfully",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rule '{rule_name}'",
        )


@router.post("/validate", response_model=RuleValidateResponse)
async def validate_rule(
    user_id: str,
    request_body: RuleValidateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleValidateResponse:
    """Validate rule content without saving."""
    _check_user_access(user_id, current_user_id)
    
    from dataagent_core.rules import RuleParser
    
    parser = RuleParser()
    is_valid, errors, warnings = parser.validate_content(request_body.content)
    
    return RuleValidateResponse(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
    )


@router.get("/conflicts/list", response_model=RuleConflictsResponse)
async def list_conflicts(
    user_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleConflictsResponse:
    """List all rule conflicts."""
    _check_user_access(user_id, current_user_id)
    
    from dataagent_core.rules import ConflictDetector
    
    store = _get_rule_store(request, user_id)
    rules = store.list_rules()
    
    detector = ConflictDetector()
    report = detector.detect_conflicts(rules)
    
    conflicts = [
        RuleConflictResponse(
            rule1_name=c.rule1_name,
            rule1_scope=c.rule1_scope.value,
            rule2_name=c.rule2_name,
            rule2_scope=c.rule2_scope.value,
            conflict_type=c.conflict_type,
            resolution=c.resolution,
            details=c.details,
        )
        for c in report.conflicts
    ]
    
    return RuleConflictsResponse(
        conflicts=conflicts,
        warnings=report.warnings,
        total_conflicts=len(conflicts),
    )


@router.post("/reload", response_model=RuleReloadResponse)
async def reload_rules(
    user_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> RuleReloadResponse:
    """Reload all rules from disk."""
    _check_user_access(user_id, current_user_id)
    
    store = _get_rule_store(request, user_id)
    store.reload()
    rules = store.list_rules()
    
    return RuleReloadResponse(
        success=True,
        rules_count=len(rules),
        message=f"Reloaded {len(rules)} rules successfully",
    )
