"""Public transport routing tool for calculating transit routes."""

from typing import Optional, List

from pydantic import BaseModel
from agents import function_tool

from services.public_transport import get_public_transport_client


class IntermediatePoint(BaseModel):
    """An intermediate waypoint for public transport routing."""
    
    longitude: float
    latitude: float
    name: str = "Waypoint"


@function_tool
async def calculate_public_transport_route(
    start_longitude: float,
    start_latitude: float,
    end_longitude: float,
    end_latitude: float,
    start_name: str = "Start Point",
    end_name: str = "End Point",
    transport_types: Optional[List[str]] = None,
    intermediate_points: Optional[List[IntermediatePoint]] = None,
    locale: str = "en",
) -> dict:
    """
    Calculate a public transport route between two points.

    Use this tool when a user wants to travel using public transportation
    like buses, metro/subway, trams, trolleybuses, or trains.

    Args:
        start_longitude: Longitude of starting point
        start_latitude: Latitude of starting point
        end_longitude: Longitude of ending point
        end_latitude: Latitude of ending point
        start_name: Human-readable name for starting point
        end_name: Human-readable name for ending point
        transport_types: List of allowed transport types. Default: ["metro", "bus", "trolleybus", "tram"]
            Valid types: "bus", "trolleybus", "tram", "shuttle_bus", "metro",
            "suburban_train", "funicular", "monorail", "river_transport"
        intermediate_points: List of waypoints (dicts with "longitude", "latitude", "name" keys)
        locale: Language code for response (default: "en")

    Returns:
        Dictionary with route alternatives including:
        - source: Starting point name
        - target: Ending point name
        - routes: List of route alternatives, each with:
          - total_duration_seconds: Total journey time
          - total_distance_meters: Total distance
          - walking_duration_seconds: Time spent walking
          - transfer_count: Number of transfers
          - transport_chain: Description of the journey (e.g., "Walk → Metro → Bus")
          - movements: Detailed segments of the journey
    """
    client = get_public_transport_client()

    # Convert intermediate points to the format expected by the client
    intermediate_pts = None
    if intermediate_points:
        intermediate_pts = [
            (point.longitude, point.latitude, point.name)
            for point in intermediate_points
        ]

    return await client.get_public_transport_route(
        source_point=(start_longitude, start_latitude),
        target_point=(end_longitude, end_latitude),
        source_name=start_name,
        target_name=end_name,
        intermediate_points=intermediate_pts,
        transport_types=transport_types,
        locale=locale,
        include_pedestrian_instructions=False,
    )
