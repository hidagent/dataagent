"""DataAgent Server - FastAPI-based REST API and WebSocket service."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("dataagent-server")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback for development
