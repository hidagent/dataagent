"""Skills management endpoints - Claude Code Desktop compatible.

Provides full Skills management compatible with Anthropic's Claude Code Desktop:
- Upload skills via ZIP file
- Enable/disable skills
- Built-in skills support
- User skills and project skills
- SKILL.md format with YAML frontmatter

Directory structure:
  User skills:    {workspace}/skills/
  Project skills: {workspace}/.claude/skills/ (or .dataagent/skills/)
  Built-in skills: {app_data}/builtin-skills/

Each skill is a directory containing:
  ├── SKILL.md        # Required: YAML frontmatter + instructions
  ├── script.py       # Optional: supporting scripts
  ├── config.json     # Optional: configuration
  └── templates/      # Optional: template files
"""

import io
import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dataagent_server.auth import get_api_key
from dataagent_server.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


# ============================================================================
# Constants
# ============================================================================

# Valid skill name pattern (alphanumeric, hyphens, underscores)
SKILL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Maximum ZIP file size (50MB)
MAX_ZIP_SIZE = 50 * 1024 * 1024

# Skill status file name
SKILL_STATUS_FILE = ".skill_status.json"


# ============================================================================
# Pydantic Models
# ============================================================================

class SkillCreate(BaseModel):
    """Request model for creating a skill."""
    name: str = Field(..., min_length=1, max_length=128, description="Skill name (directory name)")
    description: str = Field(..., description="Brief description of what this skill does")
    content: str = Field(..., description="Full SKILL.md content (markdown instructions)")
    category: Optional[str] = Field(None, description="Skill category (e.g., 'document', 'code', 'data')")
    tags: Optional[list[str]] = Field(None, description="Skill tags for filtering")


class SkillUpdate(BaseModel):
    """Request model for updating a skill."""
    description: Optional[str] = Field(None, description="Brief description")
    content: Optional[str] = Field(None, description="Full SKILL.md content")
    category: Optional[str] = Field(None, description="Skill category")
    tags: Optional[list[str]] = Field(None, description="Skill tags")


class SkillStatusUpdate(BaseModel):
    """Request model for enabling/disabling a skill."""
    enabled: bool = Field(..., description="Whether the skill is enabled")


class SkillInfo(BaseModel):
    """Response model for skill information."""
    name: str = Field(..., description="Skill name (directory name)")
    description: str = Field(..., description="Skill description from YAML frontmatter")
    path: str = Field(..., description="Path to SKILL.md file")
    source: str = Field(..., description="Skill source: 'user', 'project', or 'builtin'")
    enabled: bool = Field(True, description="Whether the skill is enabled")
    category: Optional[str] = Field(None, description="Skill category")
    tags: list[str] = Field(default_factory=list, description="Skill tags")
    content: Optional[str] = Field(None, description="Full SKILL.md content (only in detail view)")
    supporting_files: list[str] = Field(default_factory=list, description="List of supporting files")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class SkillListResponse(BaseModel):
    """Response model for listing skills."""
    skills: list[SkillInfo] = Field(default_factory=list, description="List of skills")
    total: int = Field(0, description="Total number of skills")
    user_skills_dir: str = Field(..., description="User skills directory path")
    project_skills_dir: Optional[str] = Field(None, description="Project skills directory path")
    builtin_skills_count: int = Field(0, description="Number of built-in skills")


class SkillUploadResponse(BaseModel):
    """Response model for skill upload."""
    skill: SkillInfo = Field(..., description="Uploaded skill information")
    message: str = Field(..., description="Upload result message")
    files_extracted: int = Field(0, description="Number of files extracted from ZIP")


class SkillExportResponse(BaseModel):
    """Response model for skill export."""
    name: str = Field(..., description="Skill name")
    download_url: str = Field(..., description="URL to download the skill ZIP")


# ============================================================================
# Helper Functions
# ============================================================================

