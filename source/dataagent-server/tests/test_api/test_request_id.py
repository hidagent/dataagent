"""Tests for request ID tracking.

**Feature: dataagent-server, Property 35: 请求 ID 追踪**
**Validates: Requirements 22.5**
"""

import pytest
from fastapi.testclient import TestClient

from dataagent_server.main import create_app
from dataagent_server.ws import ConnectionManager


def create_test_app():
    """Create test app with initialized stores."""
    from dataagent_core.session import MemorySessionStore, MemoryMessageStore
    
    app = create_app()
    app.state.session_store = MemorySessionStore()
    app.state.message_store = MemoryMessageStore()
    app.state.connection_manager = ConnectionManager(max_connections=10)
    return app


class TestRequestIDTracking:
    """Tests for request ID tracking.
    
    **Feature: dataagent-server, Property 35: 请求 ID 追踪**
    **Validates: Requirements 22.5**
    """
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_test_app()
        return TestClient(app)
    
    def test_response_contains_request_id_header(self, client):
        """Test that response contains X-Request-ID header."""
        response = client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers
    
    def test_request_id_is_uuid_format(self, client):
        """Test that request ID is in UUID format."""
        response = client.get("/api/v1/health")
        request_id = response.headers.get("X-Request-ID")
        
        # UUID format: 8-4-4-4-12 hex characters
        parts = request_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12
    
    def test_each_request_gets_unique_id(self, client):
        """Test that each request gets a unique ID."""
        ids = set()
        for _ in range(10):
            response = client.get("/api/v1/health")
            request_id = response.headers.get("X-Request-ID")
            ids.add(request_id)
        
        # All IDs should be unique
        assert len(ids) == 10
    
    def test_client_provided_request_id_is_used(self, client):
        """Test that client-provided X-Request-ID is used."""
        custom_id = "custom-request-id-12345"
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": custom_id}
        )
        
        # Server should echo back the client's request ID
        assert response.headers.get("X-Request-ID") == custom_id
    
    def test_request_id_on_error_response(self, client):
        """Test that error responses also contain request ID."""
        response = client.get("/api/v1/sessions/nonexistent")
        assert "X-Request-ID" in response.headers
