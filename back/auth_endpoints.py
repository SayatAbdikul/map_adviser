"""
Authentication API endpoints for user registration, login, and token management.
Uses Supabase REST API for user storage.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from auth_service import AuthService
from jwt_handler import create_access_token, decode_token
from supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_scheme = HTTPBearer(auto_error=False)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _build_user_name(user: dict) -> str:
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.get("login") or user.get("email") or "User"


def _coerce_user_id(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Invalid user id format") from exc


def _parse_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_auth_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    return credentials.credentials


class UserRegister(BaseModel):
    """User registration request."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    login: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(default="", max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value:
            raise ValueError("Invalid email format")
        return _normalize_email(value)

    @field_validator("login")
    @classmethod
    def validate_login(cls, value: str) -> str:
        login = value.strip()
        sanitized = login.replace("_", "").replace("-", "").replace(".", "")
        if not sanitized.isalnum():
            raise ValueError("Login must contain only letters, numbers, dots, dashes, and underscores")
        return login


class UserLogin(BaseModel):
    """User login request."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: str) -> str:
        return _normalize_email(value)


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str
    user_id: int
    email: str
    login: str
    name: str


class UserInfo(BaseModel):
    """User information."""

    id: int
    email: str
    name: str
    login: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None


async def _get_user_by_email(email: str) -> Optional[dict]:
    supabase = get_supabase()
    result = await supabase.table("users").select("*").eq("email", email).execute()
    if not result.data:
        return None
    return result.data[0]


async def _get_user_by_login(login: str) -> Optional[dict]:
    supabase = get_supabase()
    result = await supabase.table("users").select("id").eq("login", login).execute()
    if not result.data:
        return None
    return result.data[0]


async def _get_user_by_id(user_id: str) -> Optional[dict]:
    supabase = get_supabase()
    result = await supabase.table("users").select("*").eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0]


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """
    Register a new user.

    Creates user in Supabase with hashed password
    Returns JWT token on success.
    """
    existing_user = await _get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_login = await _get_user_by_login(user_data.login)
    if existing_login:
        raise HTTPException(status_code=400, detail="Login already registered")

    password_hash = AuthService.hash_password(user_data.password)

    supabase = get_supabase()
    try:
        response = await supabase.table("users").insert(
            {
                "email": user_data.email,
                "password": password_hash,
                "login": user_data.login,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
            }
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}") from exc

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = response.data[0]
    user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=500, detail="User ID missing from registration response")

    token = create_access_token(str(user_id), user.get("email", user_data.email))
    name = _build_user_name(user)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=_coerce_user_id(user_id),
        email=user.get("email", user_data.email),
        login=user.get("login", user_data.login),
        name=name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login user with email and password.

    Returns JWT token on successful authentication.
    """
    user = await _get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_password = user.get("password")
    if not stored_password or not AuthService.verify_password(credentials.password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=500, detail="User ID missing from login response")

    token = create_access_token(str(user_id), user.get("email", credentials.email))
    name = _build_user_name(user)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=_coerce_user_id(user_id),
        email=user.get("email", credentials.email),
        login=user.get("login", ""),
        name=name,
    )


@router.post("/verify", response_model=UserInfo)
async def verify_token(token: str = Depends(_parse_bearer_token)):
    """
    Verify JWT token validity.

    Returns user info if token is valid.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await _get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserInfo(
        id=_coerce_user_id(user.get("id")),
        email=user.get("email", ""),
        name=_build_user_name(user),
        login=user.get("login"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        avatar_url=user.get("avatar_url"),
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(token: str = Depends(_parse_bearer_token)):
    """
    Get current user information from JWT token.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await _get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserInfo(
        id=_coerce_user_id(user.get("id")),
        email=user.get("email", ""),
        name=_build_user_name(user),
        login=user.get("login"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        avatar_url=user.get("avatar_url"),
    )
