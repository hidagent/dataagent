"""Server configuration settings."""

from functools import lru_cache
from pathlib import Path
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
    auth_disabled: bool = True  # Disabled by default for development
    
    # Default user for development mode
    default_user: str = "dataagent"
    default_password: str = "dataagent"
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    # Session
    session_timeout: int = 3600
    
    # Concurrency
    max_connections: int = 200
    
    # HITL
    hitl_timeout: int = 300
    
    # Session storage configuration: memory, sqlite, postgres
    session_store: Literal["memory", "sqlite", "postgres"] = "sqlite"
    
    # SQLite configuration (default for development)
    sqlite_path: str = str(Path.home() / ".dataagent" / "dataagent.db")
    
    # PostgreSQL configuration (for production)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_database: str = "dataagent"
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 20
    
    # MCP configuration
    mcp_max_connections_per_user: int = 10
    mcp_max_total_connections: int = 100
    
    # Workspace configuration (multi-tenant file isolation)
    workspace_base_path: str = "/var/dataagent/workspaces"
    workspace_default_max_size_bytes: int = 1073741824  # 1GB
    workspace_default_max_files: int = 10000
    
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
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL for async driver."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache
def get_settings() -> ServerSettings:
    """Get cached server settings instance."""
    return ServerSettings()
