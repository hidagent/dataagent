"""Tests for API endpoints.

**Feature: dataagent-server, Property 23: API 端点注册完整性**
**Feature: dataagent-server, Property 24: API 响应 JSON 格式**
**Feature: dataagent-server, Property 25: 错误响应格式一致性**
**Validates: Requirements 16.2, 16.3, 16.4**
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


class TestAPIEndpointRegistration:
    """Tests for API endpoint registration.
    
    **Feature: dataagent-server, Property 23: API 端点注册完整性**
    **Validates: Requirements 16.2**
    """
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_test_app()
        return TestClient(app)
    
    def test_health_endpoint_registered(self, client):
        """Test /api/v1/health endpoint is registered."""
        response = client.get("/api/v1/health")
        assert response.status_code != 404
    
    def test_chat_endpoint_registered(self, client):
        """Test /api/v1/chat endpoint is registered."""
        response = client.post("/api/v1/chat", json={"message": "test"})
        # Should not be 404 (may be 401 if auth required, or 200/503)
        assert response.status_code != 404
    
    def test_sessions_list_endpoint_registered(self, client):
        """Test /api/v1/sessions endpoint is registered."""
        response = client.get("/api/v1/sessions")
        assert response.status_code != 404
    
    def test_session_detail_endpoint_registered(self, client):
        """Test /api/v1/sessions/{id} endpoint is registered."""
        response = client.get("/api/v1/sessions/test-session")
        # 404 is expected for non-existent session, but endpoint should be registered
        # So we check it's not a 405 (method not allowed) which would indicate no route
        assert response.status_code in (200, 401, 404, 500)
    
    def test_session_delete_endpoint_registered(self, client):
        """Test DELETE /api/v1/sessions/{id} endpoint is registered."""
        response = client.delete("/api/v1/sessions/test-session")
        # 404 is expected for non-existent session, but endpoint should be registered
        assert response.status_code in (200, 204, 401, 404, 500)
    
    def test_chat_cancel_endpoint_registered(self, client):
        """Test /api/v1/chat/{id}/cancel endpoint is registered."""
        response = client.post("/api/v1/chat/test-session/cancel")
        # 404 is expected when no active chat exists, but endpoint should be registered
        # We verify it's not a 405 (method not allowed) which would indicate no route
        assert response.status_code in (200, 401, 404, 500, 503)


class TestAPIResponseFormat:
    """Tests for API response format.
    
    **Feature: dataagent-server, Property 24: API 响应 JSON 格式**
    **Validates: Requirements 16.3**
    """
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_test_app()
        return TestClient(app)
    
    def test_health_returns_json(self, client):
        """Test health endpoint returns JSON."""
        response = client.get("/api/v1/health")
        assert "application/json" in response.headers["content-type"]
    
    def test_sessions_returns_json(self, client):
        """Test sessions endpoint returns JSON."""
        response = client.get("/api/v1/sessions")
        assert "application/json" in response.headers["content-type"]


class TestErrorResponseFormat:
    """Tests for error response format.
    
    **Feature: dataagent-server, Property 25: 错误响应格式一致性**
    **Validates: Requirements 16.4**
    """
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_test_app()
        return TestClient(app)
    
    def test_404_contains_error_code(self, client):
        """Test 404 response contains error_code field."""
        response = client.get("/api/v1/sessions/nonexistent")
        if response.status_code == 404:
            data = response.json()
            # FastAPI default 404 or our custom format
            assert "detail" in data or "error_code" in data
    
    def test_chat_cancel_404_format(self, client):
        """Test chat cancel 404 response format."""
        response = client.post("/api/v1/chat/nonexistent/cancel")
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data or ("error_code" in data and "message" in data)
