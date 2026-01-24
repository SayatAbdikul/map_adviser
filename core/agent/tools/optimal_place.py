"""Optimal place finder tool for finding places that minimize route detour."""

from typing import Literal

from agents import function_tool

from services.gis_places import get_places_client
from services.gis_routing import get_routing_client


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
