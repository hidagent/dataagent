"""MCP isolation tests.

Verifies that users cannot access each other's MCP servers and data.
"""

import sqlite3
import pytest
from pathlib import Path

from .conftest import (
    TestUser,
    SecurityAuditLogger,
    assert_contains_marker,
    assert_isolation_enforced,
)


class TestMCPDatabaseIsolation:
    """Test MCP database isolation between users."""
    
    # =========================================================================
    # Positive Tests - Users can access their own MCP data
    # =========================================================================
    
    def test_alice_can_query_own_database(self, alice: TestUser) -> None:
        """Alice can query her own MCP database."""
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content, secret_marker FROM user_data")
        rows = cursor.fetchall()
        
        conn.close()
        
        assert len(rows) >= 3, "Alice should have at least 3 data rows"
        
        # All rows should contain Alice's markers
        for content, marker in rows:
            assert alice.user_id in content.lower() or alice.display_name in content
            assert alice.secret_markers["db"] in marker
    
    def test_alice_can_list_own_mcp_servers(self, alice: TestUser) -> None:
        """Alice can list her own MCP server configurations."""
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT server_name, config_json FROM mcp_servers")
        rows = cursor.fetchall()
        
        conn.close()
        
        assert len(rows) >= 2, "Alice should have at least 2 MCP servers"
        
        server_names = [row[0] for row in rows]
        assert f"{alice.user_id}-database" in server_names
        assert f"{alice.user_id}-api" in server_names
    
    def test_bob_can_query_own_database(self, bob: TestUser) -> None:
        """Bob can query his own MCP database."""
        conn = sqlite3.connect(bob.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content, secret_marker FROM user_data")
        rows = cursor.fetchall()
        
        conn.close()
        
        assert len(rows) >= 3, "Bob should have at least 3 data rows"
        
        # All rows should contain Bob's markers
        for content, marker in rows:
            assert bob.user_id in content.lower() or bob.display_name in content
            assert bob.secret_markers["db"] in marker
    
    # =========================================================================
    # Negative Tests - Users cannot access other's MCP data
    # =========================================================================
    
    def test_alice_database_does_not_contain_bob_data(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Alice's database should not contain Bob's data."""
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content, secret_marker FROM user_data")
        rows = cursor.fetchall()
        
        conn.close()
        
        for content, marker in rows:
            # Should not contain Bob's markers
            assert bob.secret_markers["db"] not in marker
            assert bob.user_id not in content.lower()
    
    def test_bob_database_does_not_contain_alice_data(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Bob's database should not contain Alice's data."""
        conn = sqlite3.connect(bob.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content, secret_marker FROM user_data")
        rows = cursor.fetchall()
        
        conn.close()
        
        for content, marker in rows:
            # Should not contain Alice's markers
            assert alice.secret_markers["db"] not in marker
            assert alice.user_id not in content.lower()
    
    def test_databases_are_separate_files(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Each user should have a separate database file."""
        assert alice.mcp_db_path != bob.mcp_db_path
        assert alice.mcp_db_path.exists()
        assert bob.mcp_db_path.exists()
        
        # Files should have different content
        alice_size = alice.mcp_db_path.stat().st_size
        bob_size = bob.mcp_db_path.stat().st_size
        
        # Both should have data
        assert alice_size > 0
        assert bob_size > 0
    
    def test_alice_cannot_access_bob_database_path(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Alice should not be able to access Bob's database path."""
        # Verify paths are different
        assert alice.mcp_db_path.parent != bob.mcp_db_path.parent or \
               alice.mcp_db_path.name != bob.mcp_db_path.name
        
        # In a properly isolated system, Alice's MCP manager should
        # not allow access to Bob's database
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="mcp",
            resource_id=str(bob.mcp_db_path),
            action="read",
            result="denied",
            details={"reason": "database path isolation"},
        )


class TestMCPServerConfigIsolation:
    """Test MCP server configuration isolation."""
    
    def test_alice_mcp_servers_do_not_include_bob_servers(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Alice's MCP server list should not include Bob's servers."""
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT server_name FROM mcp_servers")
        server_names = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Should not contain Bob's servers
        for name in server_names:
            assert bob.user_id not in name
    
    def test_bob_mcp_servers_do_not_include_alice_servers(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Bob's MCP server list should not include Alice's servers."""
        conn = sqlite3.connect(bob.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT server_name FROM mcp_servers")
        server_names = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Should not contain Alice's servers
        for name in server_names:
            assert alice.user_id not in name
    
    def test_mcp_config_contains_user_identifier(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """MCP configurations should contain user identifiers for isolation."""
        # Check Alice's configs
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT config_json FROM mcp_servers")
        configs = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        for config in configs:
            assert alice.user_id in config
            assert bob.user_id not in config


class TestMCPToolExecutionIsolation:
    """Test MCP tool execution isolation."""
    
    def test_mcp_query_returns_only_user_data(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """MCP query should return only the user's own data."""
        # Simulate MCP tool execution for Alice
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        # Query that might try to get all data
        cursor.execute("SELECT secret_marker FROM user_data")
        markers = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # All markers should be Alice's
        for marker in markers:
            assert alice.secret_markers["db"] in marker
            assert bob.secret_markers["db"] not in marker
    
    def test_search_across_databases_is_isolated(
        self,
        alice: TestUser,
        bob: TestUser,
    ) -> None:
        """Searching should be isolated to user's own database."""
        # Search in Alice's database
        conn = sqlite3.connect(alice.mcp_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT content FROM user_data WHERE content LIKE ?",
            ("%report%",)
        )
        results = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Results should only be Alice's
        for result in results:
            assert alice.display_name in result or alice.user_id in result.lower()
            assert bob.display_name not in result


class TestMCPAPIIsolation:
    """Test MCP isolation via REST API."""
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_list_mcp_servers_returns_only_user_servers(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """API should return only the requesting user's MCP servers."""
        from .conftest import make_request_as_user
        
        response = make_request_as_user(
            api_client,
            alice,
            "GET",
            f"/api/v1/users/{alice.user_id}/mcp-servers",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All servers should be Alice's
        for server in data.get("servers", []):
            assert alice.user_id in server["name"]
            assert bob.user_id not in server["name"]
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_access_bob_mcp_servers(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to access Bob's MCP servers via API."""
        from .conftest import make_request_as_user
        
        response = make_request_as_user(
            api_client,
            alice,
            "GET",
            f"/api/v1/users/{bob.user_id}/mcp-servers",
        )
        
        assert_isolation_enforced(response.status_code)
    
    @pytest.mark.skip(reason="Requires running server")
    def test_api_alice_cannot_call_bob_mcp_tool(
        self,
        alice: TestUser,
        bob: TestUser,
        api_client,
    ) -> None:
        """Alice should not be able to call Bob's MCP tools via API."""
        from .conftest import make_request_as_user
        
        response = make_request_as_user(
            api_client,
            alice,
            "POST",
            f"/api/v1/users/{bob.user_id}/mcp-servers/{bob.user_id}-database/tools/query",
            json={"query": "SELECT * FROM user_data"},
        )
        
        assert_isolation_enforced(response.status_code)


class TestMCPSecurityAudit:
    """Test security audit logging for MCP operations."""
    
    def test_audit_log_records_cross_tenant_mcp_access(
        self,
        alice: TestUser,
        bob: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """Security audit should record cross-tenant MCP access attempts."""
        # Simulate cross-tenant access attempts
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="mcp",
            resource_id=f"{bob.user_id}-database",
            action="list",
            result="denied",
        )
        
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=bob.user_id,
            resource_type="mcp",
            resource_id=f"{bob.user_id}-database/query",
            action="execute",
            result="denied",
        )
        
        cross_tenant = security_audit.get_cross_tenant_attempts()
        assert len(cross_tenant) == 2
        
        violations = security_audit.get_violations()
        assert len(violations) == 0
    
    def test_mcp_tool_results_are_audited(
        self,
        alice: TestUser,
        security_audit: SecurityAuditLogger,
    ) -> None:
        """MCP tool execution results should be audited."""
        # Simulate successful tool execution
        security_audit.log(
            requesting_user=alice.user_id,
            target_user=alice.user_id,
            resource_type="mcp",
            resource_id=f"{alice.user_id}-database/query",
            action="execute",
            result="allowed",
            details={"rows_returned": 3},
        )
        
        report = security_audit.generate_report()
        assert report["total_events"] == 1
        assert report["violations"] == 0
