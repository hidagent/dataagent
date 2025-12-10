"""API v1 routes."""

from dataagent_server.api.v1 import (
    auth,
    chat,
    chat_stream,
    health,
    sessions,
    mcp,
    users,
    user_profiles,
    rules,
    assistants,
    workspaces,
)

__all__ = [
    "auth",
    "chat",
    "chat_stream",
    "health",
    "sessions",
    "mcp",
    "users",
    "user_profiles",
    "rules",
    "assistants",
    "workspaces",
]
