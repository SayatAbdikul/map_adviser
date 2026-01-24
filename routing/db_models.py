"""
SQLAlchemy ORM models for database tables.
"""

from sqlalchemy import Column, String, Text, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()


class MessageRoleEnum(str, enum.Enum):
    """Message role enumeration"""
    USER = "user"
    BOT = "bot"


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to messages
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_created_at', 'created_at'),
    )


class Message(Base):
    """Message model for chat"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    message = Column(Text, nullable=False)
    role = Column(Enum(MessageRoleEnum, name='message_role'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationship to user
    user = relationship("User", back_populates="messages")
    
    __table_args__ = (
        Index('idx_messages_created_at', 'created_at'),
        Index('idx_messages_user_id', 'user_id'),
        Index('idx_messages_role', 'role'),
        Index('idx_messages_user_created', 'user_id', 'created_at'),
    )
