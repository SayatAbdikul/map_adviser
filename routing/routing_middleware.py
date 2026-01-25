"""
Routing Middleware
Accepts JSON of places, calls 2GIS routing APIs, returns route data to frontend
Supports: car, walking, bicycle, public_transport
"""
import httpx
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


class TransportMode(str, Enum):
    CAR = "car"
    WALKING = "pedestrian"
    BICYCLE = "bicycle"
    PUBLIC_TRANSPORT = "public_transport"


class RoutePoint(BaseModel):
    """A point on the route"""
    lat: float
    lon: float
    name: Optional[str] = None


class RoutingRequest(BaseModel):
    """Request model for routing"""
    points: List[RoutePoint]
    mode: TransportMode = TransportMode.CAR
    # Public transport specific options
    transport_types: Optional[List[str]] = None  # ["metro", "bus", "tram", "trolleybus"]


class RouteSegment(BaseModel):
    """A segment of the route"""
    from_point: RoutePoint
    to_point: RoutePoint
    distance_meters: int
    duration_seconds: int
    geometry: Optional[str] = None  # WKT or encoded polyline


class PublicTransportStep(BaseModel):
    """A step in public transport journey"""
    type: str  # walking, public_transport, transfer
    duration_minutes: float
    distance_meters: Optional[int] = None
    transport_type: Optional[str] = None  # metro, bus, etc.
    from_stop: Optional[str] = None
    to_stop: Optional[str] = None
    stops: Optional[List[str]] = None
    instruction: Optional[str] = None


