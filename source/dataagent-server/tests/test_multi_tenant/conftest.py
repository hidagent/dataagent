"""Test fixtures for multi-tenant isolation tests.

Provides test users, test data, and isolation verification utilities.
"""

import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Test User Configuration
# =============================================================================

@dataclass
class IsolationTestUser:
    """Test user configuration for isolation testing.
    
    Note: Named IsolationTestUser instead of TestUser to avoid
    pytest collection warnings.
    """
    
    user_id: str
    display_name: str
    department: str
    role: str
    secret_markers: dict[str, str] = field(default_factory=dict)
    
    @property
    def workspace_path(self) -> Path:
        """Get user's workspace path."""
        return Path(tempfile.gettempdir()) / "dataagent-test" / "workspaces" / self.user_id
    
    @property
    def rules_path(self) -> Path:
        """Get user's rules path."""
        return Path(tempfile.gettempdir()) / "dataagent-test" / "users" / self.user_id / "rules"
    
    @property
    def memory_path(self) -> Path:
        """Get user's memory path."""
        return Path(tempfile.gettempdir()) / "dataagent-test" / "users" / self.user_id / "agent"
    
    @property
    def mcp_db_path(self) -> Path:
        """Get user's MCP database path."""
        return Path(tempfile.gettempdir()) / "dataagent-test" / "mcp" / f"{self.user_id}.db"


# Type alias for backward compatibility
TestUser = IsolationTestUser

# Pre-configured test users
TEST_ALICE = IsolationTestUser(
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
)

TEST_BOB = IsolationTestUser(
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
)


# =============================================================================
# Security Audit
# =============================================================================

@dataclass
class SecurityAuditEvent:
    """Security audit event."""
    
    timestamp: datetime
    requesting_user: str
    target_user: str
    resource_type: str  # mcp, rule, file, skill, memory
    resource_id: str
    action: str  # read, write, delete, execute, list
    result: str  # allowed, denied
    details: dict[str, Any] = field(default_factory=dict)


