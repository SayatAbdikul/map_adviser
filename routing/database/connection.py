"""
Secure PostgreSQL Database Connection
- Uses connection pooling
- Environment variables for credentials
- No hardcoded secrets
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from typing import Generator

load_dotenv()

# Load from environment variables (NEVER hardcode credentials)
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "map_adviser"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Build connection URL safely (password is URL-encoded automatically by SQLAlchemy)
DATABASE_URL = (
    f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
    f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
)

# Create engine with connection pooling and security settings
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,              # Number of connections to keep open
    max_overflow=10,          # Additional connections when pool is full
    pool_timeout=30,          # Seconds to wait for a connection
    pool_recycle=1800,        # Recycle connections after 30 minutes
    pool_pre_ping=True,       # Verify connections before using
    echo=False,               # Set True for debugging SQL queries
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI endpoints.
    Ensures session is properly closed after each request.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine)