def _validate_skill_name(name: str) -> tuple[bool, str]:
    """Validate skill name to prevent path traversal attacks."""
    if not name or not name.strip():
        return False, "Skill name cannot be empty"
    if ".." in name:
        return False, "Skill name cannot contain '..'"
    if "/" in name or "\\" in name:
        return False, "Skill name cannot contain path separators"
    if not SKILL_NAME_PATTERN.match(name):
        return False, "Skill name can only contain letters, numbers, hyphens, and underscores"
    if len(name) > 128:
        return False, "Skill name cannot exceed 128 characters"
    return True, ""


async def _get_user_skills_dir(request: Request, user_id: str) -> Path:
    """Get the user skills directory for a user's workspace."""
    from dataagent_server.api.v1.workspaces import get_user_default_workspace_path
    
    workspace_path = await get_user_default_workspace_path(user_id)
    if not workspace_path:
        from dataagent_server.config import get_settings
        settings = get_settings()
        workspace_path = str(Path(settings.workspace_base_path) / user_id / "workspace")
    
    skills_dir = Path(workspace_path) / "skills"
    return skills_dir


async def _get_project_skills_dir(request: Request, user_id: str) -> Path | None:
    """Get the project skills directory (.claude/skills or .dataagent/skills)."""
    from dataagent_server.api.v1.workspaces import get_user_default_workspace_path
    
    workspace_path = await get_user_default_workspace_path(user_id)
    if not workspace_path:
        return None
    
    workspace = Path(workspace_path)
    
    # Check for .claude/skills first (Claude Code Desktop compatible)
    claude_skills = workspace / ".claude" / "skills"
    if claude_skills.exists():
        return claude_skills
    
    # Check for .dataagent/skills
    dataagent_skills = workspace / ".dataagent" / "skills"
    if dataagent_skills.exists():
        return dataagent_skills
    
    return None


def _get_builtin_skills_dir() -> Path:
    """Get the built-in skills directory."""
    from dataagent_server.config import get_settings
    settings = get_settings()
    
    # Built-in skills are stored in the app data directory
    builtin_dir = Path(settings.workspace_base_path).parent / "builtin-skills"
    return builtin_dir


def _parse_skill_metadata(skill_md_path: Path) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a SKILL.md file.
    
    Returns:
        Dictionary with name, description, category, tags, etc. or None if parsing fails.
    """
    try:
        content = skill_md_path.read_text(encoding="utf-8")
        
        # Match YAML frontmatter between --- delimiters
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)
        
        if not match:
            return None
        
        frontmatter = match.group(1)
        metadata: dict[str, Any] = {}
        
        for line in frontmatter.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Handle array values (tags: [tag1, tag2])
            array_match = re.match(r"^(\w+):\s*\[(.*)\]$", line)
            if array_match:
                key, value = array_match.groups()
                metadata[key] = [v.strip().strip('"\'') for v in value.split(",") if v.strip()]
                continue
            
            # Handle simple key-value pairs
            kv_match = re.match(r"^(\w+):\s*(.+)$", line)
            if kv_match:
                key, value = kv_match.groups()
                metadata[key] = value.strip().strip('"\'')
        
        if "name" not in metadata or "description" not in metadata:
            return None
        
        return metadata
    except Exception as e:
        logger.warning(f"Failed to parse SKILL.md at {skill_md_path}: {e}")
        return None


def _generate_skill_md(
    name: str,
    description: str,
    content: str,
    category: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Generate SKILL.md content with YAML frontmatter."""
    # Build frontmatter
    frontmatter_lines = [
        f"name: {name}",
        f"description: {description}",
    ]
    if category:
        frontmatter_lines.append(f"category: {category}")
    if tags:
        frontmatter_lines.append(f"tags: [{', '.join(tags)}]")
    
    frontmatter = "\n".join(frontmatter_lines)
    
    # Check if content already has frontmatter
    if content.strip().startswith("---"):
        # Extract body after existing frontmatter
        body_pattern = r"^---\s*\n.*?\n---\s*\n(.*)$"
        match = re.match(body_pattern, content, re.DOTALL)
        if match:
            body = match.group(1)
            return f"---\n{frontmatter}\n---\n\n{body}"
    
    # No frontmatter, add it
    return f"---\n{frontmatter}\n---\n\n{content}"


