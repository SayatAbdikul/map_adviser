"""
SQLAlchemy ORM Models
- Using ORM prevents SQL injection by default
- All queries are parameterized automatically
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, Index, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Store hashed passwords only!
    name = Column(String(100))
    preferred_city = Column(String(50), default="astana")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    saved_places = relationship("SavedPlace", back_populates="user", cascade="all, delete-orphan")
    saved_routes = relationship("SavedRoute", back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user")


class SavedPlace(Base):
    __tablename__ = "saved_places"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(String(100))  # 2GIS place ID
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    lat = Column(Numeric(10, 7), nullable=False)
    lon = Column(Numeric(10, 7), nullable=False)
    category = Column(String(100))
    city = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_places")
    
    __table_args__ = (
        Index("idx_saved_places_user", "user_id"),
    )


class SavedRoute(Base):
    __tablename__ = "saved_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255))
    origin_name = Column(String(255))
    origin_lat = Column(Numeric(10, 7), nullable=False)
    origin_lon = Column(Numeric(10, 7), nullable=False)
    destination_name = Column(String(255))
    destination_lat = Column(Numeric(10, 7), nullable=False)
    destination_lon = Column(Numeric(10, 7), nullable=False)
    preferred_mode = Column(String(20), default="car")
    waypoints = Column(JSONB)  # Intermediate stops as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_routes")
    
    __table_args__ = (
        Index("idx_saved_routes_user", "user_id"),
    )


class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query = Column(String(500), nullable=False)
    city = Column(String(50))
    result_count = Column(Integer)
    selected_place_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="search_history")


class RouteRequest(Base):
    __tablename__ = "route_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    origin_lat = Column(Numeric(10, 7))
    origin_lon = Column(Numeric(10, 7))
    destination_lat = Column(Numeric(10, 7))
    destination_lon = Column(Numeric(10, 7))
    mode = Column(String(20))
    distance_meters = Column(Integer)
    duration_seconds = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PlacesCache(Base):
    """Cache 2GIS API responses to reduce API calls"""
    __tablename__ = "places_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    query_hash = Column(String(64), unique=True, nullable=False, index=True)
    query = Column(String(500))
    city = Column(String(50))
    results = Column(JSONB)
    expires_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
