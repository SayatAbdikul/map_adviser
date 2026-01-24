"""
Database connection module using SQLAlchemy ORM.
Provides async session management and database utilities.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from db_models import Base

load_dotenv()


class Database:
    """Database connection and session manager"""
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
    
    def get_connection_string(self) -> str:
        """
        Build database connection string from environment variables.
        Host details are read from environment to avoid hardcoding.
        
        Returns:
            Connection string for async PostgreSQL
        """
        password = os.getenv('SUPABASE_DB_PASSWORD')
        db_host = os.getenv('SUPABASE_DB_HOST')
        db_port = os.getenv('SUPABASE_DB_PORT')
        db_name = os.getenv('SUPABASE_DB_NAME')
        db_user = os.getenv('SUPABASE_DB_USER')
        
        if not password:
            raise ValueError(
                "SUPABASE_DB_PASSWORD environment variable is not set. "
                "Please add it to your .env file."
            )
        
        # SQLAlchemy async connection string
        connection_string = (
            f"postgresql+asyncpg://{db_user}:{password}@"
            f"{db_host}:{db_port}/{db_name}"
        )
        
        return connection_string
    
    async def connect(self):
        """
        Create async engine and session factory.
        """
        if self.engine is not None:
            return
        
        connection_string = self.get_connection_string()
        
        try:
            self.engine = create_async_engine(
                connection_string,
                echo=False,  # Set to True for SQL query logging
                pool_pre_ping=True,  # Verify connections before using
                pool_size=5,
                max_overflow=10,
            )
            
            # Create session factory
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            print("✓ Database connection established successfully")
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close database engine"""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.async_session_maker = None
            print("✓ Database connection closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session as an async context manager.
        
        Usage:
            async with db.get_session() as session:
                result = await session.execute(query)
        
        Yields:
            AsyncSession instance
        """
        if self.async_session_maker is None:
            raise RuntimeError("Database is not initialized. Call connect() first.")
        
        async with self.async_session_maker() as session:
            try:
                print('norm')
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Create all tables (for development/testing)"""
        if self.engine is None:
            raise RuntimeError("Database engine is not initialized.")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


# Global database instance
db = Database()