def _get_skill_status(skill_dir: Path) -> dict[str, Any]:
    """Get skill status from .skill_status.json file."""
    status_file = skill_dir / SKILL_STATUS_FILE
    if status_file.exists():
        try:
            return json.loads(status_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": True}


def _set_skill_status(skill_dir: Path, status: dict[str, Any]) -> None:
    """Save skill status to .skill_status.json file."""
    status_file = skill_dir / SKILL_STATUS_FILE
    status_file.write_text(json.dumps(status, indent=2), encoding="utf-8")


def _load_skill_info(
    skill_dir: Path,
    source: str,
    include_content: bool = False,
) -> SkillInfo | None:
    """Load skill information from a skill directory."""
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        return None
    
    metadata = _parse_skill_metadata(skill_md_path)
    if not metadata:
        return None
    
    # Get status
    status = _get_skill_status(skill_dir)
    
    # Get supporting files
    supporting_files = [
        f.name for f in skill_dir.iterdir()
        if f.is_file() and f.name not in ("SKILL.md", SKILL_STATUS_FILE)
    ]
    
    # Get timestamps
    stat = skill_md_path.stat()
    created_at = datetime.fromtimestamp(stat.st_ctime)
    updated_at = datetime.fromtimestamp(stat.st_mtime)
    
    # Read content if requested
    content = None
    if include_content:
        content = skill_md_path.read_text(encoding="utf-8")
    
    return SkillInfo(
        name=metadata["name"],
        description=metadata["description"],
        path=str(skill_md_path),
        source=source,
        enabled=status.get("enabled", True),
        category=metadata.get("category"),
        tags=metadata.get("tags", []),
        content=content,
        supporting_files=supporting_files,
        created_at=created_at,
        updated_at=updated_at,
    )


def _extract_zip_to_skill(
    zip_file: zipfile.ZipFile,
    target_dir: Path,
) -> tuple[int, str | None]:
    """Extract ZIP file to skill directory.
    
    Returns:
        Tuple of (files_extracted, error_message)
    """
    files_extracted = 0
    
    # Check for SKILL.md in the ZIP
    skill_md_found = False
    root_prefix = None
    
    for name in zip_file.namelist():
        # Skip directories
        if name.endswith("/"):
            continue
        
        # Check if SKILL.md exists (might be in root or in a subdirectory)
        if name.endswith("SKILL.md"):
            skill_md_found = True
            # Determine if there's a root directory prefix
            parts = name.split("/")
            if len(parts) > 1:
                root_prefix = parts[0] + "/"
            break
    
    if not skill_md_found:
        return 0, "ZIP file must contain a SKILL.md file"
    
    # Extract files
    for name in zip_file.namelist():
        # Skip directories
        if name.endswith("/"):
            continue
        
        # Remove root prefix if exists
        target_name = name
        if root_prefix and name.startswith(root_prefix):
            target_name = name[len(root_prefix):]
        
        if not target_name:
            continue
        
        # Security: prevent path traversal
        if ".." in target_name or target_name.startswith("/"):
            continue
        
        target_path = target_dir / target_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zip_file.open(name) as src, open(target_path, "wb") as dst:
            dst.write(src.read())
        
        files_extracted += 1
    
    return files_extracted, None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=SkillListResponse)
