"""
JWT token management utilities.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is required")
    return secret


def _get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _get_jwt_expiration_hours() -> int:
    try:
        return int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    except ValueError:
        return 24


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User identifier in database
        email: User's email
        expires_delta: Custom expiration time (default: JWT_EXPIRATION_HOURS)

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=_get_jwt_expiration_hours())

    issued_at = datetime.now(timezone.utc)
    expire = issued_at + expires_delta

    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def extract_user_from_token(token: str) -> Optional[dict]:
    """Extract user info from a valid token."""
    payload = decode_token(token)
    if not payload:
        return None
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
    }
