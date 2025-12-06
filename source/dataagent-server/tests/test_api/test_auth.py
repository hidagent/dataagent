"""Tests for API Key authentication.

**Feature: dataagent-server, Property 30: API Key 认证有效性**
**Feature: dataagent-server, Property 31: 多 API Key 支持**
**Validates: Requirements 19.3, 19.4**
"""

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_server.auth import APIKeyAuth, get_api_key


class TestAPIKeyAuth:
    """Tests for API Key authentication."""
    
    @pytest.fixture
    def app_with_auth(self):
        """Create app with auth enabled."""
        app = FastAPI()
        auth = APIKeyAuth(api_keys=["valid-key-1", "valid-key-2"], disabled=False)
        
        @app.get("/protected")
        async def protected(api_key: str | None = Depends(auth)):
            return {"api_key": api_key}
        
        return app
    
    @pytest.fixture
    def app_no_auth(self):
        """Create app with auth disabled."""
        app = FastAPI()
        auth = APIKeyAuth(api_keys=["valid-key"], disabled=True)
        
        @app.get("/protected")
        async def protected(api_key: str | None = Depends(auth)):
            return {"api_key": api_key}
        
        return app
    
    def test_missing_api_key_returns_401(self, app_with_auth):
        """Test that missing API key returns 401.
        
        **Feature: dataagent-server, Property 30: API Key 认证有效性**
        **Validates: Requirements 19.3**
        """
        client = TestClient(app_with_auth)
        response = client.get("/protected")
        assert response.status_code == 401
    
    def test_invalid_api_key_returns_401(self, app_with_auth):
        """Test that invalid API key returns 401.
        
        **Feature: dataagent-server, Property 30: API Key 认证有效性**
        **Validates: Requirements 19.3**
        """
        client = TestClient(app_with_auth)
        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401
    
    def test_valid_api_key_returns_200(self, app_with_auth):
        """Test that valid API key returns 200."""
        client = TestClient(app_with_auth)
        response = client.get("/protected", headers={"X-API-Key": "valid-key-1"})
        assert response.status_code == 200
    
    def test_multiple_valid_keys(self, app_with_auth):
        """Test that multiple API keys are supported.
        
        **Feature: dataagent-server, Property 31: 多 API Key 支持**
        **Validates: Requirements 19.4**
        """
        client = TestClient(app_with_auth)
        
        # First key works
        response1 = client.get("/protected", headers={"X-API-Key": "valid-key-1"})
        assert response1.status_code == 200
        
        # Second key also works
        response2 = client.get("/protected", headers={"X-API-Key": "valid-key-2"})
        assert response2.status_code == 200
    
    def test_auth_disabled_allows_all(self, app_no_auth):
        """Test that disabled auth allows all requests."""
        client = TestClient(app_no_auth)
        
        # No key works
        response = client.get("/protected")
        assert response.status_code == 200
        
        # Invalid key also works
        response = client.get("/protected", headers={"X-API-Key": "any-key"})
        assert response.status_code == 200


class TestAPIKeyAuthProperties:
    """Property-based tests for API Key authentication."""
    
    # Use ASCII-safe alphabet for HTTP headers
    ASCII_SAFE = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    
    @settings(max_examples=100)
    @given(
        valid_keys=st.lists(
            st.text(alphabet=ASCII_SAFE, min_size=1, max_size=50),
            min_size=1,
            max_size=10,
        ),
    )
    def test_all_configured_keys_are_valid(self, valid_keys: list[str]):
        """Test that all configured keys are accepted.
        
        **Feature: dataagent-server, Property 31: 多 API Key 支持**
        **Validates: Requirements 19.4**
        """
        # Filter out empty strings after generation
        valid_keys = [k for k in valid_keys if k.strip()]
        if not valid_keys:
            return
        
        app = FastAPI()
        auth = APIKeyAuth(api_keys=valid_keys, disabled=False)
        
        @app.get("/protected")
        async def protected(api_key: str | None = Depends(auth)):
            return {"api_key": api_key}
        
        client = TestClient(app)
        
        for key in valid_keys:
            response = client.get("/protected", headers={"X-API-Key": key})
            assert response.status_code == 200
    
    @settings(max_examples=100)
    @given(
        valid_keys=st.lists(
            st.text(alphabet=ASCII_SAFE, min_size=1, max_size=50),
            min_size=1,
            max_size=5,
        ),
        invalid_key=st.text(alphabet=ASCII_SAFE, min_size=1, max_size=50),
    )
    def test_invalid_keys_are_rejected(
        self,
        valid_keys: list[str],
        invalid_key: str,
    ):
        """Test that invalid keys are rejected.
        
        **Feature: dataagent-server, Property 30: API Key 认证有效性**
        **Validates: Requirements 19.3**
        """
        # Filter out empty strings
        valid_keys = [k for k in valid_keys if k.strip()]
        if not valid_keys or not invalid_key.strip():
            return
        
        # Skip if invalid_key happens to be in valid_keys
        if invalid_key in valid_keys:
            return
        
        app = FastAPI()
        auth = APIKeyAuth(api_keys=valid_keys, disabled=False)
        
        @app.get("/protected")
        async def protected(api_key: str | None = Depends(auth)):
            return {"api_key": api_key}
        
        client = TestClient(app)
        response = client.get("/protected", headers={"X-API-Key": invalid_key})
        assert response.status_code == 401
