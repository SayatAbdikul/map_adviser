"""2GIS Public Transport API client for calculating public transport routes."""

import logging
import os
import re
from typing import Literal, Optional

import httpx

logger = logging.getLogger(__name__)

def parse_wkt(wkt: str) -> list[list[float]]:
    """Parse WKT geometry to list of [lon, lat] coordinates.

    Supports POINT, LINESTRING, and MULTILINESTRING.

    Args:
        wkt: WKT string like "LINESTRING(lon1 lat1, lon2 lat2, ...)" or "POINT(lon lat)"

    Returns:
        List of [lon, lat] coordinate pairs
    """
    if not wkt:
        return []

    coordinates = []

    # Try POINT first
    point_match = re.search(r'POINT\s*\(\s*([^\)]+)\s*\)', wkt, re.IGNORECASE)
    if point_match:
        parts = point_match.group(1).strip().split()
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                return [[lon, lat]]
            except ValueError:
                pass

    # Try LINESTRING
    line_match = re.search(r'LINESTRING\s*\(([^)]+)\)', wkt, re.IGNORECASE)
    if line_match:
        coords_str = line_match.group(1)
        for pair in coords_str.split(','):
            parts = pair.strip().split()
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coordinates.append([lon, lat])
                except ValueError:
                    continue
        return coordinates

    # Try MULTILINESTRING - take all linestrings
    multi_match = re.findall(r'\(([^()]+)\)', wkt)
    if multi_match:
        for coords_str in multi_match:
            for pair in coords_str.split(','):
                parts = pair.strip().split()
                if len(parts) >= 2:
                    try:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        coordinates.append([lon, lat])
                    except ValueError:
                        continue

    return coordinates

from services.gis_rate_limiter import create_2gis_async_client

PUBLIC_TRANSPORT_URL = "https://routing.api.2gis.com/public_transport/2.0"

# Singleton instance for connection reuse
_public_transport_client_instance: Optional["GISPublicTransportClient"] = None


def get_api_key() -> str:
    """Get API key lazily to ensure .env is loaded first."""
    return os.getenv("GIS_API_KEY", "")


def get_public_transport_client() -> "GISPublicTransportClient":
    """Get or create the singleton GISPublicTransportClient instance.

    This reuses the same HTTP client across calls to avoid
    connection setup overhead.
    """
    global _public_transport_client_instance
    if _public_transport_client_instance is None:
        _public_transport_client_instance = GISPublicTransportClient()
    return _public_transport_client_instance


async def close_public_transport_client() -> None:
    """Close the singleton client. Call on application shutdown."""
    global _public_transport_client_instance
    if _public_transport_client_instance is not None:
        await _public_transport_client_instance.close()
        _public_transport_client_instance = None


