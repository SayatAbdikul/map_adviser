"""2GIS Routing API client for calculating routes."""

import os
from typing import Literal, Optional

import httpx

ROUTING_URL = "https://routing.api.2gis.com/routing/7.0.0/global"


def get_api_key() -> str:
    """Get API key lazily to ensure .env is loaded first."""
    return os.getenv("GIS_API_KEY", "")


class GISRoutingClient:
    """Client for 2GIS Routing API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_route(
        self,
        points: list[tuple[float, float]],
        mode: Literal["driving", "walking"] = "driving",
        optimize: Literal["distance", "time"] = "time",
    ) -> dict:
        """
        Calculate route between multiple points.

        Args:
            points: List of (longitude, latitude) tuples
            mode: Transport mode - "driving" or "walking"
            optimize: Optimization criteria - "distance" or "time"

        Returns:
            Dict with route geometry, total distance, total duration, and segments
        """
        if len(points) < 2:
            return {"error": "At least 2 points are required"}

        # Convert mode to 2GIS type
        transport_type = "car" if mode == "driving" else "pedestrian"

        # Build waypoints for the request
        waypoints = [{"lon": lon, "lat": lat} for lon, lat in points]

        params = {"key": self.api_key}

        payload = {
            "points": waypoints,
            "type": transport_type,
        }

        response = await self.client.post(
            ROUTING_URL,
            params=params,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("result"):
            return {"error": "No route found", "details": data}

        result = data["result"][0]

        # Extract geometry (list of coordinates for the polyline)
        geometry = []
        segments = []

        for i, leg in enumerate(result.get("maneuvers", [])):
            if "outcoming_path" in leg:
                path = leg["outcoming_path"]
                if "geometry" in path:
                    # Geometry is encoded - extract coordinates
                    for point in path["geometry"]:
                        geometry.append([point["lon"], point["lat"]])

        # If maneuvers don't have geometry, try to get from the route directly
        if not geometry and "geometry" in result:
            for point in result["geometry"]:
                geometry.append([point["lon"], point["lat"]])

        # Build segments info
        total_distance = result.get("total_distance", 0)
        total_duration = result.get("total_duration", 0)

        # Calculate per-segment info if available
        if "waypoints" in result:
            prev_distance = 0
            prev_duration = 0
            for i, wp in enumerate(result["waypoints"]):
                if i > 0:
                    seg_distance = wp.get("distance", 0) - prev_distance
                    seg_duration = wp.get("duration", 0) - prev_duration
                    segments.append({
                        "from": i - 1,
                        "to": i,
                        "distance": seg_distance,
                        "duration": seg_duration,
                    })
                prev_distance = wp.get("distance", 0)
                prev_duration = wp.get("duration", 0)

        return {
            "geometry": geometry,
            "total_distance": total_distance,
            "total_duration": total_duration,
            "segments": segments,
            "mode": mode,
            "optimize": optimize,
        }

    async def calculate_detour(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        via: tuple[float, float],
        mode: Literal["driving", "walking"] = "driving",
    ) -> dict:
        """
        Calculate how much extra distance/time a detour adds.

        Args:
            start: Starting point (lon, lat)
            end: Ending point (lon, lat)
            via: Waypoint to route through (lon, lat)
            mode: Transport mode

        Returns:
            Dict with direct route info, detour route info, and difference
        """
        # Get direct route
        direct = await self.get_route([start, end], mode=mode)
        if "error" in direct:
            return direct

        # Get route via waypoint
        detour = await self.get_route([start, via, end], mode=mode)
        if "error" in detour:
            return detour

        return {
            "direct_distance": direct["total_distance"],
            "direct_duration": direct["total_duration"],
            "detour_distance": detour["total_distance"],
            "detour_duration": detour["total_duration"],
            "extra_distance": detour["total_distance"] - direct["total_distance"],
            "extra_duration": detour["total_duration"] - direct["total_duration"],
        }


# Convenience function for one-off operations
async def calculate_route(
    points: list[tuple[float, float]],
    mode: Literal["driving", "walking"] = "driving",
    optimize: Literal["distance", "time"] = "time",
) -> dict:
    """Calculate route between points."""
    client = GISRoutingClient()
    try:
        return await client.get_route(points, mode, optimize)
    finally:
        await client.close()
