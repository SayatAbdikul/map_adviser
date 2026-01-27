"""Region tools for searching and validating geographic regions."""

from agents import function_tool

from services.gis_regions import get_regions_client


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
