"""Pydantic models for API request/response schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """Request model for route planning."""

    query: str = Field(
        ...,
        description="Natural language route request",
        examples=["Поехать от Назарбаев Университета до банка, потом в кафе, потом в Ботанический парк"],
    )
    mode: Literal["driving", "walking", "public_transport"] = Field(
        default="driving",
        description="Transportation mode: driving (car), walking (pedestrian), or public_transport (bus, metro, tram, etc.)",
    )


class Location(BaseModel):
    """Geographic location."""

    lat: float
    lon: float


class Waypoint(BaseModel):
    """A waypoint in the route."""

    order: int
    type: Literal["start", "stop", "end"]
    name: str
    address: str
    location: Location
    category: Optional[str] = None


class PublicTransportMovement(BaseModel):
    """A single segment of a public transport journey."""

    type: str  # "walkway", "passage", "transfer"
    duration_seconds: int
    distance_meters: int
    transport_type: Optional[str] = None  # "metro", "bus", "tram", etc.
    route_name: Optional[str] = None  # e.g., "Line 1", "Bus 42"
    line_name: Optional[str] = None  # for metro
    stops_count: Optional[int] = None


class PublicTransportRoute(BaseModel):
    """A public transport route alternative."""

    total_duration_seconds: int
    total_distance_meters: int
    walking_duration_seconds: int
    transfer_count: int
    transport_chain: str  # e.g., "Walk → Metro → Bus → Walk"
    movements: list[PublicTransportMovement]


class Route(BaseModel):
    """A single route variant."""

    route_id: int
    title: str
    total_distance_meters: Optional[float] = None
    total_duration_minutes: Optional[float] = None
    waypoints: list[Waypoint]
    # Public transport specific fields
    transport_chain: Optional[str] = None  # e.g., "Walk → Metro → Bus → Walk"
    transfer_count: Optional[int] = None
    walking_duration_minutes: Optional[float] = None
    # Time-based planning fields
    recommended_departure_time: Optional[str] = None  # e.g., "08:15"
    estimated_arrival_time: Optional[str] = None  # e.g., "09:00"


class RequestSummary(BaseModel):
    """Summary of the user's request."""

    origin_address: str
    intent: str
    transport_mode: Optional[str] = None  # "driving", "walking", "public_transport"
    optimization_choice: Optional[str] = None  # "time" or "distance"
    arrival_time: Optional[str] = None  # Desired arrival time (e.g., "09:00", "14:30")
    departure_time: Optional[str] = None  # Calculated/specified departure time


class RouteResponse(BaseModel):
    """Response model for route planning with 3 variants."""

    request_summary: RequestSummary
    routes: list[Route]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    details: Optional[str] = None
    raw_response: Optional[str] = None
