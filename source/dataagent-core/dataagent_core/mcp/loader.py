"""MCP configuration loader for CLI mode."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from dataagent_core.mcp.config import MCPConfig

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class MCPConfigLoader:
    """Loader for MCP configuration in CLI mode.
    
    Loads MCP configuration from:
    1. Command line argument (--mcp-config)
    2. User config: ~/.deepagents/{assistant_id}/mcp.json
    3. Project config: .deepagents/mcp.json
    """
    
    def __init__(
        self,
        assistant_id: str | None = None,
        config_path: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        """Initialize the loader.
        
        Args:
            assistant_id: The assistant ID for user-level config.
            config_path: Explicit config path (overrides auto-detection).
            project_root: Project root for project-level config.
        """
        self.assistant_id = assistant_id
        self.config_path = config_path
        self.project_root = project_root
        self._config: MCPConfig | None = None
        self._tools: list[BaseTool] | None = None
    
    def get_user_config_path(self) -> Path | None:
        """Get the user-level MCP config path."""
        if not self.assistant_id:
            return None
        return Path.home() / ".deepagents" / self.assistant_id / "mcp.json"
    
    def get_project_config_path(self) -> Path | None:
        """Get the project-level MCP config path."""
        if not self.project_root:
            return None
        return self.project_root / ".deepagents" / "mcp.json"
    
    def find_config_path(self) -> Path | None:
        """Find the MCP config path to use.
        
        Priority:
        1. Explicit config_path
        2. User config (~/.deepagents/{assistant_id}/mcp.json)
        3. Project config (.deepagents/mcp.json)
        """
        if self.config_path and self.config_path.exists():
            return self.config_path
        
        user_path = self.get_user_config_path()
        if user_path and user_path.exists():
            return user_path
        
        project_path = self.get_project_config_path()
        if project_path and project_path.exists():
            return project_path
        
        return None
    
    def load_config(self) -> MCPConfig:
        """Load MCP configuration from file.
        
        Returns:
            MCPConfig instance (empty if no config found).
        """
        if self._config is not None:
            return self._config
        
        config_path = self.find_config_path()
        if config_path:
            logger.info(f"Loading MCP config from: {config_path}")
            self._config = MCPConfig.from_json_file(config_path)
        else:
            logger.debug("No MCP config found, using empty config")
            self._config = MCPConfig()
        
        return self._config
    
    def reload_config(self) -> MCPConfig:
        """Reload MCP configuration from file."""
        self._config = None
        self._tools = None
        return self.load_config()
    
    async def get_tools(self) -> list[BaseTool]:
        """Get MCP tools from configured servers.
        
        Uses langchain-mcp-adapters to connect to MCP servers
        and retrieve their tools.
        
        Returns:
            List of LangChain tools from MCP servers.
        """
        if self._tools is not None:
            return self._tools
        
        config = self.load_config()
        enabled_servers = config.get_enabled_servers()
        
        if not enabled_servers:
            logger.debug("No enabled MCP servers configured")
            self._tools = []
            return self._tools
        
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            logger.warning(
                "langchain-mcp-adapters not installed. "
                "Install with: pip install langchain-mcp-adapters"
            )
            self._tools = []
            return self._tools
        
        tools: list[BaseTool] = []
        mcp_config = config.to_mcp_client_config()
        
        try:
            async with MultiServerMCPClient(mcp_config) as client:
                tools = client.get_tools()
                logger.info(f"Loaded {len(tools)} tools from MCP servers")
        except Exception as e:
            logger.warning(f"Failed to connect to MCP servers: {e}")
            # Don't block main flow on MCP connection failure
        
        self._tools = tools
        return self._tools
    
    def get_auto_approve_tools(self) -> set[str]:
        """Get set of tool names that should be auto-approved."""
        config = self.load_config()
        auto_approve = set()
        for server in config.get_enabled_servers().values():
            auto_approve.update(server.auto_approve)
        return auto_approve
