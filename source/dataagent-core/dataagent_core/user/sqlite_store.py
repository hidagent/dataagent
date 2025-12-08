"""SQLite user profile store implementation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Index, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

from dataagent_core.session.models import Base
from dataagent_core.user.profile import UserProfile
from dataagent_core.user.store import UserProfileStore

logger = logging.getLogger(__name__)


class UserProfileModel(Base):
    """SQLAlchemy model for user_profiles table."""
    
    __tablename__ = "user_profiles"
    
    user_id = Column(String(64), primary_key=True)
    username = Column(String(64), nullable=False)
    display_name = Column(String(128), nullable=False)
    email = Column(String(256), nullable=True)
    department = Column(String(128), nullable=True)
    role = Column(String(64), nullable=True)
    custom_fields = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index("idx_user_profiles_username", "username"),
    )


class SQLiteUserProfileStore(UserProfileStore):
    """SQLite user profile store implementation.
    
    Uses SQLAlchemy async engine with aiosqlite for async SQLite access.
    
    Args:
        db_path: Path to SQLite database file. Defaults to ~/.dataagent/dataagent.db
        engine: Optional existing SQLAlchemy async engine to share.
    """
    
    def __init__(
        self,
        db_path: str | Path | None = None,
        engine: "AsyncEngine | None" = None,
    ) -> None:
        if engine is not None:
            self._engine = engine
            self._owns_engine = False
            self.db_path = None
        else:
            if db_path is None:
                db_path = Path.home() / ".dataagent" / "dataagent.db"
            
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            url = f"sqlite+aiosqlite:///{self.db_path}"
            self._engine = create_async_engine(url, echo=False)
            self._owns_engine = True
        
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def init_tables(self) -> None:
        """Initialize database tables."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"User profiles table initialized: {self.db_path}")
    
    async def close(self) -> None:
        """Close the database engine if owned."""
        if self._owns_engine:
            await self._engine.dispose()
            logger.info("SQLite user profile store closed")
    
    def _model_to_profile(self, model: UserProfileModel) -> UserProfile:
        """Convert SQLAlchemy model to UserProfile dataclass."""
        custom_fields = {}
        if model.custom_fields:
            try:
                custom_fields = json.loads(model.custom_fields)
            except json.JSONDecodeError:
                pass
        
        return UserProfile(
            user_id=model.user_id,
            username=model.username,
            display_name=model.display_name,
            email=model.email,
            department=model.department,
            role=model.role,
            custom_fields=custom_fields,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _profile_to_model(self, profile: UserProfile) -> UserProfileModel:
        """Convert UserProfile dataclass to SQLAlchemy model."""
        custom_fields_json = None
        if profile.custom_fields:
            custom_fields_json = json.dumps(profile.custom_fields, ensure_ascii=False)
        
        return UserProfileModel(
            user_id=profile.user_id,
            username=profile.username,
            display_name=profile.display_name,
            email=profile.email,
            department=profile.department,
            role=profile.role,
            custom_fields=custom_fields_json,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    async def get_profile(self, user_id: str) -> UserProfile | None:
        """获取用户档案。"""
        async with self._session_factory() as db:
            result = await db.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            model = result.scalar_one_or_none()
            
            if model is None:
                return None
            
            return self._model_to_profile(model)
    
    async def save_profile(self, profile: UserProfile) -> None:
        """保存用户档案。"""
        async with self._session_factory() as db:
            # Check if exists
            result = await db.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == profile.user_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.username = profile.username
                existing.display_name = profile.display_name
                existing.email = profile.email
                existing.department = profile.department
                existing.role = profile.role
                existing.custom_fields = (
                    json.dumps(profile.custom_fields, ensure_ascii=False)
                    if profile.custom_fields else None
                )
                existing.updated_at = datetime.now()
            else:
                # Create new
                model = self._profile_to_model(profile)
                db.add(model)
            
            await db.commit()
            logger.debug(f"Saved user profile: {profile.user_id}")
    
    async def delete_profile(self, user_id: str) -> bool:
        """删除用户档案。"""
        async with self._session_factory() as db:
            result = await db.execute(
                delete(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            await db.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Deleted user profile: {user_id}")
            return deleted
    
    async def update_profile(
        self, user_id: str, updates: dict[str, Any]
    ) -> UserProfile | None:
        """更新用户档案。"""
        async with self._session_factory() as db:
            result = await db.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            model = result.scalar_one_or_none()
            
            if model is None:
                return None
            
            # Update fields
            for key, value in updates.items():
                if key == "custom_fields" and value is not None:
                    model.custom_fields = json.dumps(value, ensure_ascii=False)
                elif hasattr(model, key) and key not in ("user_id", "created_at"):
                    setattr(model, key, value)
            
            model.updated_at = datetime.now()
            await db.commit()
            
            logger.debug(f"Updated user profile: {user_id}")
            return self._model_to_profile(model)
    
    async def list_profiles(self) -> list[UserProfile]:
        """列出所有用户档案。"""
        async with self._session_factory() as db:
            result = await db.execute(
                select(UserProfileModel).order_by(UserProfileModel.created_at.desc())
            )
            models = result.scalars().all()
            return [self._model_to_profile(m) for m in models]
