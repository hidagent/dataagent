#!/usr/bin/env python3
"""Initialize test users for DataAgent Server.

This script creates test users in the s_user table for development and testing.
"""

import asyncio
import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "source" / "dataagent-server"))

from dataagent_server.database import DatabaseFactory, get_db_session, SUser
from dataagent_server.auth import hash_password
from sqlalchemy import select


async def create_test_users():
    """Create test users."""
    # Initialize database tables
    await DatabaseFactory.create_tables()
    
    test_users = [
        {
            "user_id": "admin",
            "username": "admin",
            "display_name": "Administrator",
            "email": "admin@example.com",
            "user_source": "local",
            "password": "admin123",
            "department": "IT",
            "role": "admin",
        },
        {
            "user_id": "alice",
            "username": "alice",
            "display_name": "Alice",
            "email": "alice@example.com",
            "user_source": "local",
            "password": "alice123",
            "department": "Engineering",
            "role": "developer",
        },
        {
            "user_id": "bob",
            "username": "bob",
            "display_name": "Bob",
            "email": "bob@example.com",
            "user_source": "local",
            "password": "bob123",
            "department": "Data",
            "role": "analyst",
        },
        {
            "user_id": "dataagent",
            "username": "dataagent",
            "display_name": "DataAgent Default User",
            "email": "dataagent@example.com",
            "user_source": "local",
            "password": "dataagent",
            "department": "System",
            "role": "user",
        },
    ]
    
    async with get_db_session() as session:
        for user_data in test_users:
            # Check if user exists
            result = await session.execute(
                select(SUser).where(SUser.username == user_data["username"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"User '{user_data['username']}' already exists, skipping")
                continue
            
            # Create user
            user = SUser(
                user_id=user_data["user_id"],
                username=user_data["username"],
                display_name=user_data["display_name"],
                email=user_data["email"],
                user_source=user_data["user_source"],
                password_hash=hash_password(user_data["password"]),
                department=user_data["department"],
                role=user_data["role"],
                status="active",
            )
            session.add(user)
            print(f"Created user: {user_data['username']}")
        
        await session.commit()
    
    print("\nTest users created successfully!")
    print("\nLogin credentials:")
    print("-" * 40)
    for user_data in test_users:
        print(f"  Username: {user_data['username']}")
        print(f"  Password: {user_data['password']}")
        print()


async def main():
    """Main entry point."""
    print("Initializing DataAgent Server test users...")
    print("=" * 50)
    
    try:
        await create_test_users()
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await DatabaseFactory.close()


if __name__ == "__main__":
    asyncio.run(main())
