"""
JWT Token management module
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-min-32-chars-long")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def create_access_token(user_id: int, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        user_id: User's ID in database
        email: User's email
        expires_delta: Custom expiration time (default: 24 hours)
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": str(user_id),  # subject (user_id)
        "email": email,
        "iat": datetime.utcnow(),  # issued at
        "exp": expire,  # expiration
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


def extract_user_from_token(token: str) -> Optional[dict]:
    """Extract user info from a valid token"""
    payload = decode_token(token)
    if payload:
        return {
            "user_id": int(payload.get("sub")),
            "email": payload.get("email"),
        }
    return None
