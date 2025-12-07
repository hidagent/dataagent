#!/usr/bin/env python3
"""Initialize test users for multi-tenant isolation testing.

This script creates two test users (test_alice and test_bob) with
isolated resources for verifying multi-tenant security.

Usage:
    python scripts/init_test_users.py [--reset] [--verbose]

Options:
    --reset     Reset all test data to initial state
    --verbose   Show detailed output
"""

import argparse
import json
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TestUser:
    """Test user configuration."""
    
    user_id: str
    display_name: str
    department: str
    role: str
    secret_markers: dict[str, str] = field(default_factory=dict)


# Pre-configured test users
TEST_USERS = [
    TestUser(
        user_id="test_alice",
        display_name="Alice Test",
        department="Engineering",
        role="Developer",
        secret_markers={
            "file": "ALICE_SECRET_FILE_MARKER_XYZ123",
            "rule": "ALICE_RULE_MARKER_ABC456",
            "memory": "ALICE_MEMORY_MARKER_DEF789",
            "db": "ALICE_DB_SECRET_GHI012",
            "skill": "ALICE_SKILL_MARKER_JKL345",
        }
    ),
    TestUser(
        user_id="test_bob",
        display_name="Bob Test",
        department="Sales",
        role="Analyst",
        secret_markers={
            "file": "BOB_SECRET_FILE_MARKER_MNO678",
            "rule": "BOB_RULE_MARKER_PQR901",
            "memory": "BOB_MEMORY_MARKER_STU234",
            "db": "BOB_DB_SECRET_VWX567",
            "skill": "BOB_SKILL_MARKER_YZA890",
        }
    ),
]

# Base directory for test data
TEST_BASE_DIR = Path("/tmp/dataagent-test")


# =============================================================================
# Initialization Functions
# =============================================================================

def get_user_paths(user: TestUser) -> dict[str, Path]:
    """Get all paths for a user."""
    return {
        "workspace": TEST_BASE_DIR / "workspaces" / user.user_id,
        "knowledge": TEST_BASE_DIR / "workspaces" / user.user_id / "knowledge",
        "rules": TEST_BASE_DIR / "users" / user.user_id / "rules",
        "memory": TEST_BASE_DIR / "users" / user.user_id / "agent",
        "mcp_db": TEST_BASE_DIR / "mcp" / f"{user.user_id}.db",
    }


def create_directories(user: TestUser, verbose: bool = False) -> None:
    """Create directories for a user."""
    paths = get_user_paths(user)
    
    for name, path in paths.items():
        if name == "mcp_db":
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
        
        if verbose:
            print(f"  Created: {path}")


def create_knowledge_files(user: TestUser, verbose: bool = False) -> None:
    """Create knowledge files for a user."""
    paths = get_user_paths(user)
    knowledge_dir = paths["knowledge"]
    
    # FAQ file
    faq_content = f"""# {user.display_name}'s FAQ

## Secret Marker
This file contains: {user.secret_markers['file']}

## Q1: What is your role?
I am a {user.role} in the {user.department} department.

## Q2: What projects are you working on?
This is {user.user_id}'s private project information.

## Q3: How to contact you?
Contact {user.display_name} through internal channels only.

## Q4: What tools do you use?
This information is specific to {user.user_id}.
"""
    (knowledge_dir / f"{user.user_id}-faq.md").write_text(faq_content)
    
    # Guide file
    guide_content = f"""# {user.display_name}'s Guide

## Private Information
User ID: {user.user_id}
Secret: {user.secret_markers['file']}_GUIDE

## Instructions
This guide is only for {user.display_name}.
Department: {user.department}
Role: {user.role}
"""
    (knowledge_dir / f"{user.user_id}-guide.md").write_text(guide_content)
    
    # Notes file
    notes_content = f"""# {user.display_name}'s Notes

## Confidential Notes
Contains: {user.secret_markers['file']}_NOTES

These notes belong to {user.user_id} only.
Created for isolation testing.
"""
    (knowledge_dir / f"{user.user_id}-notes.md").write_text(notes_content)
    
    if verbose:
        print(f"  Created knowledge files in: {knowledge_dir}")


def create_rules(user: TestUser, verbose: bool = False) -> None:
    """Create rule files for a user."""
    paths = get_user_paths(user)
    rules_dir = paths["rules"]
    
    # Main rule
    main_rule = f"""---
name: {user.user_id}-main-rule
description: Main rule for {user.display_name}
inclusion: always
priority: 90
---

# {user.display_name}'s Main Rule

## Secret Marker
{user.secret_markers['rule']}

## Instructions
This rule is specific to {user.user_id}.
Department: {user.department}
Role: {user.role}
"""
    (rules_dir / f"{user.user_id}-main-rule.md").write_text(main_rule)
    
    # Secondary rule
    secondary_rule = f"""---
name: {user.user_id}-secondary-rule
description: Secondary rule for {user.display_name}
inclusion: manual
priority: 50
---

# {user.display_name}'s Secondary Rule

Contains: {user.secret_markers['rule']}_SECONDARY

This is a manual-inclusion rule for {user.user_id}.
"""
    (rules_dir / f"{user.user_id}-secondary-rule.md").write_text(secondary_rule)
    
    if verbose:
        print(f"  Created rules in: {rules_dir}")


