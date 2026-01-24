"""
Pydantic models for authentication and chat functionality.
Provides request/response schemas with validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message sender role"""
    USER = "user"
    BOT = "bot"


# ============================================================================
# Auth Models
# ============================================================================

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('username')
    def validate_username(cls, v):
        """Username validation - alphanumeric and underscore only"""
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v.lower()


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user data returned to client (no password)"""
    id: str
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Message/Chat Models
# ============================================================================

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    message: str = Field(..., min_length=1, max_length=10000)
    role: MessageRole
    user_id: Optional[str] = None
    
    @validator('message')
    def validate_message(cls, v):
        """Ensure message is not empty after stripping whitespace"""
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v, values):
        """Validate user_id is provided for user messages"""
        if values.get('role') == MessageRole.USER and not v:
            # For user messages, user_id is optional but recommended
            # You can make it required by raising an error here
            pass
        return v


class MessageResponse(BaseModel):
    """Schema for message data returned to client"""
    id: str
    user_id: Optional[str]
    message: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Schema for paginated message list"""
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int
