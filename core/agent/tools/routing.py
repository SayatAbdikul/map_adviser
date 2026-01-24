"""Routing tool for calculating routes between points."""

from typing import Literal

from pydantic import BaseModel
from agents import function_tool

from services.gis_routing import get_routing_client


class RoutePoint(BaseModel):
    """A point for routing with longitude and latitude."""

    longitude: float
    latitude: float


@function_tool
async def calculate_route(
    points: list[RoutePoint],
    mode: Literal["driving", "walking"] = "driving",
    optimize: Literal["distance", "time"] = "time",
) -> dict:
    """
    Calculate a route through multiple points.

    Args:
        points: List of RoutePoint objects with longitude and latitude
        mode: Transportation mode - "driving" or "walking"
        optimize: What to optimize for - "distance" or "time"

    Returns:
        Dictionary with route geometry, total_distance (meters), total_duration (seconds)
    """
    client = get_routing_client()
    # Convert points to tuples
    point_tuples = [(p.longitude, p.latitude) for p in points]
    return await client.get_route(point_tuples, mode, optimize)
