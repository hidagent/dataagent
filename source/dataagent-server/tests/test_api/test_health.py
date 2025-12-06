"""Tests for health endpoint.

**Feature: dataagent-server, Property 34: 健康检查响应格式**
**Validates: Requirements 22.4**
"""

import pytest
from fastapi.testclient import TestClient

from dataagent_server.main import create_app


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_health_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
    
    def test_health_returns_json(self, client):
        """Test health endpoint returns JSON.
        
        **Feature: dataagent-server, Property 24: API 响应 JSON 格式**
        **Validates: Requirements 16.3**
        """
        response = client.get("/api/v1/health")
        assert response.headers["content-type"] == "application/json"
    
    def test_health_contains_status(self, client):
        """Test health response contains status field."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
    
    def test_health_contains_version(self, client):
        """Test health response contains version field."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
    
    def test_health_contains_uptime(self, client):
        """Test health response contains uptime field."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "uptime" in data
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0
