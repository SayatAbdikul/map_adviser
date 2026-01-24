"""Agent tools for interacting with 2GIS APIs."""

from typing import Literal, Optional

from pydantic import BaseModel
from agents import function_tool

from services.gis_places import GISPlacesClient
from services.gis_routing import GISRoutingClient


class RoutePoint(BaseModel):
    """A point for routing with longitude and latitude."""

    longitude: float
    latitude: float


@function_tool
async def geocode_address(address: str, city: Optional[str] = None) -> dict:
    """
    Convert an address string to geographic coordinates.

    Args:
        address: The address to geocode (e.g., "Red Square", "123 Main Street")
        city: Optional city name to narrow the search

    Returns:
        Dictionary with name, address, and coordinates [longitude, latitude]
    """
    client = GISPlacesClient()
    try:
        result = await client.geocode(address, city)
        return result
    finally:
        await client.close()


@function_tool
async def search_nearby_places(
    query: str,
    longitude: float,
    latitude: float,
    radius: int = 5000,
    limit: int = 5,
) -> list:
    """
    Search for places by category or name near a specific location.

    Args:
        query: What to search for (e.g., "bank", "cafe", "pharmacy", "restaurant")
        longitude: Longitude of the search center point
        latitude: Latitude of the search center point
        radius: Search radius in meters (default 5000)
        limit: Maximum number of results to return (default 5)

    Returns:
        List of places with name, address, coordinates, and rating
    """
    client = GISPlacesClient()
    try:
        result = await client.search_places(query, (longitude, latitude), radius, limit)
        return result
    finally:
        await client.close()


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
    client = GISRoutingClient()
    try:
        # Convert points to tuples
        point_tuples = [(p.longitude, p.latitude) for p in points]
        result = await client.get_route(point_tuples, mode, optimize)
        return result
    finally:
        await client.close()


@function_tool
async def find_optimal_place(
    query: str,
    start_longitude: float,
    start_latitude: float,
    end_longitude: float,
    end_latitude: float,
    mode: Literal["driving", "walking"] = "driving",
    limit: int = 5,
) -> dict:
    """
    Find the best place of a category that minimizes detour from start to end.

    This searches for places along the route and returns the one that adds
    the least extra distance/time to the journey, along with alternatives.

    Args:
        query: What to search for (e.g., "bank", "cafe")
        start_longitude: Longitude of starting point
        start_latitude: Latitude of starting point
        end_longitude: Longitude of ending point
        end_latitude: Latitude of ending point
        mode: Transportation mode - "driving" or "walking"
        limit: Maximum number of alternatives to consider

    Returns:
        Dictionary with the best place and list of alternatives
    """
    places_client = GISPlacesClient()
    routing_client = GISRoutingClient()

    try:
        # Search for places along the route
        places = await places_client.search_places_along_route(
            query,
            (start_longitude, start_latitude),
            (end_longitude, end_latitude),
            limit=limit,
        )

        if not places:
            return {"error": f"No {query} found along the route"}

        # Calculate detour for each place
        start = (start_longitude, start_latitude)
        end = (end_longitude, end_latitude)

        places_with_detour = []
        for place in places:
            coords = place["coordinates"]
            if coords[0] is None or coords[1] is None:
                continue

            via = (coords[0], coords[1])
            detour = await routing_client.calculate_detour(start, end, via, mode)

            if "error" not in detour:
                places_with_detour.append({
                    **place,
                    "extra_distance": detour["extra_distance"],
                    "extra_duration": detour["extra_duration"],
                })

        if not places_with_detour:
            # Return first place without detour calculation
            return {
                "best": places[0],
                "alternatives": places[1:] if len(places) > 1 else [],
            }

        # Sort by extra duration (or distance)
        places_with_detour.sort(key=lambda p: p["extra_duration"])

        return {
            "best": places_with_detour[0],
            "alternatives": places_with_detour[1:],
        }

    finally:
        await places_client.close()
        await routing_client.close()
