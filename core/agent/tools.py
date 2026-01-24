"""Agent tools for interacting with 2GIS APIs."""

from typing import Literal, Optional

from pydantic import BaseModel
from agents import function_tool

from services.gis_places import get_places_client
from services.gis_routing import get_routing_client
from services.gis_regions import get_regions_client


class RoutePoint(BaseModel):
    """A point for routing with longitude and latitude."""

    longitude: float
    latitude: float


@function_tool
async def geocode_address(
    address: str, city: Optional[str] = None, region_id: Optional[int] = None
) -> dict:
    """
    Convert an address string to geographic coordinates.

    Args:
        address: The address to geocode (e.g., "Red Square", "123 Main Street")
        city: Optional city name to narrow the search
        region_id: Optional region ID to limit search to a specific region.
            Use the search_region tool first to get the region ID.

    Returns:
        Dictionary with name, address, and coordinates [longitude, latitude]
    """
    client = get_places_client()
    return await client.geocode(address, city, region_id)


@function_tool
async def search_nearby_places(
    query: str,
    longitude: Optional[float] = None,
    latitude: Optional[float] = None,
    radius: int = 5000,
    limit: int = 5,
    region_id: Optional[int] = None,
) -> list:
    """
    Search for places by category or name near a specific location or within a region.

    You can search in two ways:
    1. Location-based: Provide longitude and latitude to search near a point
    2. Region-based: Provide region_id to search within an entire city/region

    Args:
        query: What to search for (e.g., "bank", "cafe", "pharmacy", "restaurant")
        longitude: Optional longitude of the search center point
        latitude: Optional latitude of the search center point
        radius: Search radius in meters (default 5000, used with location)
        limit: Maximum number of results to return (default 5)
        region_id: Optional region ID to limit search to a specific region.
            Use the search_region tool first to get the region ID.

    Returns:
        List of places with name, address, coordinates, and rating
    """
    client = get_places_client()
    location = None
    if longitude is not None and latitude is not None:
        location = (longitude, latitude)
    return await client.search_places(query, location, radius, limit, region_id)


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
    places_client = get_places_client()
    routing_client = get_routing_client()

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


@function_tool
async def search_region(
    query: str,
    include_bounds: bool = False,
) -> list:
    """
    Search for geographic regions by name to get region IDs.

    Use this tool when a user mentions a city or region name to:
    1. Find the correct region ID for limiting subsequent searches
    2. Verify the region exists in the 2GIS database
    3. Get geographic bounds for the region

    Args:
        query: City or region name (e.g., "Almaty", "Moscow", "Dubai", "Prague")
        include_bounds: Whether to include the geographic bounding box

    Returns:
        List of matching regions with:
        - id: The region ID to use for limiting searches
        - name: The region name
        - type: Region type (e.g., "region")
        - country_code: ISO country code (e.g., "kz", "ru")
        - bounds: Geographic bounding box (if include_bounds=True)
    """
    client = get_regions_client()
    return await client.search_by_name(query, include_bounds=include_bounds)


@function_tool
async def get_region_from_coordinates(
    longitude: float,
    latitude: float,
) -> dict:
    """
    Find which region contains the given coordinates.

    Use this tool to determine the region for a specific location,
    which can then be used to limit subsequent searches.

    Args:
        longitude: Longitude of the point
        latitude: Latitude of the point

    Returns:
        The region containing the coordinates with id, name, type, and country_code.
        Returns an error if no region is found.
    """
    client = get_regions_client()
    result = await client.search_by_coordinates(longitude, latitude)
    if result is None:
        return {"error": f"No region found for coordinates ({longitude}, {latitude})"}
    return result


@function_tool
async def validate_location_in_region(
    longitude: float,
    latitude: float,
    region_id: int,
) -> dict:
    """
    Check if coordinates are within a specific region.

    Use this tool to validate that a destination or waypoint is within
    the user's specified region before including it in a route.

    Args:
        longitude: Longitude of the point to validate
        latitude: Latitude of the point to validate
        region_id: The region ID to validate against (from search_region tool)

    Returns:
        Dictionary with:
        - is_valid: True if location is in the expected region
        - actual_region: The region the coordinates are actually in (id, name)
        - expected_region_id: The expected region ID
        - message: Human-readable message about the validation result
    """
    client = get_regions_client()
    return await client.validate_location_in_region(longitude, latitude, region_id)
