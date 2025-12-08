"""Password hashing utilities."""

import hashlib
import secrets
from typing import Tuple


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt.
    
    For production, consider using bcrypt or argon2.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password with salt (format: salt$hash)
    """
    salt = secrets.token_hex(16)
    hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hash_value}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash.
    
    Args:
        password: Plain text password
        hashed: Hashed password (format: salt$hash)
        
    Returns:
        True if password matches
    """
    try:
        salt, hash_value = hashed.split("$", 1)
        expected_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return secrets.compare_digest(hash_value, expected_hash)
    except (ValueError, AttributeError):
        return False


def generate_api_key() -> Tuple[str, str]:
    """Generate API key and its hash.
    
    Returns:
        Tuple of (plain_key, hashed_key)
    """
    plain_key = f"da_{secrets.token_urlsafe(32)}"
    hashed_key = hashlib.sha256(plain_key.encode()).hexdigest()
    return plain_key, hashed_key


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify API key against hash.
    
    Args:
        plain_key: Plain API key
        hashed_key: Hashed API key
        
    Returns:
        True if key matches
    """
    expected_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return secrets.compare_digest(expected_hash, hashed_key)
