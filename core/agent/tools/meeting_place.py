"""Meeting place finder tool for room members."""

from typing import Literal

from agents import function_tool
from pydantic import BaseModel

from services.gis_places import get_places_client
from services.gis_routing import get_routing_client


class MemberLocation(BaseModel):
    """A member's location with ID for reference."""
    member_id: str
    member_nickname: str
    longitude: float
    latitude: float


def calculate_centroid(locations: list[MemberLocation]) -> tuple[float, float]:
    """Calculate the geographic centroid of all member locations.
    
    Returns:
        Tuple of (longitude, latitude) representing the centroid.
    """
    if not locations:
        raise ValueError("No locations provided")
    
    total_lon = sum(loc.longitude for loc in locations)
    total_lat = sum(loc.latitude for loc in locations)
    count = len(locations)
    
    return (total_lon / count, total_lat / count)


async def find_meeting_place_impl(
    query: str,
    member_locations: list[MemberLocation],
    mode: Literal["driving", "walking"] = "driving",
    limit: int = 5,
    radius: int = 3000,
) -> dict:
    """
    Internal implementation of find_meeting_place.
    
    Find the best meeting place for a group of people at different locations.
    
    This calculates the centroid (central point) of all member locations,
    searches for places near that center, and scores them based on total
    travel time for all members.
    
    Args:
        query: What to search for (e.g., "кафе", "ресторан", "парк")
        member_locations: List of MemberLocation objects with each member's position
        mode: Transportation mode - "driving" or "walking"
        limit: Maximum number of places to consider and return
        radius: Search radius in meters from centroid (default 3000)
    
    Returns:
        Dictionary with:
        - centroid: The calculated center point
        - best: The best meeting place with total travel times
        - alternatives: Other good options
        - member_routes: Estimated travel time for each member to the best place
    """
    if not member_locations:
        return {"error": "No member locations provided"}
    
    if len(member_locations) < 2:
        return {"error": "At least 2 members with locations are required"}
    
    # Calculate centroid
    centroid_lon, centroid_lat = calculate_centroid(member_locations)
    
    # Search for places near the centroid
    places_client = get_places_client()
    places = await places_client.search_places(
        query=query,
        location=(centroid_lon, centroid_lat),
        radius=radius,
        limit=limit,
    )
    
    if not places:
        return {
            "error": f"Не найдено '{query}' в радиусе {radius}м от центральной точки",
            "centroid": {"longitude": centroid_lon, "latitude": centroid_lat},
        }
    
    # Calculate travel times for each place from all members
    routing_client = get_routing_client()
    
    places_with_scores = []
    for place in places:
        coords = place.get("coordinates", [None, None])
        if coords[0] is None or coords[1] is None:
            continue
        
        place_lon, place_lat = coords[0], coords[1]
        total_duration = 0
        max_duration = 0
        member_travel_times = []
        
        # Calculate route from each member to this place
        for member in member_locations:
            try:
                route = await routing_client.get_route(
                    points=[(member.longitude, member.latitude), (place_lon, place_lat)],
                    mode=mode,
                    optimize="time",
                )
                duration = route.get("total_duration", 0)
                total_duration += duration
                max_duration = max(max_duration, duration)
                
                member_travel_times.append({
                    "member_id": member.member_id,
                    "member_nickname": member.member_nickname,
                    "duration_seconds": duration,
                    "duration_minutes": round(duration / 60, 1),
                    "distance_meters": route.get("total_distance", 0),
                })
            except Exception:
                # If routing fails, use a large penalty
                member_travel_times.append({
                    "member_id": member.member_id,
                    "member_nickname": member.member_nickname,
                    "duration_seconds": None,
                    "error": "Could not calculate route",
                })
                total_duration += 9999  # Penalty for failed route
        
        places_with_scores.append({
            "place": place,
            "total_duration_seconds": total_duration,
            "max_duration_seconds": max_duration,
            "average_duration_seconds": total_duration / len(member_locations),
            "member_travel_times": member_travel_times,
        })
    
    if not places_with_scores:
        return {
            "error": "Could not calculate routes to any places",
            "centroid": {"longitude": centroid_lon, "latitude": centroid_lat},
        }
    
    # Sort by total duration (fairest for everyone)
    places_with_scores.sort(key=lambda p: p["total_duration_seconds"])
    
    best = places_with_scores[0]
    alternatives = places_with_scores[1:] if len(places_with_scores) > 1 else []
    
    return {
        "centroid": {"longitude": centroid_lon, "latitude": centroid_lat},
        "member_count": len(member_locations),
        "best": {
            "name": best["place"].get("name"),
            "address": best["place"].get("address"),
            "coordinates": best["place"].get("coordinates"),
            "rating": best["place"].get("rating"),
            "total_travel_time_minutes": round(best["total_duration_seconds"] / 60, 1),
            "max_travel_time_minutes": round(best["max_duration_seconds"] / 60, 1),
            "average_travel_time_minutes": round(best["average_duration_seconds"] / 60, 1),
            "member_travel_times": best["member_travel_times"],
        },
        "alternatives": [
            {
                "name": alt["place"].get("name"),
                "address": alt["place"].get("address"),
                "coordinates": alt["place"].get("coordinates"),
                "rating": alt["place"].get("rating"),
                "total_travel_time_minutes": round(alt["total_duration_seconds"] / 60, 1),
                "average_travel_time_minutes": round(alt["average_duration_seconds"] / 60, 1),
            }
            for alt in alternatives
        ],
    }


@function_tool
async def find_meeting_place(
    query: str,
    member_locations: list[MemberLocation],
    mode: Literal["driving", "walking"] = "driving",
    limit: int = 5,
    radius: int = 3000,
) -> dict:
    """
    Find the best meeting place for a group of people at different locations.
    
    This calculates the centroid (central point) of all member locations,
    searches for places near that center, and scores them based on total
    travel time for all members.
    
    Args:
        query: What to search for (e.g., "кафе", "ресторан", "парк")
        member_locations: List of MemberLocation objects with each member's position
        mode: Transportation mode - "driving" or "walking"
        limit: Maximum number of places to consider and return
        radius: Search radius in meters from centroid (default 3000)
    
    Returns:
        Dictionary with meeting place information
    """
    return await find_meeting_place_impl(query, member_locations, mode, limit, radius)
