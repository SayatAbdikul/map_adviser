"""
Authentication service with password hashing and user management.
Uses SQLAlchemy ORM for database operations.
"""

import bcrypt
from typing import Optional
from sqlalchemy import select
from database import db
from db_models import User
from auth_models import UserCreate, UserResponse


class AuthService:
    """Service for authentication operations using ORM"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hash as string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password to verify
            hashed: Bcrypt hash to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> UserResponse:
        """
        Create a new user with hashed password using ORM.
        
        Args:
            user_data: User registration data
            
        Returns:
            Created user data (without password)
            
        Raises:
            ValueError: If username or email already exists
        """
        async with db.get_session() as session:
            # Check if username already exists
            stmt = select(User).where(User.username == user_data.username.lower())
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValueError("Username already exists")
            
            # Check if email already exists
            stmt = select(User).where(User.email == user_data.email.lower())
            result = await session.execute(stmt)
            existing_email = result.scalar_one_or_none()
            
            if existing_email:
                raise ValueError("Email already exists")
            
            # Hash password
            password_hash = AuthService.hash_password(user_data.password)
            
            # Create new user
            new_user = User(
                username=user_data.username.lower(),
                email=user_data.email.lower(),
                password_hash=password_hash
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            return UserResponse(
                id=str(new_user.id),
                username=new_user.username,
                email=new_user.email,
                created_at=new_user.created_at
            )
    
    @staticmethod
    async def authenticate_user(username: str, password: str) -> Optional[UserResponse]:
        """
        Authenticate user with username and password using ORM.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            User data if authentication successful, None otherwise
        """
        async with db.get_session() as session:
            # Fetch user from database
            stmt = select(User).where(User.username == username.lower())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Verify password
            if not AuthService.verify_password(password, user.password_hash):
                return None
            
            return UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                created_at=user.created_at
            )
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[UserResponse]:
        """
        Get user by ID using ORM.
        
        Args:
            user_id: User UUID
            
        Returns:
            User data if found, None otherwise
        """
        async with db.get_session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            return UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                created_at=user.created_at
            )