def create_memory(user: TestUser, verbose: bool = False) -> None:
    """Create memory/agent.md for a user."""
    paths = get_user_paths(user)
    memory_dir = paths["memory"]
    
    memory_content = f"""# {user.display_name}'s Memory

## User Preferences
- User ID: {user.user_id}
- Display Name: {user.display_name}
- Department: {user.department}
- Role: {user.role}

## Secret Marker
{user.secret_markers['memory']}

## Private Notes
This memory belongs exclusively to {user.user_id}.
It should never be visible to other users.

## Preferences
- Language: English
- Theme: Dark
- Notifications: Enabled
"""
    (memory_dir / "agent.md").write_text(memory_content)
    
    if verbose:
        print(f"  Created memory in: {memory_dir}")


def create_mcp_database(user: TestUser, verbose: bool = False) -> None:
    """Create MCP database for a user."""
    paths = get_user_paths(user)
    db_path = paths["mcp_db"]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY,
            content TEXT,
            secret_marker TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id INTEGER PRIMARY KEY,
            server_name TEXT UNIQUE,
            config_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert test data
    data_rows = [
        (f"{user.display_name}'s report 1", f"{user.secret_markers['db']}_001", "report"),
        (f"{user.display_name}'s report 2", f"{user.secret_markers['db']}_002", "report"),
        (f"{user.display_name}'s analysis", f"{user.secret_markers['db']}_003", "analysis"),
        (f"{user.display_name}'s notes", f"{user.secret_markers['db']}_004", "notes"),
        (f"{user.display_name}'s summary", f"{user.secret_markers['db']}_005", "summary"),
    ]
    
    cursor.executemany(
        "INSERT INTO user_data (content, secret_marker, category) VALUES (?, ?, ?)",
        data_rows
    )
    
    # Insert MCP server configs
    server_configs = [
        (f"{user.user_id}-database", json.dumps({"type": "sqlite", "user": user.user_id})),
        (f"{user.user_id}-api", json.dumps({"type": "http", "user": user.user_id})),
    ]
    
    cursor.executemany(
        "INSERT INTO mcp_servers (server_name, config_json) VALUES (?, ?)",
        server_configs
    )
    
    conn.commit()
    conn.close()
    
    if verbose:
        print(f"  Created MCP database: {db_path}")


def init_user(user: TestUser, verbose: bool = False) -> None:
    """Initialize all resources for a user."""
    print(f"\nInitializing {user.display_name} ({user.user_id})...")
    
    create_directories(user, verbose)
    create_knowledge_files(user, verbose)
    create_rules(user, verbose)
    create_memory(user, verbose)
    create_mcp_database(user, verbose)
    
    print(f"  ✅ {user.user_id} initialized successfully")


def reset_test_data() -> None:
    """Reset all test data."""
    print("\nResetting test data...")
    
    if TEST_BASE_DIR.exists():
        shutil.rmtree(TEST_BASE_DIR)
        print(f"  Removed: {TEST_BASE_DIR}")
    
    print("  ✅ Test data reset complete")


def verify_isolation(verbose: bool = False) -> bool:
    """Verify that test users are properly isolated."""
    print("\nVerifying isolation...")
    
    alice = TEST_USERS[0]
    bob = TEST_USERS[1]
    
    alice_paths = get_user_paths(alice)
    bob_paths = get_user_paths(bob)
    
    issues = []
    
    # Check that paths are different
    for key in alice_paths:
        if alice_paths[key] == bob_paths[key]:
            issues.append(f"Paths overlap for {key}")
    
    # Check that Alice's files don't contain Bob's markers
    for file_path in alice_paths["knowledge"].glob("*.md"):
        content = file_path.read_text()
        for marker_type, marker in bob.secret_markers.items():
            if marker in content:
                issues.append(f"Alice's {file_path.name} contains Bob's {marker_type} marker")
    
    # Check that Bob's files don't contain Alice's markers
    for file_path in bob_paths["knowledge"].glob("*.md"):
        content = file_path.read_text()
        for marker_type, marker in alice.secret_markers.items():
            if marker in content:
                issues.append(f"Bob's {file_path.name} contains Alice's {marker_type} marker")
    
    if issues:
        print("  ❌ Isolation issues found:")
        for issue in issues:
            print(f"    - {issue}")
        return False
    else:
        print("  ✅ Isolation verified successfully")
        return True


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Initialize test users for multi-tenant isolation testing"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all test data to initial state"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Multi-Tenant Test User Initialization")
    print("=" * 60)
    
    if args.reset:
        reset_test_data()
    
    # Initialize each test user
    for user in TEST_USERS:
        init_user(user, args.verbose)
    
    # Verify isolation
    if not verify_isolation(args.verbose):
        print("\n❌ Initialization completed with issues")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Test users initialized successfully")
    print("=" * 60)
    print(f"\nTest data location: {TEST_BASE_DIR}")
    print("\nTest users:")
    for user in TEST_USERS:
        print(f"  - {user.user_id}: {user.display_name} ({user.department}/{user.role})")
    
    print("\nRun isolation tests with:")
    print("  ./scripts/run_isolation_tests.sh")
    print("  # or")
    print("  pytest source/dataagent-server/tests/test_multi_tenant/ -v")


if __name__ == "__main__":
    main()
