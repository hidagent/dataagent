"""Authentication module."""

from dataagent_server.auth.api_key import APIKeyAuth, api_key_auth, get_api_key
from dataagent_server.auth.jwt import (
    create_access_token,
    decode_access_token,
    get_token_expiration_seconds,
    TokenPayload,
    TokenResponse,
)
from dataagent_server.auth.password import (
    hash_password,
    verify_password,
    generate_api_key,
    verify_api_key,
)
from dataagent_server.auth.middleware import (
    get_current_user_from_token,
    get_optional_user_from_token,
    require_user_match,
)

__all__ = [
    # API Key auth
    "APIKeyAuth",
    "api_key_auth",
    "get_api_key",
    # JWT
    "create_access_token",
    "decode_access_token",
    "get_token_expiration_seconds",
    "TokenPayload",
    "TokenResponse",
    # Password
    "hash_password",
    "verify_password",
    "generate_api_key",
    "verify_api_key",
    # Middleware
    "get_current_user_from_token",
    "get_optional_user_from_token",
    "require_user_match",
]
