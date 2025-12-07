"""DataAgent CLI - Command-line interface for DataAgent platform."""

from importlib.metadata import version, PackageNotFoundError

from dataagent_cli.main import cli_main

try:
    __version__ = version("dataagent-cli")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback for development

__all__ = ["cli_main", "__version__"]
