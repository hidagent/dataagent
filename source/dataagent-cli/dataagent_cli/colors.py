"""Color scheme and constants for DataAgent CLI."""

# Color scheme
COLORS = {
    "primary": "#10b981",
    "dim": "#6b7280",
    "user": "#ffffff",
    "agent": "#10b981",
    "thinking": "#34d399",
    "tool": "#fbbf24",
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
    "quit": "Exit the CLI",
    "exit": "Exit the CLI",
}

# Maximum argument length for display
MAX_ARG_LENGTH = 150
