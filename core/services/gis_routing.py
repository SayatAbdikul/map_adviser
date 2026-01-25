"""2GIS Routing API client for calculating routes."""

import os
from typing import Literal, Optional

from services.gis_rate_limiter import create_2gis_async_client

ROUTING_URL = "https://routing.api.2gis.com/routing/7.0.0/global"

# Singleton instance for connection reuse
_routing_client_instance: Optional["GISRoutingClient"] = None


def get_api_key() -> str:
    """Get API key lazily to ensure .env is loaded first."""
    return os.getenv("GIS_API_KEY", "")


def get_routing_client() -> "GISRoutingClient":
    """Get or create the singleton GISRoutingClient instance.
    
    This reuses the same HTTP client across calls to avoid
    connection setup overhead.
    """
    global _routing_client_instance
    if _routing_client_instance is None:
        _routing_client_instance = GISRoutingClient()
    return _routing_client_instance


async def close_routing_client() -> None:
    """Close the singleton client. Call on application shutdown."""
    global _routing_client_instance
    if _routing_client_instance is not None:
        await _routing_client_instance.close()
        _routing_client_instance = None


class GISRoutingClient:
    """Client for 2GIS Routing API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = create_2gis_async_client(timeout=90.0)

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

        # Convert optimize to 2GIS route_mode
        route_mode = "shortest" if optimize == "distance" else "fastest"

        # Build waypoints for the request
        waypoints = [{"lon": lon, "lat": lat} for lon, lat in points]

        params = {"key": self.api_key}

        payload = {
            "points": waypoints,
            "type": transport_type,
            "route_mode": route_mode,
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
        maneuvers = []
        
        def parse_linestring(linestring_wkt: str) -> list:
            """Parse WKT LINESTRING into list of [lon, lat] coordinates."""
            coords = []
            try:
                # Extract coordinates from LINESTRING(lon lat, lon lat, ...)
                if linestring_wkt.startswith("LINESTRING("):
                    content = linestring_wkt[11:-1]  # Remove 'LINESTRING(' and ')'
                    for pair in content.split(", "):
                        parts = pair.strip().split(" ")
                        if len(parts) >= 2:
                            lon, lat = float(parts[0]), float(parts[1])
                            coords.append([lon, lat])
            except (ValueError, IndexError):
                pass
            return coords

        for i, leg in enumerate(result.get("maneuvers", [])):
            # Extract maneuver/direction instructions
            maneuver_info = {
                "instruction": leg.get("comment", ""),
                "type": leg.get("type", ""),
                "distance": leg.get("outcoming_path", {}).get("distance", 0),
                "duration": leg.get("outcoming_path", {}).get("duration", 0),
            }
            
            # Add street name if available
            if "outcoming_path" in leg:
                path = leg["outcoming_path"]
                # Street names are in "names" list
                names = path.get("names", [])
                maneuver_info["street_name"] = names[0] if names else ""
                
                if "geometry" in path:
                    # Geometry is a list of segments with WKT LINESTRING in 'selection' field
                    for geom_segment in path["geometry"]:
                        selection = geom_segment.get("selection", "")
                        if selection:
                            coords = parse_linestring(selection)
                            geometry.extend(coords)
            
            if maneuver_info["instruction"] or maneuver_info["type"]:
                maneuvers.append(maneuver_info)

        # If maneuvers don't have geometry, try to get from the route directly
        if not geometry and "geometry" in result:
            for geom_item in result["geometry"]:
                # Check if it's WKT format
                if isinstance(geom_item, dict) and "selection" in geom_item:
                    coords = parse_linestring(geom_item["selection"])
                    geometry.extend(coords)
                # Check if it's direct lon/lat format
                elif isinstance(geom_item, dict):
                    lon = geom_item.get("lon") or geom_item.get("longitude")
                    lat = geom_item.get("lat") or geom_item.get("latitude")
                    if lon is not None and lat is not None:
                        geometry.append([lon, lat])

        # Build segments info
        total_distance = result.get("total_distance", 0)
        total_duration = result.get("total_duration", 0)
        
        segments = []

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
            "maneuvers": maneuvers,
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


# Convenience function using shared client
async def calculate_route(
    points: list[tuple[float, float]],
    mode: Literal["driving", "walking"] = "driving",
    optimize: Literal["distance", "time"] = "time",
) -> dict:
    """Calculate route between points."""
    client = get_routing_client()
    return await client.get_route(points, mode, optimize)
