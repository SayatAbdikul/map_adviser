"""
Repository Layer - Safe Database Operations
- All queries use parameterized statements via SQLAlchemy ORM
- Never concatenates user input into SQL strings
- Input validation before database operations
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import hashlib
import re

from .models import User, SavedPlace, SavedRoute, SearchHistory, RouteRequest, PlacesCache


# =============================================================================
# INPUT VALIDATION HELPERS
# =============================================================================

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude ranges"""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def sanitize_string(value: str, max_length: int = 500) -> str:
    """Sanitize string input - trim and limit length"""
    if not value:
        return ""
    return str(value).strip()[:max_length]


# =============================================================================
# USER REPOSITORY
# =============================================================================

class UserRepository:
    """Safe database operations for users"""
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID - parameterized automatically by ORM"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email - safe from SQL injection"""
        if not validate_email(email):
            return None
        # SQLAlchemy parameterizes this: WHERE email = $1
        return db.query(User).filter(User.email == email.lower()).first()
    
    @staticmethod
    def create(db: Session, email: str, password_hash: str, name: str = None) -> User:
        """Create new user with validated input"""
        if not validate_email(email):
            raise ValueError("Invalid email format")
        
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,  # Must be already hashed!
            name=sanitize_string(name, 100) if name else None
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update(db: Session, user_id: int, **kwargs) -> Optional[User]:
        """Update user with validated input"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Only allow specific fields to be updated
        allowed_fields = {"name", "preferred_city", "is_active"}
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(user, key, sanitize_string(str(value), 100))
        
        db.commit()
        db.refresh(user)
        return user


# =============================================================================
# SAVED PLACES REPOSITORY
# =============================================================================

class SavedPlaceRepository:
    """Safe database operations for saved places"""
    
    @staticmethod
    def get_user_places(db: Session, user_id: int, limit: int = 100) -> List[SavedPlace]:
        """Get all saved places for a user"""
        # Limit is capped to prevent abuse
        safe_limit = min(max(1, limit), 1000)
        return (
            db.query(SavedPlace)
            .filter(SavedPlace.user_id == user_id)
            .order_by(SavedPlace.created_at.desc())
            .limit(safe_limit)
            .all()
        )
    
    @staticmethod
    def create(
        db: Session, 
        user_id: int,
        name: str,
        lat: float,
        lon: float,
        place_id: str = None,
        address: str = None,
        category: str = None,
        city: str = None
    ) -> SavedPlace:
        """Create saved place with validation"""
        if not validate_coordinates(lat, lon):
            raise ValueError("Invalid coordinates")
        
        place = SavedPlace(
            user_id=user_id,
            place_id=sanitize_string(place_id, 100) if place_id else None,
            name=sanitize_string(name, 255),
            address=sanitize_string(address, 500) if address else None,
            lat=lat,
            lon=lon,
            category=sanitize_string(category, 100) if category else None,
            city=sanitize_string(city, 50) if city else None
        )
        db.add(place)
        db.commit()
        db.refresh(place)
        return place
    
    @staticmethod
    def delete(db: Session, place_id: int, user_id: int) -> bool:
        """Delete place - ensures user owns the place"""
        result = (
            db.query(SavedPlace)
            .filter(and_(SavedPlace.id == place_id, SavedPlace.user_id == user_id))
            .delete()
        )
        db.commit()
        return result > 0


# =============================================================================
# SAVED ROUTES REPOSITORY
# =============================================================================

class SavedRouteRepository:
    """Safe database operations for saved routes"""
    
    @staticmethod
    def get_user_routes(db: Session, user_id: int, limit: int = 100) -> List[SavedRoute]:
        """Get all saved routes for a user"""
        safe_limit = min(max(1, limit), 1000)
        return (
            db.query(SavedRoute)
            .filter(SavedRoute.user_id == user_id)
            .order_by(SavedRoute.created_at.desc())
            .limit(safe_limit)
            .all()
        )
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        name: str = None,
        origin_name: str = None,
        destination_name: str = None,
        preferred_mode: str = "car",
        waypoints: list = None
    ) -> SavedRoute:
        """Create saved route with validation"""
        if not validate_coordinates(origin_lat, origin_lon):
            raise ValueError("Invalid origin coordinates")
        if not validate_coordinates(destination_lat, destination_lon):
            raise ValueError("Invalid destination coordinates")
        
        # Validate transport mode
        valid_modes = {"car", "pedestrian", "bicycle", "public_transport"}
        mode = preferred_mode if preferred_mode in valid_modes else "car"
        
        route = SavedRoute(
            user_id=user_id,
            name=sanitize_string(name, 255) if name else None,
            origin_name=sanitize_string(origin_name, 255) if origin_name else None,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_name=sanitize_string(destination_name, 255) if destination_name else None,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            preferred_mode=mode,
            waypoints=waypoints  # JSONB handles this safely
        )
        db.add(route)
        db.commit()
        db.refresh(route)
        return route


# =============================================================================
# SEARCH HISTORY REPOSITORY
# =============================================================================

class SearchHistoryRepository:
    """Safe database operations for search history"""
    
    @staticmethod
    def log_search(
        db: Session,
        query: str,
        city: str = None,
        user_id: int = None,
        result_count: int = None,
        selected_place_id: str = None
    ) -> SearchHistory:
        """Log a search - safe from injection"""
        history = SearchHistory(
            user_id=user_id,
            query=sanitize_string(query, 500),
            city=sanitize_string(city, 50) if city else None,
            result_count=result_count,
            selected_place_id=sanitize_string(selected_place_id, 100) if selected_place_id else None
        )
        db.add(history)
        db.commit()
        return history
    
    @staticmethod
    def get_popular_searches(db: Session, city: str = None, limit: int = 10) -> List[tuple]:
        """Get popular search queries"""
        safe_limit = min(max(1, limit), 100)
        query = (
            db.query(SearchHistory.query, func.count(SearchHistory.id).label("count"))
            .group_by(SearchHistory.query)
            .order_by(func.count(SearchHistory.id).desc())
            .limit(safe_limit)
        )
        if city:
            query = query.filter(SearchHistory.city == sanitize_string(city, 50))
        return query.all()


# =============================================================================
# ROUTE REQUESTS REPOSITORY (Logging)
# =============================================================================

class RouteRequestRepository:
    """Safe database operations for route request logging"""
    
    @staticmethod
    def log_request(
        db: Session,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        mode: str,
        success: bool,
        user_id: int = None,
        distance_meters: int = None,
        duration_seconds: int = None,
        error_message: str = None
    ) -> RouteRequest:
        """Log route request for analytics"""
        request = RouteRequest(
            user_id=user_id,
            origin_lat=origin_lat if validate_coordinates(origin_lat, 0) else None,
            origin_lon=origin_lon if validate_coordinates(0, origin_lon) else None,
            destination_lat=destination_lat if validate_coordinates(destination_lat, 0) else None,
            destination_lon=destination_lon if validate_coordinates(0, destination_lon) else None,
            mode=sanitize_string(mode, 20),
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            success=success,
            error_message=sanitize_string(error_message, 1000) if error_message else None
        )
        db.add(request)
        db.commit()
        return request


# =============================================================================
# PLACES CACHE REPOSITORY
# =============================================================================

class PlacesCacheRepository:
    """Cache repository to reduce 2GIS API calls"""
    
    @staticmethod
    def _generate_hash(query: str, city: str) -> str:
        """Generate deterministic hash for cache key"""
        key = f"{query.lower().strip()}:{city.lower().strip() if city else ''}"
        return hashlib.md5(key.encode()).hexdigest()
    
    @staticmethod
    def get_cached(db: Session, query: str, city: str = None) -> Optional[dict]:
        """Get cached results if not expired"""
        query_hash = PlacesCacheRepository._generate_hash(query, city)
        cached = (
            db.query(PlacesCache)
            .filter(
                and_(
                    PlacesCache.query_hash == query_hash,
                    PlacesCache.expires_at > datetime.utcnow()
                )
            )
            .first()
        )
        return cached.results if cached else None
    
    @staticmethod
    def set_cache(
        db: Session, 
        query: str, 
        city: str, 
        results: dict, 
        ttl_hours: int = 24
    ) -> PlacesCache:
        """Cache search results"""
        query_hash = PlacesCacheRepository._generate_hash(query, city)
        
        # Upsert: update if exists, insert if not
        existing = db.query(PlacesCache).filter(PlacesCache.query_hash == query_hash).first()
        
        if existing:
            existing.results = results
            existing.expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            db.commit()
            return existing
        
        cache = PlacesCache(
            query_hash=query_hash,
            query=sanitize_string(query, 500),
            city=sanitize_string(city, 50) if city else None,
            results=results,
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours)
        )
        db.add(cache)
        db.commit()
        return cache
    
    @staticmethod
    def cleanup_expired(db: Session) -> int:
        """Remove expired cache entries"""
        result = (
            db.query(PlacesCache)
            .filter(PlacesCache.expires_at < datetime.utcnow())
            .delete()
        )
        db.commit()
        return result