async def list_skills(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    source: Optional[str] = Query(None, description="Filter by source: 'user', 'project', 'builtin'"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    _api_key: Optional[str] = Depends(get_api_key),
) -> SkillListResponse:
    """List all skills for the current user.
    
    Returns skills from three sources:
    - User skills: {workspace}/skills/
    - Project skills: {workspace}/.claude/skills/ or .dataagent/skills/
    - Built-in skills: System-provided skills
    
    Args:
        source: Filter by skill source ('user', 'project', 'builtin')
        enabled: Filter by enabled status
        category: Filter by category
        
    Returns:
        List of skills with metadata.
    """
    user_skills_dir = await _get_user_skills_dir(request, user_id)
    project_skills_dir = await _get_project_skills_dir(request, user_id)
    builtin_skills_dir = _get_builtin_skills_dir()
    
    skills: list[SkillInfo] = []
    builtin_count = 0
    
    # Load user skills
    if (source is None or source == "user") and user_skills_dir.exists():
        for skill_dir in user_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_info = _load_skill_info(skill_dir, "user")
            if skill_info:
                if enabled is not None and skill_info.enabled != enabled:
                    continue
                if category and skill_info.category != category:
                    continue
                skills.append(skill_info)
    
    # Load project skills
    if (source is None or source == "project") and project_skills_dir and project_skills_dir.exists():
        for skill_dir in project_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_info = _load_skill_info(skill_dir, "project")
            if skill_info:
                if enabled is not None and skill_info.enabled != enabled:
                    continue
                if category and skill_info.category != category:
                    continue
                skills.append(skill_info)
    
    # Load built-in skills
    if (source is None or source == "builtin") and builtin_skills_dir.exists():
        for skill_dir in builtin_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_info = _load_skill_info(skill_dir, "builtin")
            if skill_info:
                builtin_count += 1
                if enabled is not None and skill_info.enabled != enabled:
                    continue
                if category and skill_info.category != category:
                    continue
                skills.append(skill_info)
    
    return SkillListResponse(
        skills=skills,
        total=len(skills),
        user_skills_dir=str(user_skills_dir),
        project_skills_dir=str(project_skills_dir) if project_skills_dir else None,
        builtin_skills_count=builtin_count,
    )


@router.post("", response_model=SkillInfo, status_code=status.HTTP_201_CREATED)
async def create_skill(
    request: Request,
    skill_data: SkillCreate,
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> SkillInfo:
    """Create a new skill with SKILL.md file.
    
    Creates a skill directory with a SKILL.md file containing
    YAML frontmatter (name, description, category, tags) and markdown instructions.
    
    Args:
        skill_data: Skill creation request.
        
    Returns:
        Created skill information.
    """
    is_valid, error_msg = _validate_skill_name(skill_data.name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {error_msg}",
        )
    
    skills_dir = await _get_user_skills_dir(request, user_id)
    skill_dir = skills_dir / skill_data.name
    
    if skill_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{skill_data.name}' already exists",
        )
    
    # Create skill directory
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate and write SKILL.md
    skill_md_content = _generate_skill_md(
        skill_data.name,
        skill_data.description,
        skill_data.content,
        skill_data.category,
        skill_data.tags,
    )
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(skill_md_content, encoding="utf-8")
    
    # Initialize status
    _set_skill_status(skill_dir, {"enabled": True})
    
    logger.info(f"Created skill '{skill_data.name}' for user {user_id}")
    
    return SkillInfo(
        name=skill_data.name,
        description=skill_data.description,
        path=str(skill_md_path),
        source="user",
        enabled=True,
        category=skill_data.category,
        tags=skill_data.tags or [],
        content=skill_md_content,
        supporting_files=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.post("/upload", response_model=SkillUploadResponse)
async def upload_skill(
    request: Request,
    file: UploadFile = File(..., description="ZIP file containing the skill"),
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> SkillUploadResponse:
    """Upload a skill from a ZIP file.
    
    The ZIP file should contain:
    - SKILL.md (required): Skill definition with YAML frontmatter
    - Supporting files (optional): scripts, configs, templates, etc.
    
    The ZIP can have files at root level or in a single subdirectory.
    
    Args:
        file: ZIP file to upload.
        
    Returns:
        Uploaded skill information.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive",
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_ZIP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"ZIP file exceeds maximum size of {MAX_ZIP_SIZE // (1024*1024)}MB",
        )
    
    # Extract to temporary directory first
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # Create temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "skill"
                temp_path.mkdir()
                
                # Extract files
                files_extracted, error = _extract_zip_to_skill(zf, temp_path)
                if error:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error,
                    )
                
                # Parse SKILL.md to get skill name
                skill_md_path = temp_path / "SKILL.md"
                if not skill_md_path.exists():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="SKILL.md not found in ZIP file",
                    )
                
                metadata = _parse_skill_metadata(skill_md_path)
                if not metadata:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid SKILL.md format: missing name or description in frontmatter",
                    )
                
                skill_name = metadata["name"]
                
                # Validate skill name
                is_valid, error_msg = _validate_skill_name(skill_name)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid skill name in SKILL.md: {error_msg}",
                    )
                
                # Get target directory
                skills_dir = await _get_user_skills_dir(request, user_id)
                target_dir = skills_dir / skill_name
                
                # Check if skill already exists
                if target_dir.exists():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Skill '{skill_name}' already exists. Delete it first or use update.",
                    )
                
                # Move from temp to target
                skills_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(temp_path), str(target_dir))
                
                # Initialize status
                _set_skill_status(target_dir, {"enabled": True})
                
                logger.info(f"Uploaded skill '{skill_name}' for user {user_id} ({files_extracted} files)")
                
                # Load skill info
                skill_info = _load_skill_info(target_dir, "user", include_content=True)
                if not skill_info:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to load uploaded skill",
                    )
                
                return SkillUploadResponse(
                    skill=skill_info,
                    message=f"Successfully uploaded skill '{skill_name}'",
                    files_extracted=files_extracted,
                )
    
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ZIP file",
        )


@router.get("/{skill_name}", response_model=SkillInfo)
async def get_skill(
    request: Request,
    skill_name: str,
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> SkillInfo:
    """Get a specific skill by name with full content.
    
    Searches in order: user skills, project skills, built-in skills.
    
    Args:
        skill_name: The skill name.
        
    Returns:
        Skill information including full SKILL.md content.
    """
    is_valid, error_msg = _validate_skill_name(skill_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {error_msg}",
        )
    
    # Search in user skills
    user_skills_dir = await _get_user_skills_dir(request, user_id)
    skill_dir = user_skills_dir / skill_name
    if skill_dir.exists():
        skill_info = _load_skill_info(skill_dir, "user", include_content=True)
        if skill_info:
            return skill_info
    
    # Search in project skills
    project_skills_dir = await _get_project_skills_dir(request, user_id)
    if project_skills_dir:
        skill_dir = project_skills_dir / skill_name
        if skill_dir.exists():
            skill_info = _load_skill_info(skill_dir, "project", include_content=True)
            if skill_info:
                return skill_info
    
    # Search in built-in skills
    builtin_skills_dir = _get_builtin_skills_dir()
    skill_dir = builtin_skills_dir / skill_name
    if skill_dir.exists():
        skill_info = _load_skill_info(skill_dir, "builtin", include_content=True)
        if skill_info:
            return skill_info
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Skill '{skill_name}' not found",
    )


@router.put("/{skill_name}", response_model=SkillInfo)
async def update_skill(
    request: Request,
    skill_name: str,
    skill_data: SkillUpdate,
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> SkillInfo:
    """Update an existing skill's content.
    
    Only user skills can be updated. Project and built-in skills are read-only.
    
    Args:
        skill_name: The skill name.
        skill_data: Skill update request.
        
    Returns:
        Updated skill information.
    """
    is_valid, error_msg = _validate_skill_name(skill_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {error_msg}",
        )
    
    skills_dir = await _get_user_skills_dir(request, user_id)
    skill_dir = skills_dir / skill_name
    skill_md_path = skill_dir / "SKILL.md"
    
    if not skill_md_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' not found in user skills",
        )
    
    # Read current metadata
    current_metadata = _parse_skill_metadata(skill_md_path)
    if not current_metadata:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse current SKILL.md",
        )
    
    # Update values
    new_description = skill_data.description or current_metadata["description"]
    new_category = skill_data.category if skill_data.category is not None else current_metadata.get("category")
    new_tags = skill_data.tags if skill_data.tags is not None else current_metadata.get("tags", [])
    
    if skill_data.content is not None:
        new_content = _generate_skill_md(skill_name, new_description, skill_data.content, new_category, new_tags)
    else:
        current_content = skill_md_path.read_text(encoding="utf-8")
        new_content = _generate_skill_md(skill_name, new_description, current_content, new_category, new_tags)
    
    skill_md_path.write_text(new_content, encoding="utf-8")
    
    logger.info(f"Updated skill '{skill_name}' for user {user_id}")
    
    skill_info = _load_skill_info(skill_dir, "user", include_content=True)
    if not skill_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated skill",
        )
    
    return skill_info


@router.patch("/{skill_name}/status", response_model=SkillInfo)
async def update_skill_status(
    request: Request,
    skill_name: str,
    status_data: SkillStatusUpdate,
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> SkillInfo:
    """Enable or disable a skill.
    
    Works for user, project, and built-in skills.
    Status is stored in .skill_status.json file.
    
    Args:
        skill_name: The skill name.
        status_data: Enable/disable status.
        
    Returns:
        Updated skill information.
    """
    is_valid, error_msg = _validate_skill_name(skill_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {error_msg}",
        )
    
    # Find skill directory
    skill_dir = None
    source = None
    
    user_skills_dir = await _get_user_skills_dir(request, user_id)
    if (user_skills_dir / skill_name).exists():
        skill_dir = user_skills_dir / skill_name
        source = "user"
    
    if not skill_dir:
        project_skills_dir = await _get_project_skills_dir(request, user_id)
        if project_skills_dir and (project_skills_dir / skill_name).exists():
            skill_dir = project_skills_dir / skill_name
            source = "project"
    
    if not skill_dir:
        builtin_skills_dir = _get_builtin_skills_dir()
        if (builtin_skills_dir / skill_name).exists():
            skill_dir = builtin_skills_dir / skill_name
            source = "builtin"
    
    if not skill_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' not found",
        )
    
    # Update status
    current_status = _get_skill_status(skill_dir)
    current_status["enabled"] = status_data.enabled
    _set_skill_status(skill_dir, current_status)
    
    logger.info(f"{'Enabled' if status_data.enabled else 'Disabled'} skill '{skill_name}' for user {user_id}")
    
    skill_info = _load_skill_info(skill_dir, source, include_content=False)
    if not skill_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load skill",
        )
    
    return skill_info


@router.delete("/{skill_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    request: Request,
    skill_name: str,
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> None:
    """Delete a skill.
    
    Only user skills can be deleted. Project and built-in skills cannot be deleted.
    
    Args:
        skill_name: The skill name.
    """
    is_valid, error_msg = _validate_skill_name(skill_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {error_msg}",
        )
    
    skills_dir = await _get_user_skills_dir(request, user_id)
    skill_dir = skills_dir / skill_name
    
    if not skill_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' not found in user skills",
        )
    
    shutil.rmtree(skill_dir)
    logger.info(f"Deleted skill '{skill_name}' for user {user_id}")


@router.get("/{skill_name}/export")
async def export_skill(
    request: Request,
    skill_name: str,
    user_id: str = Depends(get_current_user_id),
    _api_key: Optional[str] = Depends(get_api_key),
) -> StreamingResponse:
    """Export a skill as a ZIP file.
    
    Args:
        skill_name: The skill name.
        
    Returns:
        ZIP file download.
    """
    is_valid, error_msg = _validate_skill_name(skill_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid skill name: {error_msg}",
        )
    
    # Find skill directory
    skill_dir = None
    
    user_skills_dir = await _get_user_skills_dir(request, user_id)
    if (user_skills_dir / skill_name).exists():
        skill_dir = user_skills_dir / skill_name
    
    if not skill_dir:
        project_skills_dir = await _get_project_skills_dir(request, user_id)
        if project_skills_dir and (project_skills_dir / skill_name).exists():
            skill_dir = project_skills_dir / skill_name
    
    if not skill_dir:
        builtin_skills_dir = _get_builtin_skills_dir()
        if (builtin_skills_dir / skill_name).exists():
            skill_dir = builtin_skills_dir / skill_name
    
    if not skill_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' not found",
        )
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_dir.rglob("*"):
            if file_path.is_file() and file_path.name != SKILL_STATUS_FILE:
                arcname = str(file_path.relative_to(skill_dir))
                zf.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{skill_name}.zip"'
        },
    )
