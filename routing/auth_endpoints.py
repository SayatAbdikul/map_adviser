"""
Authentication API endpoints for user registration, login, and token management
Integrates with Supabase for user management
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from pydantic import BaseModel
from supabase_client import get_supabase
from jwt_handler import create_access_token, decode_token
from auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================================
# Pydantic Models
# ============================================================================

class UserRegister(BaseModel):
    """User registration request"""
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    """User login request"""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str
    user_id: int
    email: str
    name: str


class UserInfo(BaseModel):
    """User information"""
    id: int
    email: str
    name: str
    avatar_url: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """
    Register a new user
    
    Creates user in Supabase with hashed password
    Returns JWT token on success
    """
    supabase = get_supabase()
    
    # Check if user already exists
    try:
        response = supabase.table("users").select("id").eq("email", user_data.email).execute()
        if response.data:
            raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as e:
        if "404" not in str(e):
            raise HTTPException(status_code=500, detail="Database error")
    
    # Hash password
    password_hash = AuthService.hash_password(user_data.password)
    
    # Create user in Supabase
    try:
        response = supabase.table("users").insert({
            "email": user_data.email,
            "password_hash": password_hash,
            "name": user_data.name,
        }).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        user = response.data[0]
        
        # Create JWT token
        token = create_access_token(user["id"], user["email"])
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user["id"],
            email=user["email"],
            name=user["name"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login user with email and password
    
    Returns JWT token on successful authentication
    """
    supabase = get_supabase()
    
    # Get user from Supabase
    try:
        response = supabase.table("users").select("*").eq("email", credentials.email).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = response.data[0]
        
        # Verify password
        if not AuthService.verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create JWT token
        token = create_access_token(user["id"], user["email"])
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user["id"],
            email=user["email"],
            name=user["name"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify JWT token validity
    
    Returns user info if token is valid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    # Decode token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user from Supabase
    supabase = get_supabase()
    try:
        response = supabase.table("users").select("*").eq("id", int(payload["sub"])).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user = response.data[0]
        
        return UserInfo(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/me", response_model=UserInfo)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get current user information from JWT token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    supabase = get_supabase()
    try:
        response = supabase.table("users").select("*").eq("id", int(payload["sub"])).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user = response.data[0]
        
        return UserInfo(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            avatar_url=user.get("avatar_url")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
