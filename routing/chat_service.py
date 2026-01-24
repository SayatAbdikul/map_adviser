"""
Chat service for message operations using SQLAlchemy ORM.
"""

from typing import List, Optional
from sqlalchemy import select, func, delete
from database import db
from db_models import Message
from auth_models import MessageCreate, MessageResponse, MessageListResponse


class ChatService:
    """Service for chat/message operations using ORM"""
    
    @staticmethod
    async def save_message(message_data: MessageCreate) -> MessageResponse:
        """
        Save a new message to database using ORM.
        
        Args:
            message_data: Message data to save
            
        Returns:
            Saved message with ID and timestamp
        """
        print(message_data) 
        async with db.get_session() as session:
            # Create new message
            new_message = Message(
                user_id=message_data.user_id if message_data.user_id else None,
                message=message_data.message,
                role=message_data.role.value
            )
            print('new_message', new_message)
            print(session)
            session.add(new_message)
            await session.commit()
            await session.refresh(new_message)
            
            print('norm')
            return MessageResponse(
                id=str(new_message.id),
                user_id=str(new_message.user_id) if new_message.user_id else None,
                message=new_message.message,
                role=new_message.role,
                created_at=new_message.created_at
            )
    
    @staticmethod
    async def get_messages(
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> MessageListResponse:
        """
        Fetch messages with pagination using ORM.
        
        Args:
            limit: Maximum number of messages to return (default: 50)
            offset: Number of messages to skip (default: 0)
            user_id: Optional user ID to filter by user's messages
            
        Returns:
            Paginated list of messages ordered by created_at DESC
        """
        async with db.get_session() as session:
            # Build query
            stmt = select(Message)
            count_stmt = select(func.count(Message.id))
            
            # Apply filter if user_id provided
            if user_id:
                stmt = stmt.where(Message.user_id == user_id)
                count_stmt = count_stmt.where(Message.user_id == user_id)
            
            # Order by created_at DESC and apply pagination
            stmt = stmt.order_by(Message.created_at.desc()).limit(limit).offset(offset)
            
            # Execute queries
            result = await session.execute(stmt)
            messages = result.scalars().all()
            
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0
            
            # Convert to response models
            message_list = [
                MessageResponse(
                    id=str(msg.id),
                    user_id=str(msg.user_id) if msg.user_id else None,
                    message=msg.message,
                    role=msg.role,
                    created_at=msg.created_at
                )
                for msg in messages
            ]
            
            return MessageListResponse(
                messages=message_list,
                total=total,
                limit=limit,
                offset=offset
            )
    
    @staticmethod
    async def get_recent_messages(limit: int = 10) -> List[MessageResponse]:
        """
        Get most recent messages using ORM.
        
        Args:
            limit: Number of recent messages to fetch
            
        Returns:
            List of recent messages
        """
        result = await ChatService.get_messages(limit=limit, offset=0)
        return result.messages
    
    @staticmethod
    async def delete_message(message_id: str) -> bool:
        """
        Delete a message by ID using ORM.
        
        Args:
            message_id: Message UUID to delete
            
        Returns:
            True if deleted, False if not found
        """
        async with db.get_session() as session:
            stmt = delete(Message).where(Message.id == message_id)
            result = await session.execute(stmt)
            await session.commit()
            
            # Check if any rows were deleted
            return result.rowcount > 0
