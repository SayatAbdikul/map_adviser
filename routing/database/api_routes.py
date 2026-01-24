"""
Example FastAPI endpoints demonstrating secure database usage.
All queries are SQL injection safe using SQLAlchemy ORM.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from decimal import Decimal

from database.connection import get_db
from database.repository import (
    UserRepository, 
    SavedPlaceRepository, 
    SavedRouteRepository,
    SearchHistoryRepository,
    RouteRequestRepository,
    PlacesCacheRepository
)
from database.security import hash_password, verify_password, generate_secure_token


router = APIRouter(prefix="/api/v1", tags=["users", "places", "routes"])


# =============================================================================
# PYDANTIC SCHEMAS (Input Validation Layer)
# =============================================================================

class UserCreate(BaseModel):
    email: EmailStr  # Validates email format automatically
    password: str
    name: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    preferred_city: str
    
    class Config:
        from_attributes = True


class PlaceCreate(BaseModel):
    name: str
    lat: float
    lon: float
    place_id: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    
    @validator('lat')
    def validate_lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('lon')
    def validate_lon(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class PlaceResponse(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    address: Optional[str]
    category: Optional[str]
    city: Optional[str]
    
    class Config:
        from_attributes = True


class RouteCreate(BaseModel):
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    name: Optional[str] = None
    origin_name: Optional[str] = None
    destination_name: Optional[str] = None
    preferred_mode: Optional[str] = "car"


class RouteResponse(BaseModel):
    id: int
    name: Optional[str]
    origin_name: Optional[str]
    origin_lat: float
    origin_lon: float
    destination_name: Optional[str]
    destination_lat: float
    destination_lon: float
    preferred_mode: str
    
    class Config:
        from_attributes = True


# =============================================================================
# USER ENDPOINTS
# =============================================================================

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.
    Password is hashed before storage - never stored in plain text.
    """
    # Check if email already exists
    existing = UserRepository.get_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password before storing
    hashed = hash_password(user_data.password)
    
    user = UserRepository.create(
        db=db,
        email=user_data.email,
        password_hash=hashed,
        name=user_data.name
    )
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID - parameterized query prevents SQL injection"""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


# =============================================================================
# SAVED PLACES ENDPOINTS
# =============================================================================

@router.get("/users/{user_id}/places", response_model=List[PlaceResponse])
def get_user_places(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Get all saved places for a user"""
    return SavedPlaceRepository.get_user_places(db, user_id, limit)


@router.post("/users/{user_id}/places", response_model=PlaceResponse, status_code=status.HTTP_201_CREATED)
def save_place(user_id: int, place_data: PlaceCreate, db: Session = Depends(get_db)):
    """Save a new place for user"""
    # Verify user exists
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    place = SavedPlaceRepository.create(
        db=db,
        user_id=user_id,
        **place_data.model_dump()
    )
    return place


@router.delete("/users/{user_id}/places/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place(user_id: int, place_id: int, db: Session = Depends(get_db)):
    """Delete a saved place - ensures user owns the place"""
    deleted = SavedPlaceRepository.delete(db, place_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Place not found")


# =============================================================================
# SAVED ROUTES ENDPOINTS
# =============================================================================

@router.get("/users/{user_id}/routes", response_model=List[RouteResponse])
def get_user_routes(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Get all saved routes for a user"""
    return SavedRouteRepository.get_user_routes(db, user_id, limit)


@router.post("/users/{user_id}/routes", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def save_route(user_id: int, route_data: RouteCreate, db: Session = Depends(get_db)):
    """Save a new route for user"""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    route = SavedRouteRepository.create(
        db=db,
        user_id=user_id,
        **route_data.model_dump()
    )
    return route


# =============================================================================
# SEARCH & ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/popular-searches")
def get_popular_searches(city: Optional[str] = None, limit: int = 10, db: Session = Depends(get_db)):
    """Get popular search queries"""
    results = SearchHistoryRepository.get_popular_searches(db, city, limit)
    return [{"query": q, "count": c} for q, c in results]
