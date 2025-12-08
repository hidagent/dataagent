"""Database migration management for DataAgent Server."""

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dataagent_server.database.factory import get_db_session

logger = logging.getLogger(__name__)

# Migration scripts directory
SCRIPTS_DIR = Path(__file__).parent / "scripts"


class MigrationManager:
    """Database migration manager."""
    
    @staticmethod
    def get_script_checksum(script_path: Path) -> str:
        """Calculate checksum for a migration script."""
        content = script_path.read_text(encoding="utf-8")
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    async def get_current_version(session: AsyncSession) -> str | None:
        """Get current schema version."""
        try:
            result = await session.execute(
                text("SELECT version FROM s_schema_version ORDER BY id DESC LIMIT 1")
            )
            row = result.fetchone()
            return row[0] if row else None
        except Exception:
            return None
    
    @staticmethod
    async def apply_migration(
        session: AsyncSession,
        version: str,
        description: str,
        sql_script: str,
        applied_by: str = "system",
    ) -> bool:
        """Apply a migration script.
        
        Args:
            session: Database session
            version: Version string (e.g., "V001")
            description: Migration description
            sql_script: SQL script content
            applied_by: User who applied the migration
            
        Returns:
            True if successful
        """
        try:
            # Execute migration script
            for statement in sql_script.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    await session.execute(text(statement))
            
            # Record migration
            checksum = hashlib.sha256(sql_script.encode()).hexdigest()[:16]
            await session.execute(
                text("""
                    INSERT INTO s_schema_version (version, description, checksum, applied_by)
                    VALUES (:version, :description, :checksum, :applied_by)
                """),
                {
                    "version": version,
                    "description": description,
                    "checksum": checksum,
                    "applied_by": applied_by,
                },
            )
            
            await session.commit()
            logger.info(f"Applied migration {version}: {description}")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Migration {version} failed: {e}")
            raise
    
    @classmethod
    async def run_migrations(cls, db_type: str = "sqlite") -> None:
        """Run all pending migrations.
        
        Args:
            db_type: Database type ("sqlite" or "postgres")
        """
        script_file = SCRIPTS_DIR / f"{db_type}_schema.sql"
        
        if not script_file.exists():
            logger.warning(f"Migration script not found: {script_file}")
            return
        
        async with get_db_session() as session:
            current_version = await cls.get_current_version(session)
            
            if current_version:
                logger.info(f"Current schema version: {current_version}")
            else:
                logger.info("No schema version found, applying initial migration")
                
                # Apply initial schema
                sql_script = script_file.read_text(encoding="utf-8")
                await cls.apply_migration(
                    session,
                    version="V001",
                    description="Initial schema with all system tables",
                    sql_script=sql_script,
                )
