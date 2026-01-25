"""Meeting place finder tool for room members."""

import math
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


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate the straight-line distance between two points using Haversine formula.
    
    Returns:
        Distance in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


async def find_meeting_place_impl(
    query: str,
    member_locations: list[MemberLocation],
    mode: Literal["driving", "walking"] = "driving",
    limit: int = 2,
    radius: int = 3000,
) -> dict:
    """
    Internal implementation of find_meeting_place.
    
    Find the best meeting place for a group of people at different locations.
    
    This calculates the centroid (central point) of all member locations,
    searches for places near that center, and finds the best one using
    straight-line distance, then calculates actual routes only for the best place.
    
    Args:
        query: What to search for (e.g., "кафе", "ресторан", "парк")
        member_locations: List of MemberLocation objects with each member's position
        mode: Transportation mode - "driving" or "walking"
        limit: Maximum number of places to search (default 2 to reduce API calls)
        radius: Search radius in meters from centroid (default 3000)
    
    Returns:
        Dictionary with:
        - centroid: The calculated center point
        - best: The best meeting place with actual travel times
        - alternatives: Other options (with estimated distances only)
        - member_routes: Actual travel time for each member to the best place
    """
    if not member_locations:
        return {"error": "No member locations provided"}
    
    if len(member_locations) < 2:
        return {"error": "At least 2 members with locations are required"}
    
    # Calculate centroid
    centroid_lon, centroid_lat = calculate_centroid(member_locations)
    
    # Search for places near the centroid (1 API call)
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
    
    # Score places using straight-line distance (no API calls)
    # This avoids the N×M routing API calls problem
    places_with_scores = []
    for place in places:
        coords = place.get("coordinates", [None, None])
        if coords[0] is None or coords[1] is None:
            continue
        
        place_lon, place_lat = coords[0], coords[1]
        total_distance = 0
        max_distance = 0
        
        # Calculate straight-line distance from each member to this place
        for member in member_locations:
            distance = haversine_distance(
                member.longitude, member.latitude,
                place_lon, place_lat
            )
            total_distance += distance
            max_distance = max(max_distance, distance)
        
        places_with_scores.append({
            "place": place,
            "total_distance_meters": total_distance,
            "max_distance_meters": max_distance,
            "avg_distance_meters": total_distance / len(member_locations),
        })
    
    if not places_with_scores:
        return {
            "error": "No valid places found",
            "centroid": {"longitude": centroid_lon, "latitude": centroid_lat},
        }
    
    # Sort by total distance (fairest for everyone)
    places_with_scores.sort(key=lambda p: p["total_distance_meters"])
    
    best_place_data = places_with_scores[0]
    best_place = best_place_data["place"]
    alternatives = places_with_scores[1:] if len(places_with_scores) > 1 else []
    
    # Calculate actual routes ONLY for the best place (N API calls, where N = member count)
    routing_client = get_routing_client()
    best_coords = best_place.get("coordinates", [None, None])
    place_lon, place_lat = best_coords[0], best_coords[1]
    
    total_duration = 0
    max_duration = 0
    member_travel_times = []
    
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
            # If routing fails, use estimated time from straight-line distance
            est_distance = haversine_distance(
                member.longitude, member.latitude,
                place_lon, place_lat
            )
            # Estimate: walking ~5km/h, driving ~30km/h
            est_speed = 5000 if mode == "walking" else 30000  # meters per hour
            est_duration = (est_distance / est_speed) * 3600  # seconds
            
            member_travel_times.append({
                "member_id": member.member_id,
                "member_nickname": member.member_nickname,
                "duration_seconds": int(est_duration),
                "duration_minutes": round(est_duration / 60, 1),
                "distance_meters": int(est_distance),
                "estimated": True,
            })
            total_duration += est_duration
            max_duration = max(max_duration, est_duration)
    
    return {
        "centroid": {"longitude": centroid_lon, "latitude": centroid_lat},
        "member_count": len(member_locations),
        "best": {
            "name": best_place.get("name"),
            "address": best_place.get("address"),
            "coordinates": best_place.get("coordinates"),
            "rating": best_place.get("rating"),
            "total_travel_time_minutes": round(total_duration / 60, 1),
            "max_travel_time_minutes": round(max_duration / 60, 1),
            "average_travel_time_minutes": round((total_duration / len(member_locations)) / 60, 1),
            "member_travel_times": member_travel_times,
        },
        "alternatives": [
            {
                "name": alt["place"].get("name"),
                "address": alt["place"].get("address"),
                "coordinates": alt["place"].get("coordinates"),
                "rating": alt["place"].get("rating"),
                "estimated_total_distance_km": round(alt["total_distance_meters"] / 1000, 1),
                "estimated_avg_distance_km": round(alt["avg_distance_meters"] / 1000, 1),
            }
            for alt in alternatives
        ],
    }


@function_tool
async def find_meeting_place(
    query: str,
    member_locations: list[MemberLocation],
    mode: Literal["driving", "walking"] = "driving",
    limit: int = 2,
    radius: int = 3000,
) -> dict:
    """
    Find the best meeting place for a group of people at different locations.
    
    This calculates the centroid (central point) of all member locations,
    searches for places near that center, and finds the best one using
    straight-line distance, then calculates actual routes only for the best place.
    
    Args:
        query: What to search for (e.g., "кафе", "ресторан", "парк")
        member_locations: List of MemberLocation objects with each member's position
        mode: Transportation mode - "driving" or "walking"
        limit: Maximum number of places to search (default 2 to reduce API calls)
        radius: Search radius in meters from centroid (default 3000)
    
    Returns:
        Dictionary with meeting place information
    """
    return await find_meeting_place_impl(query, member_locations, mode, limit, radius)
