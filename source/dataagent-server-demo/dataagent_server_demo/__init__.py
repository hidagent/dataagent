"""DataAgent Server Demo - Streamlit UI for testing."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("dataagent-server-demo")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback for development