class GISPublicTransportClient:
    """Client for 2GIS Public Transport Navigation API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = create_2gis_async_client(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_public_transport_route(
        self,
        source_point: tuple[float, float],
        target_point: tuple[float, float],
        source_name: str = "Start",
        target_name: str = "End",
        intermediate_points: Optional[list[tuple[float, float, str]]] = None,
        transport_types: Optional[list[str]] = None,
        locale: str = "en",
        include_pedestrian_instructions: bool = False,
    ) -> dict:
        """
        Calculate public transport route between two points.

        Args:
            source_point: (longitude, latitude) tuple for starting point
            target_point: (longitude, latitude) tuple for ending point
            source_name: Human-readable name for source
            target_name: Human-readable name for target
            intermediate_points: List of (longitude, latitude, name) tuples for waypoints
            transport_types: List of allowed transport types. Default: ["metro", "bus", "trolleybus", "tram"]
                Valid types: "bus", "trolleybus", "tram", "shuttle_bus", "metro",
                "suburban_train", "funicular", "monorail", "river_transport"
            locale: Language code for response (default: "en")
            include_pedestrian_instructions: Whether to include detailed walking instructions

        Returns:
            Dict with route alternatives, each containing:
            - total_duration: Total journey time in seconds
            - total_distance: Total distance in meters
            - walking_duration: Walking time in seconds
            - transfer_count: Number of transfers
            - movements: Array of journey segments
        """
        if not self.api_key:
            return {"error": "GIS_API_KEY not configured"}

        # Set default transport types if not provided
        if transport_types is None:
            transport_types = ["metro", "bus", "trolleybus", "tram"]

        # Build the request payload
        payload = {
            "source": {
                "point": {"lat": source_point[1], "lon": source_point[0]},
                "name": source_name,
            },
            "target": {
                "point": {"lat": target_point[1], "lon": target_point[0]},
                "name": target_name,
            },
            "transport": transport_types,
            "locale": locale,
            "enable_schedule": True,  # Enable schedule information
        }

        # Add intermediate points if provided
        if intermediate_points:
            payload["intermediate_points"] = [
                {
                    "point": {"lat": point[1], "lon": point[0]},
                    "name": point[2],
                }
                for point in intermediate_points
            ]

        # Add options if pedestrian instructions are requested
        if include_pedestrian_instructions:
            payload["options"] = ["pedestrian_instructions"]

        params = {"key": self.api_key}

        try:
            response = await self.client.post(
                PUBLIC_TRANSPORT_URL,
                params=params,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # Handle error responses
            if isinstance(data, dict) and ("error" in data or "error_code" in data):
                error_msg = data.get("error_message") or data.get("message") or str(data)
                return {"error": f"API error: {error_msg}", "details": data}

            # API returns a list of route alternatives or empty list
            if not isinstance(data, list):
                return {"error": f"Unexpected response format: {type(data)}", "details": data}

            if not data:
                return {"error": "No public transport routes found for this route"}

            # Process and return route alternatives
            return {
                "source": source_name,
                "target": target_name,
                "routes": [
                    self._parse_route(
                        route,
                        source_point=source_point,
                        target_point=target_point,
                        intermediate_points=intermediate_points,
                    )
                    for route in data
                ],
                "alternatives_count": len(data),
            }

        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error {e.response.status_code}",
                "details": str(e),
            }
        except Exception as e:
            return {
                "error": f"Public transport API error: {str(e)}",
                "details": str(e),
            }

    def _parse_route(
        self,
        route: dict,
        source_point: tuple[float, float],
        target_point: tuple[float, float],
        intermediate_points: Optional[list[tuple[float, float, str]]] = None,
    ) -> dict:
        """Parse a single route from the API response.

        Args:
            route: A route object from the API response

        Returns:
            Parsed route with summary, detailed movements, and geometry
        """
        movements = route.get("movements", [])
        total_duration = route.get("total_duration", 0)
        total_distance = route.get("total_distance", 0)
        walking_duration = route.get("walking_duration", 0)
        transfer_count = route.get("transfer_count", 0)
        schedules = route.get("schedules", [])

        # Get route-level transport info (names, colors)
        route_level_routes = route.get("routes", [])

        # Extract transport chain description
        transport_chain = self._extract_transport_chain(movements)
        route_geometry = self._extract_route_geometry(movements)
        if not route_geometry:
            route_geometry = self._fallback_geometry(
                source_point, target_point, intermediate_points
            )

        # Parse detailed movements and build geometry
        movement_details = []
        route_geometry: list[list[float]] = []
        route_info_index = 0  # Track which route info to use for each passage

        for movement in movements:
            mov_type = movement.get("type", "unknown")
            distance = movement.get("distance", 0)
            duration = movement.get("moving_duration", 0)

            # Skip empty finish markers
            waypoint = movement.get("waypoint", {})
            if not isinstance(waypoint, dict):
                waypoint = {}
            subtype = waypoint.get("subtype", "")
            if mov_type == "walkway" and subtype == "finish" and distance == 0:
                continue

            detail = {
                "type": mov_type,
                "subtype": subtype,
                "duration_seconds": duration,
                "distance_meters": distance,
                "from_name": waypoint.get("name", ""),
            }

            # Extract geometry from alternatives
            segment_geometry: list[list[float]] = []
            alternatives = movement.get("alternatives", [])

            if alternatives and isinstance(alternatives, list) and len(alternatives) > 0:
                alt = alternatives[0]
                if isinstance(alt, dict):
                    # geometry is an ARRAY of objects with 'selection' (WKT)
                    geometry_list = alt.get("geometry", [])
                    if isinstance(geometry_list, list):
                        for geom_obj in geometry_list:
                            if isinstance(geom_obj, dict):
                                wkt_string = geom_obj.get("selection", "")
                                if wkt_string:
                                    coords = parse_wkt(wkt_string)
                                    segment_geometry.extend(coords)

                    # platforms is an array with 'geometry' as WKT POINT string
                    platforms = alt.get("platforms", [])
                    if platforms and isinstance(platforms, list):
                        detail["stops_count"] = len(platforms)
                        platform_coords: list[list[float]] = []

                        for i, platform in enumerate(platforms):
                            if isinstance(platform, dict):
                                # Get platform name if available
                                plat_name = platform.get("name", "")
                                if i == 0 and plat_name:
                                    detail["from_stop"] = plat_name
                                elif i == len(platforms) - 1 and plat_name:
                                    detail["to_stop"] = plat_name

                                # geometry is a WKT string directly (e.g., "POINT(lon lat)")
                                plat_geom = platform.get("geometry", "")
                                if isinstance(plat_geom, str) and plat_geom:
                                    coords = parse_wkt(plat_geom)
                                    if coords:
                                        platform_coords.extend(coords)

                        # If no line geometry, use platform coordinates
                        if not segment_geometry and platform_coords:
                            segment_geometry = platform_coords

            # Get transport info from route-level 'routes' array
            if mov_type == "passage" and route_level_routes:
                if route_info_index < len(route_level_routes):
                    route_info = route_level_routes[route_info_index]
                    if isinstance(route_info, dict):
                        # names is an array of route names/numbers
                        names = route_info.get("names", [])
                        if names and isinstance(names, list):
                            detail["route_name"] = ", ".join(str(n) for n in names)
                        detail["transport_type"] = route_info.get("subtype", "transit")
                        detail["transport_type_name"] = route_info.get("subtype_name", "")
                        detail["route_color"] = route_info.get("color", "")
                    route_info_index += 1

            # Check for metro info (additional details from movement)
            if mov_type == "passage":
                metro = movement.get("metro", {})
                if metro and isinstance(metro, dict):
                    detail["transport_type"] = "metro"
                    detail["line_name"] = metro.get("line_name", "")
                    detail["line_color"] = metro.get("color", "") or detail.get("route_color", "")
                    detail["direction"] = metro.get("ui_direction_suggest", "")
                    detail["station_count"] = metro.get("ui_station_count", "")

            elif mov_type == "walkway":
                detail["transport_type"] = "walk"

            # Add geometry to detail and route
            if segment_geometry:
                detail["geometry"] = segment_geometry
                route_geometry.extend(segment_geometry)

            movement_details.append(detail)

        # Parse schedule information
        schedule_info = None
        if schedules and isinstance(schedules, list) and len(schedules) > 0:
            first_schedule = schedules[0]
            if isinstance(first_schedule, dict):
                schedule_info = {
                    "type": first_schedule.get("type", ""),
                    "period_minutes": first_schedule.get("period", 0) // 60 if first_schedule.get("period") else None,
                    "departure_time": first_schedule.get("precise_time", ""),
                    "start_time_utc": first_schedule.get("start_time_utc", 0),
                }

        return {
            "total_duration_seconds": total_duration,
            "total_distance_meters": total_distance,
            "walking_duration_seconds": walking_duration,
            "transfer_count": transfer_count,
            "transport_chain": transport_chain,
            "movements": movement_details,
            "route_geometry": route_geometry,
            "schedule": schedule_info,
        }

    def _extract_route_geometry(self, movements: list[dict]) -> list[list[float]]:
        """Extract route geometry by combining coordinates from movements."""
        coordinates: list[list[float]] = []

        for movement in movements or []:
            for point in self._extract_geometry_from_movement(movement):
                if not coordinates or coordinates[-1] != point:
                    coordinates.append(point)

        return coordinates

    def _extract_geometry_from_movement(self, movement: dict) -> list[list[float]]:
        candidates = []
        for key in ("geometry", "path", "paths", "track", "tracks", "line", "lines", "route", "routes", "polyline"):
            if key in movement:
                candidates.append(movement[key])

        coords: list[list[float]] = []
        for candidate in candidates:
            coords.extend(self._collect_coordinates(candidate))

        # Also check nested pedestrian instructions if present
        if not coords and "pedestrian_instructions" in movement:
            coords.extend(self._collect_coordinates(movement["pedestrian_instructions"]))

        return coords

    def _collect_coordinates(self, obj) -> list[list[float]]:
        coords: list[list[float]] = []

        if isinstance(obj, dict):
            if "lon" in obj and "lat" in obj:
                coords.append(self._normalize_pair(obj["lon"], obj["lat"]))
            if "longitude" in obj and "latitude" in obj:
                coords.append(self._normalize_pair(obj["longitude"], obj["latitude"]))
            if "point" in obj:
                coords.extend(self._collect_coordinates(obj["point"]))
            if "points" in obj:
                coords.extend(self._collect_coordinates(obj["points"]))
            if "geometry" in obj and obj["geometry"] is not obj:
                coords.extend(self._collect_coordinates(obj["geometry"]))
            if "polyline" in obj and isinstance(obj["polyline"], str):
                coords.extend(self._parse_linestring(obj["polyline"]))
            return coords

        if isinstance(obj, (list, tuple)):
            if len(obj) >= 2 and all(isinstance(val, (int, float)) for val in obj[:2]):
                coords.append(self._normalize_pair(obj[0], obj[1]))
            else:
                for item in obj:
                    coords.extend(self._collect_coordinates(item))
            return coords

        if isinstance(obj, str):
            coords.extend(self._parse_linestring(obj))

        return coords

    def _normalize_pair(self, first: float, second: float) -> list[float]:
        if abs(first) <= 90 and abs(second) > 90:
            return [second, first]
        return [first, second]

    def _parse_linestring(self, linestring: str) -> list[list[float]]:
        if "LINESTRING" not in linestring:
            return []

        text = linestring.strip()
        if text.startswith("LINESTRING"):
            text = text[text.find("(") + 1:text.rfind(")")]
        coords = []
        for pair in text.split(","):
            parts = pair.strip().split()
            if len(parts) < 2:
                continue
            try:
                lon = float(parts[0])
                lat = float(parts[1])
            except ValueError:
                continue
            coords.append([lon, lat])
        return coords

    def _fallback_geometry(
        self,
        source_point: tuple[float, float],
        target_point: tuple[float, float],
        intermediate_points: Optional[list[tuple[float, float, str]]] = None,
    ) -> list[list[float]]:
        points = [source_point]
        if intermediate_points:
            points.extend((pt[0], pt[1]) for pt in intermediate_points)
        points.append(target_point)
        return [[lon, lat] for lon, lat in points]

    def _extract_transport_chain(self, movements: list[dict]) -> str:
        """Extract transport types from movements to show the journey chain.

        Args:
            movements: List of movement objects from the API response

        Returns:
            String describing the transport chain (e.g., "Walk → Metro → Bus → Walk")
        """
        if not movements:
            return "No movements"

        chain = []

        for movement in movements:
            movement_type = movement.get("type", "unknown")

            if movement_type == "walkway":
                # Check if it's a finish marker (distance 0)
                distance = movement.get("distance", 0)
                waypoint = movement.get("waypoint", {})
                subtype = waypoint.get("subtype", "")

                # Skip empty finish markers
                if subtype == "finish" and distance == 0:
                    continue

                chain.append("Walk")

            elif movement_type == "passage":
                # Check for metro info first
                metro = movement.get("metro", {})
                if metro:
                    line_name = metro.get("line_name", "Metro")
                    chain.append(f"Metro ({line_name})")
                else:
                    # Check for routes array
                    routes = movement.get("routes", [])
                    if routes:
                        route_info = routes[0]
                        transport_type = route_info.get("type", "transit")
                        route_name = route_info.get("name", "")

                        # Map transport type to readable name
                        transport_map = {
                            "bus": "Bus",
                            "trolleybus": "Trolleybus",
                            "tram": "Tram",
                            "shuttle_bus": "Shuttle Bus",
                            "metro": "Metro",
                            "suburban_train": "Suburban Train",
                            "funicular": "Funicular",
                            "monorail": "Monorail",
                            "river_transport": "Ferry",
                        }
                        transport_name = transport_map.get(transport_type, transport_type.title())

                        if route_name:
                            chain.append(f"{transport_name} ({route_name})")
                        else:
                            chain.append(transport_name)
                    else:
                        chain.append("Transit")

            elif movement_type == "transfer":
                chain.append("Transfer")

        return " → ".join(chain) if chain else "Walking only"
