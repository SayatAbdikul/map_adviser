"""
Security utilities for password hashing and verification
- Uses bcrypt for secure password hashing
- Constant-time comparison to prevent timing attacks
"""
import os
import hashlib
import secrets
from typing import Tuple

# Try to use bcrypt if available, fallback to PBKDF2
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


def hash_password(password: str) -> str:
    """
    Hash password securely.
    Uses bcrypt if available, otherwise PBKDF2.
    """
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        # Fallback to PBKDF2
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return f"pbkdf2:{salt}:{hash_obj.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash.
    Uses constant-time comparison to prevent timing attacks.
    """
    if BCRYPT_AVAILABLE and not hashed.startswith('pbkdf2:'):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    else:
        # PBKDF2 verification
        if not hashed.startswith('pbkdf2:'):
            return False
        try:
            _, salt, stored_hash = hashed.split(':')
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return secrets.compare_digest(hash_obj.hex(), stored_hash)
        except (ValueError, AttributeError):
            return False


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)