class RoutingResponse(BaseModel):
    """Response model for routing"""
    success: bool
    mode: str
    total_distance_meters: int
    total_duration_seconds: int
    total_duration_text: str
    segments: Optional[List[RouteSegment]] = None
    # Public transport specific
    transfers: Optional[int] = None
    walking_duration_seconds: Optional[int] = None
    transport_types: Optional[List[str]] = None
    steps: Optional[List[PublicTransportStep]] = None
    # Alternative routes for public transport
    alternatives: Optional[List[Dict]] = None
    # Raw API response (for frontend flexibility) - use Any for flexibility
    raw_response: Optional[Any] = None
    error: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class RoutingMiddleware:
    """Middleware to handle all routing requests"""
    
    def __init__(self):
        self.api_key = DOUBLEGIS_API_KEY
        self.routing_url = DOUBLEGIS_ROUTING_URL
    
    async def get_route(self, request: RoutingRequest) -> RoutingResponse:
        """
        Main entry point - routes request to appropriate API based on mode
        """
        if len(request.points) < 2:
            return RoutingResponse(
                success=False,
                mode=request.mode,
                total_distance_meters=0,
                total_duration_seconds=0,
                total_duration_text="0 min",
                error="Need at least 2 points to build a route"
            )
        
        if request.mode == TransportMode.PUBLIC_TRANSPORT:
            return await self._get_public_transport_route(request)
        else:
            return await self._get_car_route(request)
    
    async def _get_car_route(self, request: RoutingRequest) -> RoutingResponse:
        """Get route for car, walking, or bicycle"""
        
        # For pedestrian and bicycle, use carrouting API
        if request.mode in [TransportMode.WALKING, TransportMode.BICYCLE]:
            return await self._get_pedestrian_bicycle_route(request)
        
        # For car, use distance matrix API
        return await self._get_car_distance_matrix(request)
    
    async def _get_pedestrian_bicycle_route(self, request: RoutingRequest) -> RoutingResponse:
        """Get pedestrian or bicycle route"""
        url = f"{self.routing_url}/carrouting/6.0.0/global"
        params = {"key": self.api_key}
        
        mode_map = {
            TransportMode.WALKING: "pedestrian",
            TransportMode.BICYCLE: "bicycle"
        }
        
        points = [{"lat": p.lat, "lon": p.lon} for p in request.points]
        
        body = {
            "points": points,
            "type": mode_map.get(request.mode, "pedestrian")
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url, params=params, json=body)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "result" in data and data["result"]:
                        route = data["result"][0]
                        total_distance = route.get("total_distance", 0)
                        total_duration = route.get("total_duration", 0)
                        
                        return RoutingResponse(
                            success=True,
                            mode=request.mode,
                            total_distance_meters=total_distance,
                            total_duration_seconds=total_duration,
                            total_duration_text=self._format_duration(total_duration),
                            raw_response=data
                        )
                
                return RoutingResponse(
                    success=False,
                    mode=request.mode,
                    total_distance_meters=0,
                    total_duration_seconds=0,
                    total_duration_text="0 min",
                    error=f"API error: {response.status_code}"
                )
                
            except Exception as e:
                return RoutingResponse(
                    success=False,
                    mode=request.mode,
                    total_distance_meters=0,
                    total_duration_seconds=0,
                    total_duration_text="0 min",
                    error=str(e)
                )
    
    async def _get_car_distance_matrix(self, request: RoutingRequest) -> RoutingResponse:
        """Get car route using distance matrix API"""
        url = f"{self.routing_url}/get_dist_matrix"
        params = {"key": self.api_key, "version": "2.0"}
        
        points = [{"lat": p.lat, "lon": p.lon} for p in request.points]
        
        # For sequential routing
        sources = list(range(len(points) - 1))
        targets = list(range(1, len(points)))
        
        body = {
            "points": points,
            "sources": sources,
            "targets": targets
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url, params=params, json=body)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    total_distance = 0
                    total_duration = 0
                    segments = []
                    all_found = True
                    
                    if "routes" in data:
                        for i, route in enumerate(data["routes"]):
                            if route.get("status") == "OK":
                                total_distance += route.get("distance", 0)
                                total_duration += route.get("duration", 0)
                                if i < len(request.points) - 1:
                                    segments.append(RouteSegment(
                                        from_point=request.points[i],
                                        to_point=request.points[i + 1],
                                        distance_meters=route.get("distance", 0),
                                        duration_seconds=route.get("duration", 0)
                                    ))
                            else:
                                all_found = False
                    
                    if total_distance > 0 or total_duration > 0:
                        return RoutingResponse(
                            success=True,
                            mode=request.mode,
                            total_distance_meters=total_distance,
                            total_duration_seconds=total_duration,
                            total_duration_text=self._format_duration(total_duration),
                            segments=segments if segments else None,
                            raw_response=data
                        )
                    else:
                        # Car route not found, fallback to estimate based on walking
                        return await self._estimate_car_from_walking(request)
                
                return RoutingResponse(
                    success=False,
                    mode=request.mode,
                    total_distance_meters=0,
                    total_duration_seconds=0,
                    total_duration_text="0 min",
                    error=f"API error: {response.status_code}"
                )
                
            except Exception as e:
                return RoutingResponse(
                    success=False,
                    mode=request.mode,
                    total_distance_meters=0,
                    total_duration_seconds=0,
                    total_duration_text="0 min",
                    error=str(e)
                )
    
    async def _estimate_car_from_walking(self, request: RoutingRequest) -> RoutingResponse:
        """Estimate car route based on pedestrian route (as fallback)"""
        # Get pedestrian route
        walk_request = RoutingRequest(
            points=request.points,
            mode=TransportMode.WALKING
        )
        walk_result = await self._get_pedestrian_bicycle_route(walk_request)
        
        if walk_result.success:
            # Estimate car: ~30km/h average vs ~5km/h walking
            # So car is roughly 6x faster, distance ~1.2x longer (roads vs paths)
            car_distance = int(walk_result.total_distance_meters * 1.2)
            car_duration = int(walk_result.total_duration_seconds / 5)  # More conservative
            
            return RoutingResponse(
                success=True,
                mode=request.mode,
                total_distance_meters=car_distance,
                total_duration_seconds=car_duration,
                total_duration_text=self._format_duration(car_duration),
                error="Estimated (car routing unavailable for this route)"
            )
        
        return RoutingResponse(
            success=False,
            mode=request.mode,
            total_distance_meters=0,
            total_duration_seconds=0,
            total_duration_text="0 min",
            error="Car routing unavailable"
        )
    
    async def _get_public_transport_route(self, request: RoutingRequest) -> RoutingResponse:
        """Get public transport route between two points"""
        # Public transport API only works between 2 points
        if len(request.points) != 2:
            return RoutingResponse(
                success=False,
                mode=request.mode,
                total_distance_meters=0,
                total_duration_seconds=0,
                total_duration_text="0 min",
                error="Public transport routing only supports 2 points (start and end)"
            )
        
        url = f"{self.routing_url}/public_transport/2.0"
        params = {"key": self.api_key}
        
        # Default transport types if not specified
        transport_types = request.transport_types or ["metro", "bus", "tram", "trolleybus"]
        
        body = {
            "source": {"point": {"lon": request.points[0].lon, "lat": request.points[0].lat}},
            "target": {"point": {"lon": request.points[1].lon, "lat": request.points[1].lat}},
            "transport": transport_types
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url, params=params, json=body)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        # Parse all route alternatives
                        alternatives = []
                        for route_data in data:
                            parsed = self._parse_public_transport_route(route_data)
                            alternatives.append(parsed)
                        
                        # Use the best (first) route for main response
                        best = alternatives[0]
                        
                        return RoutingResponse(
                            success=True,
                            mode=request.mode,
                            total_distance_meters=best["total_distance_meters"],
                            total_duration_seconds=best["total_duration_seconds"],
                            total_duration_text=self._format_duration(best["total_duration_seconds"]),
                            transfers=best["transfers"],
                            walking_duration_seconds=best["walking_duration_seconds"],
                            transport_types=best["transport_types"],
                            steps=best["steps"],
                            alternatives=alternatives,
                            raw_response=data
                        )
                    
                    return RoutingResponse(
                        success=True,
                        mode=request.mode,
                        total_distance_meters=0,
                        total_duration_seconds=0,
                        total_duration_text="0 min",
                        error="No public transport routes found",
                        raw_response=data
                    )
                
                return RoutingResponse(
                    success=False,
                    mode=request.mode,
                    total_distance_meters=0,
                    total_duration_seconds=0,
                    total_duration_text="0 min",
                    error=f"API error: {response.text}"
                )
                
            except Exception as e:
                return RoutingResponse(
                    success=False,
                    mode=request.mode,
                    total_distance_meters=0,
                    total_duration_seconds=0,
                    total_duration_text="0 min",
                    error=str(e)
                )
    
    def _parse_public_transport_route(self, route_data: Dict) -> Dict[str, Any]:
        """Parse a public transport route from API response"""
        total_duration = self._safe_int(route_data.get("total_duration", 0))
        total_distance = self._safe_int(route_data.get("total_distance", 0))
        transfer_count = self._safe_int(route_data.get("transfer_count", 0))
        
        movements = route_data.get("movements", [])
        steps = []
        walking_duration = 0
        transport_types_used = []
        
        for movement in movements:
            move_type = movement.get("type", "")
            moving_dur = movement.get("moving_duration", 0)
            waiting_dur = movement.get("waiting_duration", 0)
            distance = movement.get("distance", 0)
            waypoint = movement.get("waypoint", {})
            
            if move_type == "walkway":
                walking_duration += moving_dur
                subtype = waypoint.get("subtype", "")
                
                # Skip finish marker
                if subtype == "finish" and distance == 0:
                    continue
                
                steps.append(PublicTransportStep(
                    type="walking",
                    duration_minutes=round(moving_dur / 60, 1),
                    distance_meters=distance,
                    instruction=waypoint.get("comment", "Walk")
                ))
                
            elif move_type == "passage":
                platforms = movement.get("platforms", {})
                subtype = waypoint.get("subtype", "transit")
                station_name = waypoint.get("name", "")
                
                platform_names = []
                if isinstance(platforms, dict):
                    platform_names = platforms.get("names", [])
                
                transport_types_used.append(subtype)
                
                steps.append(PublicTransportStep(
                    type="public_transport",
                    duration_minutes=round(moving_dur / 60, 1),
                    distance_meters=distance,
                    transport_type=subtype,
                    from_stop=station_name,
                    to_stop=platform_names[-1] if platform_names else "",
                    stops=platform_names,
                    instruction=f"Take {subtype} from {station_name}"
                ))
                
            elif move_type == "crossing":
                steps.append(PublicTransportStep(
                    type="transfer",
                    duration_minutes=round(moving_dur / 60, 1),
                    distance_meters=distance,
                    instruction=waypoint.get("comment", "Transfer")
                ))
        
        return {
            "total_distance_meters": total_distance,
            "total_duration_seconds": total_duration,
            "transfers": transfer_count,
            "walking_duration_seconds": walking_duration,
            "transport_types": list(set(transport_types_used)),
            "steps": steps
        }
    
    def _safe_int(self, value, default=0):
        """Safely convert value to int"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            import re
            match = re.search(r'(\d+)', value)
            if match:
                return int(match.group(1))
        return default
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable string"""
        if seconds < 60:
            return f"{seconds} sec"
        elif seconds < 3600:
            minutes = round(seconds / 60)
            return f"{minutes} min"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}min"
            return f"{hours}h"


# Create singleton instance
routing_middleware = RoutingMiddleware()


async def get_directions(
    points: List[Dict[str, float]],
    mode: str = "car",
    transport_types: List[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to get directions
    
    Args:
        points: List of dicts with 'lat', 'lon' keys and optional 'name'
        mode: One of 'car', 'walking', 'bicycle', 'public_transport'
        transport_types: For public transport - list of types to use
        
    Returns:
        Dictionary with route information
    """
    route_points = [
        RoutePoint(lat=p["lat"], lon=p["lon"], name=p.get("name"))
        for p in points
    ]
    
    mode_enum = TransportMode(mode) if mode in [m.value for m in TransportMode] else TransportMode.CAR
    
    request = RoutingRequest(
        points=route_points,
        mode=mode_enum,
        transport_types=transport_types
    )
    
    response = await routing_middleware.get_route(request)
    return response.dict()
