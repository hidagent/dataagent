"""Tests for server settings.

**Feature: dataagent-server, Property 32: 配置默认值**
**Validates: Requirements 20.4**
"""

import os

import pytest
from hypothesis import given, settings as hypothesis_settings
from hypothesis import strategies as st

from dataagent_server.config import ServerSettings


class TestServerSettingsDefaults:
    """Test that ServerSettings provides reasonable defaults."""
    
    def test_default_host(self):
        """Test default host is 0.0.0.0."""
        settings = ServerSettings()
        assert settings.host == "0.0.0.0"
    
    def test_default_port(self):
        """Test default port is 8000."""
        settings = ServerSettings()
        assert settings.port == 8000
    
    def test_default_workers(self):
        """Test default workers is 1."""
        settings = ServerSettings()
        assert settings.workers == 1
    
    def test_default_api_keys_empty(self):
        """Test default api_keys is empty list."""
        settings = ServerSettings()
        assert settings.api_keys == []
    
    def test_default_auth_disabled(self):
        """Test default auth_disabled is False."""
        settings = ServerSettings()
        assert settings.auth_disabled is False
    
    def test_default_cors_origins(self):
        """Test default cors_origins allows all."""
        settings = ServerSettings()
        assert settings.cors_origins == ["*"]
    
    def test_default_session_timeout(self):
        """Test default session_timeout is 3600."""
        settings = ServerSettings()
        assert settings.session_timeout == 3600
    
    def test_default_max_connections(self):
        """Test default max_connections is 200."""
        settings = ServerSettings()
        assert settings.max_connections == 200
    
    def test_default_hitl_timeout(self):
        """Test default hitl_timeout is 300."""
        settings = ServerSettings()
        assert settings.hitl_timeout == 300


class TestServerSettingsProperties:
    """Property-based tests for ServerSettings.
    
    **Feature: dataagent-server, Property 32: 配置默认值**
    **Validates: Requirements 20.4**
    """
    
    @hypothesis_settings(max_examples=100)
    @given(
        host=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        port=st.integers(min_value=1, max_value=65535),
        workers=st.integers(min_value=1, max_value=32),
        max_connections=st.integers(min_value=1, max_value=10000),
    )
    def test_settings_accept_valid_values(
        self,
        host: str,
        port: int,
        workers: int,
        max_connections: int,
    ):
        """Test that settings accept valid configuration values."""
        settings = ServerSettings(
            host=host,
            port=port,
            workers=workers,
            max_connections=max_connections,
        )
        assert settings.host == host
        assert settings.port == port
        assert settings.workers == workers
        assert settings.max_connections == max_connections
    
    @hypothesis_settings(max_examples=100)
    @given(api_keys=st.lists(st.text(min_size=1, max_size=50), max_size=10))
    def test_settings_accept_api_keys_list(self, api_keys: list[str]):
        """Test that settings accept list of API keys."""
        settings = ServerSettings(api_keys=api_keys)
        assert settings.api_keys == api_keys
    
    def test_is_auth_enabled_with_keys(self):
        """Test is_auth_enabled returns True when keys configured."""
        settings = ServerSettings(api_keys=["key1"], auth_disabled=False)
        assert settings.is_auth_enabled is True
    
    def test_is_auth_enabled_disabled(self):
        """Test is_auth_enabled returns False when disabled."""
        settings = ServerSettings(api_keys=["key1"], auth_disabled=True)
        assert settings.is_auth_enabled is False
    
    def test_is_auth_enabled_no_keys(self):
        """Test is_auth_enabled returns False when no keys."""
        settings = ServerSettings(api_keys=[], auth_disabled=False)
        assert settings.is_auth_enabled is False
