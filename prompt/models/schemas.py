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
    mode: Literal["driving", "walking"] = Field(
        default="driving",
        description="Transportation mode",
    )
    optimize: Literal["distance", "time"] = Field(
        default="time",
        description="Optimization criteria",
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


class Route(BaseModel):
    """A single route variant."""

    route_id: int
    title: str
    total_distance_meters: Optional[float] = None
    total_duration_minutes: Optional[float] = None
    waypoints: list[Waypoint]


class RequestSummary(BaseModel):
    """Summary of the user's request."""

    origin_address: str
    intent: str


class RouteResponse(BaseModel):
    """Response model for route planning with 3 variants."""

    request_summary: RequestSummary
    routes: list[Route]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    details: Optional[str] = None
    raw_response: Optional[str] = None
