"""Geocoding tool for converting addresses to coordinates."""

from typing import Optional

from agent.tools.compat import function_tool

from services.gis_places import get_places_client


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
