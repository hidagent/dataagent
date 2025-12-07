"""Color scheme and constants for DataAgent CLI."""

# Color scheme
# Note: "prompt" uses a color that works on both light and dark backgrounds
COLORS = {
    "primary": "#10b981",      # Emerald green - main brand color
    "dim": "#6b7280",          # Gray - secondary text
    "user": "#ffffff",         # White - user message text (for dark bg)
    "agent": "#10b981",        # Emerald green - agent responses
    "thinking": "#34d399",     # Light green - thinking indicator
    "tool": "#fbbf24",         # Amber - tool calls
    "prompt": "#10b981",       # Emerald green - input prompt (works on light/dark)
}

# ASCII art banner
DATAAGENT_ASCII = """
╔═══════════════════════════════════════════════════╗
║                                                   ║
║     ██████╗   █████╗ ████████╗ █████╗             ║
║     ██╔══██╗ ██╔══██╗╚══██╔══╝██╔══██╗            ║
║     ██║  ██║ ███████║   ██║   ███████║            ║
║     ██║  ██║ ██╔══██║   ██║   ██╔══██║            ║
║     ██████╔╝ ██║  ██║   ██║   ██║  ██║            ║
║     ╚═════╝  ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝            ║
║                                                   ║
║      █████╗  ██████╗ ███████╗███╗   ██╗████████╗  ║
║     ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝  ║
║     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║     ║
║     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║     ║
║     ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║     ║
║     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝     ║
║                                                   ║
║           AI-Powered Data Assistant               ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
"""

# Interactive commands
COMMANDS = {
    "clear": "Clear screen and reset conversation",
    "help": "Show help information",
    "tokens": "Show token usage for current session",
    "mcp": "Show MCP servers",
    "mcp reload": "Reload MCP configuration",
    "rules": "List all rules",
    "rules list": "List all rules grouped by scope",
    "rules show": "Show full content of a rule",
    "rules create": "Create a new rule",
    "rules delete": "Delete a rule",
    "rules validate": "Validate all rule files",
    "rules reload": "Reload rules from disk",
    "rules debug": "Enable/disable debug mode",
    "rules conflicts": "Show rule conflicts",
    "rules help": "Show rules command help",
    "quit": "Exit the CLI",
    "exit": "Exit the CLI",
}

# Maximum argument length for display
MAX_ARG_LENGTH = 150
