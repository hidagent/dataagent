"""Server configuration settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """Server configuration loaded from environment variables.
    
    All settings can be configured via environment variables with the
    DATAAGENT_ prefix (e.g., DATAAGENT_HOST, DATAAGENT_PORT).
    """
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Authentication
    api_keys: list[str] = []
    auth_disabled: bool = False
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    # Session
    session_timeout: int = 3600
    
    # Concurrency
    max_connections: int = 200
    
    # HITL
    hitl_timeout: int = 300
    
    # Session storage configuration
    session_store: Literal["memory", "mysql"] = "memory"
    
    # MySQL configuration
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "dataagent"
    mysql_pool_size: int = 10
    mysql_max_overflow: int = 20
    
    # MCP configuration
    mcp_max_connections_per_user: int = 10
    mcp_max_total_connections: int = 100
    
    model_config = SettingsConfigDict(
        env_prefix="DATAAGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    @property
    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return not self.auth_disabled and len(self.api_keys) > 0
    
    @property
    def mysql_url(self) -> str:
        """Get MySQL connection URL for async driver."""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


@lru_cache
def get_settings() -> ServerSettings:
    """Get cached server settings instance."""
    return ServerSettings()
