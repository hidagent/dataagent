"""DataAgent Harbor - Testing and evaluation framework for DataAgent Server."""

from importlib.metadata import version, PackageNotFoundError

from dataagent_harbor.client import DataAgentClient
from dataagent_harbor.runner import BenchmarkRunner
from dataagent_harbor.models import (
    Question,
    QuestionSet,
    QuestionResult,
    BenchmarkReport,
)
from dataagent_harbor.tracing import TracingManager

try:
    __version__ = version("dataagent-harbor")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback for development

__all__ = [
    "DataAgentClient",
    "BenchmarkRunner",
    "Question",
    "QuestionSet",
    "QuestionResult",
    "BenchmarkReport",
    "TracingManager",
]
