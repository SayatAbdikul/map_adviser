from pydantic import BaseModel
from typing import List, Optional


class PlaceRequest(BaseModel):
    """Request model for user's textual description"""
    description: str
    city: Optional[str] = "astana"  # Default city for search


class Place(BaseModel):
    """Model for a place returned by 2GIS"""
    id: str
    name: str
    address: str
    lat: float
    lon: float
    type: Optional[str] = None


class RouteRequest(BaseModel):
    """Request model for route building"""
    places: List[Place]


class RouteResponse(BaseModel):
    """Response model for the complete route"""
    places: List[Place]
    route_url: str
    total_distance: Optional[int] = None  # in meters
    total_duration: Optional[int] = None  # in seconds
    gemini_explanation: str
