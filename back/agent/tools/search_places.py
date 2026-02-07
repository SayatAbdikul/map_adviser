"""Search nearby places tool for finding places by category or name."""

from typing import Optional

from agent.tools.compat import function_tool

from services.gis_places import get_places_client


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
