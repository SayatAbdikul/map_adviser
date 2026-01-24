"""2GIS Public Transport API client for calculating public transport routes."""

import os
from typing import Literal, Optional

import httpx

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
        self.client = httpx.AsyncClient(timeout=30.0)

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
                "routes": [self._parse_route(route) for route in data],
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

    def _parse_route(self, route: dict) -> dict:
        """Parse a single route from the API response.

        Args:
            route: A route object from the API response

        Returns:
            Parsed route with summary and detailed movements
        """
        movements = route.get("movements", [])
        total_duration = route.get("total_duration", 0)
        total_distance = route.get("total_distance", 0)
        walking_duration = route.get("walking_duration", 0)
        transfer_count = route.get("transfer_count", 0)

        # Extract transport chain description
        transport_chain = self._extract_transport_chain(movements)

        # Parse detailed movements
        movement_details = []
        for movement in movements:
            mov_type = movement.get("type", "unknown")
            distance = movement.get("distance", 0)
            duration = movement.get("moving_duration", 0)

            # Skip empty finish markers
            waypoint = movement.get("waypoint", {})
            subtype = waypoint.get("subtype", "")
            if mov_type == "walkway" and subtype == "finish" and distance == 0:
                continue

            detail = {
                "type": mov_type,
                "duration_seconds": duration,
                "distance_meters": distance,
            }

            # Add transit-specific details
            if mov_type == "passage":
                # Check for metro info
                metro = movement.get("metro", {})
                if metro:
                    detail["transport_type"] = "metro"
                    detail["line_name"] = metro.get("line_name", "Metro")
                    detail["direction"] = metro.get("ui_direction_suggest", "")
                else:
                    # Check for regular transport routes
                    routes = movement.get("routes", [])
                    if routes:
                        route_info = routes[0]
                        detail["transport_type"] = route_info.get("type", "transit")
                        detail["route_name"] = route_info.get("name", "")

                # Count platforms/stops
                alternatives = movement.get("alternatives", [])
                if alternatives:
                    platforms = alternatives[0].get("platforms", [])
                    detail["stops_count"] = len(platforms) if platforms else 0

            movement_details.append(detail)

        return {
            "total_duration_seconds": total_duration,
            "total_distance_meters": total_distance,
            "walking_duration_seconds": walking_duration,
            "transfer_count": transfer_count,
            "transport_chain": transport_chain,
            "movements": movement_details,
        }

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
