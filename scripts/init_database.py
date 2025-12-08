#!/usr/bin/env python3
"""Database initialization script for DataAgent.

This script initializes the database schema for DataAgent multi-tenant system.
Supports both SQLite3 and PostgreSQL databases.

Usage:
    # SQLite (default)
    python scripts/init_database.py
    
    # SQLite with custom path
    python scripts/init_database.py --db-path /path/to/dataagent.db
    
    # PostgreSQL
    python scripts/init_database.py --db-type postgres --db-url "postgresql+asyncpg://user:pass@localhost/dataagent"
    
    # Check current version
    python scripts/init_database.py --check
    
    # Rollback to specific version
    python scripts/init_database.py --rollback 003
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "source" / "dataagent-core"))

from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_database(
    db_type: str = "sqlite",
    db_path: str | None = None,
    db_url: str | None = None,
    check_only: bool = False,
    rollback_to: str | None = None,
) -> None:
    """Initialize or migrate the database.
    
    Args:
        db_type: Database type ('sqlite' or 'postgres')
        db_path: Path to SQLite database file
        db_url: Full database URL (for PostgreSQL)
        check_only: Only check current version, don't migrate
        rollback_to: Version to rollback to
    """
    from dataagent_core.database.migration import MigrationManager
    
    # Build database URL
    if db_url:
        url = db_url
    elif db_type == "sqlite":
        if db_path is None:
            db_path = Path.home() / ".dataagent" / "dataagent.db"
        else:
            db_path = Path(db_path)
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+aiosqlite:///{db_path}"
        logger.info(f"Using SQLite database: {db_path}")
    else:
        raise ValueError("PostgreSQL requires --db-url parameter")
    
    # Create engine
    engine = create_async_engine(url, echo=False)
    
    try:
        # Initialize migration manager
        manager = MigrationManager(engine)
        await manager.init()
        
        # Get current version
        current = await manager.get_current_version()
        logger.info(f"Current schema version: {current or 'None (fresh database)'}")
        
        if check_only:
            applied = await manager.get_applied_versions()
            logger.info(f"Applied migrations: {applied}")
            return
        
        if rollback_to:
            logger.info(f"Rolling back to version: {rollback_to}")
            rolled_back = await manager.rollback(rollback_to)
            if rolled_back:
                logger.info(f"Rolled back migrations: {rolled_back}")
            else:
                logger.info("No migrations to rollback")
            return
        
        # Apply migrations
        logger.info("Applying pending migrations...")
        applied = await manager.migrate()
        
        if applied:
            logger.info(f"Applied migrations: {applied}")
        else:
            logger.info("Database is up to date")
        
        # Show final version
        final = await manager.get_current_version()
        logger.info(f"Final schema version: {final}")
        
    finally:
        await engine.dispose()


async def create_test_user(
    db_type: str = "sqlite",
    db_path: str | None = None,
    db_url: str | None = None,
    user_id: str = "admin",
    username: str = "admin",
    display_name: str = "Administrator",
) -> None:
    """Create a test user in the database.
    
    Args:
        db_type: Database type
        db_path: SQLite database path
        db_url: Full database URL
        user_id: User ID
        username: Username
        display_name: Display name
    """
    from sqlalchemy import text
    
    # Build database URL
    if db_url:
        url = db_url
    elif db_type == "sqlite":
        if db_path is None:
            db_path = Path.home() / ".dataagent" / "dataagent.db"
        url = f"sqlite+aiosqlite:///{db_path}"
    else:
        raise ValueError("PostgreSQL requires --db-url parameter")
    
    engine = create_async_engine(url, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Check if user exists
            result = await conn.execute(
                text("SELECT user_id FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            if result.fetchone():
                logger.info(f"User '{user_id}' already exists")
                return
            
            # Create user
            await conn.execute(
                text("""
                    INSERT INTO users (user_id, username, display_name, status)
                    VALUES (:user_id, :username, :display_name, 'active')
                """),
                {
                    "user_id": user_id,
                    "username": username,
                    "display_name": display_name,
                }
            )
            logger.info(f"Created user: {user_id} ({display_name})")
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Initialize DataAgent database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgres"],
        default="sqlite",
        help="Database type (default: sqlite)"
    )
    parser.add_argument(
        "--db-path",
        help="Path to SQLite database file (default: ~/.dataagent/dataagent.db)"
    )
    parser.add_argument(
        "--db-url",
        help="Full database URL (required for PostgreSQL)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check current version, don't migrate"
    )
    parser.add_argument(
        "--rollback",
        metavar="VERSION",
        help="Rollback to specific version"
    )
    parser.add_argument(
        "--create-user",
        action="store_true",
        help="Create a test admin user"
    )
    parser.add_argument(
        "--user-id",
        default="admin",
        help="User ID for test user (default: admin)"
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Username for test user (default: admin)"
    )
    parser.add_argument(
        "--display-name",
        default="Administrator",
        help="Display name for test user (default: Administrator)"
    )
    
    args = parser.parse_args()
    
    async def run():
        # Initialize database
        await init_database(
            db_type=args.db_type,
            db_path=args.db_path,
            db_url=args.db_url,
            check_only=args.check,
            rollback_to=args.rollback,
        )
        
        # Create test user if requested
        if args.create_user:
            await create_test_user(
                db_type=args.db_type,
                db_path=args.db_path,
                db_url=args.db_url,
                user_id=args.user_id,
                username=args.username,
                display_name=args.display_name,
            )
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
