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
    
    def test_mysql_store_type_accepted(self):
        """Test that mysql store type is accepted."""
        settings = ServerSettings(session_store="mysql")
        assert settings.session_store == "mysql"
    
    def test_default_mysql_host(self):
        """Test default MySQL host."""
        settings = ServerSettings()
        assert settings.mysql_host == "localhost"
    
    def test_default_mysql_port(self):
        """Test default MySQL port."""
        settings = ServerSettings()
        assert settings.mysql_port == 3306
    
    def test_default_mysql_user(self):
        """Test default MySQL user."""
        settings = ServerSettings()
        assert settings.mysql_user == "root"
    
    def test_default_mysql_database(self):
        """Test default MySQL database."""
        settings = ServerSettings()
        assert settings.mysql_database == "dataagent"
    
    def test_default_mysql_pool_size(self):
        """Test default MySQL pool size."""
        settings = ServerSettings()
        assert settings.mysql_pool_size == 10
    
    def test_default_mysql_max_overflow(self):
        """Test default MySQL max overflow."""
        settings = ServerSettings()
        assert settings.mysql_max_overflow == 20
    
    def test_mysql_url_property(self):
        """Test MySQL URL property generation."""
        settings = ServerSettings(
            mysql_host="db.example.com",
            mysql_port=3307,
            mysql_user="testuser",
            mysql_password="testpass",
            mysql_database="testdb",
        )
        expected = "mysql+aiomysql://testuser:testpass@db.example.com:3307/testdb"
        assert settings.mysql_url == expected
    
    def test_custom_mysql_settings(self):
        """Test custom MySQL settings."""
        settings = ServerSettings(
            session_store="mysql",
            mysql_host="192.168.1.100",
            mysql_port=3307,
            mysql_user="dataagent_user",
            mysql_password="secret123",
            mysql_database="dataagent_prod",
            mysql_pool_size=20,
            mysql_max_overflow=40,
        )
        
        assert settings.session_store == "mysql"
        assert settings.mysql_host == "192.168.1.100"
        assert settings.mysql_port == 3307
        assert settings.mysql_user == "dataagent_user"
        assert settings.mysql_password == "secret123"
        assert settings.mysql_database == "dataagent_prod"
        assert settings.mysql_pool_size == 20
        assert settings.mysql_max_overflow == 40


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
    def test_mysql_url_contains_all_components(
        self, host: str, port: int, user: str, database: str
    ):
        """Test that MySQL URL contains all configuration components."""
        settings = ServerSettings(
            mysql_host=host,
            mysql_port=port,
            mysql_user=user,
            mysql_password="testpass",
            mysql_database=database,
        )
        
        url = settings.mysql_url
        assert "mysql+aiomysql://" in url
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
            mysql_pool_size=pool_size,
            mysql_max_overflow=max_overflow,
        )
        
        assert settings.mysql_pool_size == pool_size
        assert settings.mysql_max_overflow == max_overflow
