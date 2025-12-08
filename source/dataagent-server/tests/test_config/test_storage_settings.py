"""Tests for storage configuration settings.

**Feature: dataagent-development-specs, Property 43: 存储类型配置有效性**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_server.config.settings import ServerSettings


class TestStorageSettings:
    """Tests for storage-related settings."""
    
    def test_default_session_store_is_memory(self):
        """Test that default session store is memory."""
        settings = ServerSettings()
        assert settings.session_store == "memory"
    
    def test_postgres_store_type_accepted(self):
        """Test that postgres store type is accepted."""
        settings = ServerSettings(session_store="postgres")
        assert settings.session_store == "postgres"
    
    def test_default_postgres_host(self):
        """Test default PostgreSQL host."""
        settings = ServerSettings()
        assert settings.postgres_host == "localhost"
    
    def test_default_postgres_port(self):
        """Test default PostgreSQL port."""
        settings = ServerSettings()
        assert settings.postgres_port == 5432
    
    def test_default_postgres_user(self):
        """Test default PostgreSQL user."""
        settings = ServerSettings()
        assert settings.postgres_user == "root"
    
    def test_default_postgres_database(self):
        """Test default PostgreSQL database."""
        settings = ServerSettings()
        assert settings.postgres_database == "dataagent"
    
    def test_default_postgres_pool_size(self):
        """Test default PostgreSQL pool size."""
        settings = ServerSettings()
        assert settings.postgres_pool_size == 10
    
    def test_default_postgres_max_overflow(self):
        """Test default PostgreSQL max overflow."""
        settings = ServerSettings()
        assert settings.postgres_max_overflow == 20
    
    def test_postgres_url_property(self):
        """Test PostgreSQL URL property generation."""
        settings = ServerSettings(
            postgres_host="db.example.com",
            postgres_port=5433,
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_database="testdb",
        )
        expected = "postgres+aiopostgres://testuser:testpass@db.example.com:5433/testdb"
        assert settings.postgres_url == expected
    
    def test_custom_postgres_settings(self):
        """Test custom PostgreSQL settings."""
        settings = ServerSettings(
            session_store="postgres",
            postgres_host="192.168.1.100",
            postgres_port=5433,
            postgres_user="dataagent_user",
            postgres_password="secret123",
            postgres_database="dataagent_prod",
            postgres_pool_size=20,
            postgres_max_overflow=40,
        )
        
        assert settings.session_store == "postgres"
        assert settings.postgres_host == "192.168.1.100"
        assert settings.postgres_port == 5433
        assert settings.postgres_user == "dataagent_user"
        assert settings.postgres_password == "secret123"
        assert settings.postgres_database == "dataagent_prod"
        assert settings.postgres_pool_size == 20
        assert settings.postgres_max_overflow == 40


class TestStorageSettingsProperties:
    """Property-based tests for storage settings.
    
    **Feature: dataagent-development-specs, Property 43: 存储类型配置有效性**
    """
    
    @settings(max_examples=100)
    @given(
        host=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        port=st.integers(min_value=1, max_value=65535),
        user=st.text(min_size=1, max_size=30).filter(lambda x: x.strip() and ":" not in x and "@" not in x),
        database=st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
    )
    def test_postgres_url_contains_all_components(
        self, host: str, port: int, user: str, database: str
    ):
        """Test that PostgreSQL URL contains all configuration components."""
        settings = ServerSettings(
            postgres_host=host,
            postgres_port=port,
            postgres_user=user,
            postgres_password="testpass",
            postgres_database=database,
        )
        
        url = settings.postgres_url
        assert "postgres+aiopostgres://" in url
        assert user in url
        assert host in url
        assert str(port) in url
        assert database in url
    
    @settings(max_examples=100)
    @given(
        pool_size=st.integers(min_value=1, max_value=100),
        max_overflow=st.integers(min_value=0, max_value=100),
    )
    def test_pool_settings_accepted(self, pool_size: int, max_overflow: int):
        """Test that pool settings are accepted."""
        settings = ServerSettings(
            postgres_pool_size=pool_size,
            postgres_max_overflow=max_overflow,
        )
        
        assert settings.postgres_pool_size == pool_size
        assert settings.postgres_max_overflow == max_overflow