class SecurityAuditLogger:
    """Logger for security audit events."""
    
    def __init__(self):
        self.events: list[SecurityAuditEvent] = []
    
    def log(
        self,
        requesting_user: str,
        target_user: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a security audit event."""
        event = SecurityAuditEvent(
            timestamp=datetime.utcnow(),
            requesting_user=requesting_user,
            target_user=target_user,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details or {},
        )
        self.events.append(event)
    
    def get_violations(self) -> list[SecurityAuditEvent]:
        """Get all security violations (cross-tenant access that was allowed)."""
        return [
            e for e in self.events
            if e.requesting_user != e.target_user and e.result == "allowed"
        ]
    
    def get_cross_tenant_attempts(self) -> list[SecurityAuditEvent]:
        """Get all cross-tenant access attempts."""
        return [
            e for e in self.events
            if e.requesting_user != e.target_user
        ]
    
    def generate_report(self) -> dict[str, Any]:
        """Generate audit report."""
        cross_tenant = self.get_cross_tenant_attempts()
        violations = self.get_violations()
        
        return {
            "total_events": len(self.events),
            "cross_tenant_attempts": len(cross_tenant),
            "violations": len(violations),
            "all_blocked": len(violations) == 0,
            "events_by_type": self._group_by_type(),
            "violation_details": [
                {
                    "timestamp": v.timestamp.isoformat(),
                    "requesting_user": v.requesting_user,
                    "target_user": v.target_user,
                    "resource_type": v.resource_type,
                    "resource_id": v.resource_id,
                    "action": v.action,
                }
                for v in violations
            ],
        }
    
    def _group_by_type(self) -> dict[str, int]:
        """Group events by resource type."""
        result: dict[str, int] = {}
        for event in self.events:
            result[event.resource_type] = result.get(event.resource_type, 0) + 1
        return result


# =============================================================================
# Test Data Initialization
# =============================================================================

def init_test_user_files(user: IsolationTestUser) -> None:
    """Initialize test files for a user."""
    # Create directories
    user.workspace_path.mkdir(parents=True, exist_ok=True)
    user.rules_path.mkdir(parents=True, exist_ok=True)
    user.memory_path.mkdir(parents=True, exist_ok=True)
    user.mcp_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    knowledge_dir = user.workspace_path / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    
    # Create knowledge files
    (knowledge_dir / f"{user.user_id}-faq.md").write_text(f"""# {user.display_name}'s FAQ

## Secret Marker
This file contains: {user.secret_markers['file']}

## Q1: What is your role?
I am a {user.role} in the {user.department} department.

## Q2: What projects are you working on?
This is {user.user_id}'s private project information.
""")
    
    (knowledge_dir / f"{user.user_id}-guide.md").write_text(f"""# {user.display_name}'s Guide

## Private Information
User ID: {user.user_id}
Secret: {user.secret_markers['file']}_GUIDE

## Instructions
This guide is only for {user.display_name}.
""")
    
    (knowledge_dir / f"{user.user_id}-notes.md").write_text(f"""# {user.display_name}'s Notes

## Confidential Notes
Contains: {user.secret_markers['file']}_NOTES

These notes belong to {user.user_id} only.
""")
    
    # Create rules
    (user.rules_path / f"{user.user_id}-main-rule.md").write_text(f"""---
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
""")
    
    (user.rules_path / f"{user.user_id}-secondary-rule.md").write_text(f"""---
name: {user.user_id}-secondary-rule
description: Secondary rule for {user.display_name}
inclusion: manual
priority: 50
---

# {user.display_name}'s Secondary Rule

Contains: {user.secret_markers['rule']}_SECONDARY
""")
    
    # Create memory/agent.md
    (user.memory_path / "agent.md").write_text(f"""# {user.display_name}'s Memory

## User Preferences
- User ID: {user.user_id}
- Display Name: {user.display_name}
- Department: {user.department}
- Role: {user.role}

## Secret Marker
{user.secret_markers['memory']}

## Private Notes
This memory belongs exclusively to {user.user_id}.
""")
    
    # Create MCP database
    init_user_mcp_db(user)


def init_user_mcp_db(user: IsolationTestUser) -> None:
    """Initialize MCP database for a user."""
    conn = sqlite3.connect(user.mcp_db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY,
            content TEXT,
            secret_marker TEXT,
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
    cursor.executemany(
        "INSERT INTO user_data (content, secret_marker) VALUES (?, ?)",
        [
            (f"{user.display_name}'s report 1", f"{user.secret_markers['db']}_001"),
            (f"{user.display_name}'s report 2", f"{user.secret_markers['db']}_002"),
            (f"{user.display_name}'s report 3", f"{user.secret_markers['db']}_003"),
        ]
    )
    
    # Insert MCP server configs
    cursor.executemany(
        "INSERT INTO mcp_servers (server_name, config_json) VALUES (?, ?)",
        [
            (f"{user.user_id}-database", f'{{"type": "sqlite", "user": "{user.user_id}"}}'),
            (f"{user.user_id}-api", f'{{"type": "http", "user": "{user.user_id}"}}'),
        ]
    )
    
    conn.commit()
    conn.close()


def cleanup_test_data() -> None:
    """Clean up all test data."""
    test_dir = Path(tempfile.gettempdir()) / "dataagent-test"
    if test_dir.exists():
        shutil.rmtree(test_dir)


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_base_dir() -> Generator[Path, None, None]:
    """Create and cleanup test base directory."""
    base_dir = Path(tempfile.gettempdir()) / "dataagent-test"
    base_dir.mkdir(parents=True, exist_ok=True)
    yield base_dir
    # Cleanup after all tests
    if base_dir.exists():
        shutil.rmtree(base_dir)


@pytest.fixture(scope="session")
def alice(test_base_dir: Path) -> IsolationTestUser:
    """Get test_alice user with initialized data."""
    init_test_user_files(TEST_ALICE)
    return TEST_ALICE


@pytest.fixture(scope="session")
def bob(test_base_dir: Path) -> IsolationTestUser:
    """Get test_bob user with initialized data."""
    init_test_user_files(TEST_BOB)
    return TEST_BOB


@pytest.fixture
def security_audit() -> SecurityAuditLogger:
    """Get a fresh security audit logger."""
    return SecurityAuditLogger()


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """Get FastAPI test client."""
    from dataagent_server.main import app
    with TestClient(app) as client:
        yield client


# =============================================================================
# Test Helpers
# =============================================================================

def assert_contains_marker(content: str, marker: str, should_contain: bool = True) -> None:
    """Assert that content contains (or doesn't contain) a marker."""
    contains = marker in content
    if should_contain:
        assert contains, f"Expected content to contain '{marker}'"
    else:
        assert not contains, f"Expected content NOT to contain '{marker}'"


def assert_isolation_enforced(
    response_status: int,
    expected_status: int = 403,
    allowed_statuses: list[int] | None = None,
) -> None:
    """Assert that isolation is enforced (access denied)."""
    allowed = allowed_statuses or [403, 404]
    assert response_status in allowed, (
        f"Expected access to be denied (status {allowed}), "
        f"but got {response_status}"
    )


def make_request_as_user(
    client: TestClient,
    user: IsolationTestUser,
    method: str,
    url: str,
    **kwargs,
) -> Any:
    """Make an API request as a specific user."""
    headers = kwargs.pop("headers", {})
    headers["X-User-ID"] = user.user_id
    
    method_func = getattr(client, method.lower())
    return method_func(url, headers=headers, **kwargs)
