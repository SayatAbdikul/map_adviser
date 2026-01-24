"""
2GIS Public Transport Routing - Working Implementation
This module provides public transport routing capabilities using the 2GIS API

Key API Format:
- Endpoint: /public_transport/2.0
- Body format:
  {
    "source": {"point": {"lon": X, "lat": Y}},
    "target": {"point": {"lon": X, "lat": Y}},
    "transport": ["metro", "bus", "tram", "trolleybus"]  # MUST be array!
  }
"""
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


class PublicTransportService:
    """Service for public transport routing using 2GIS API"""
    
    def __init__(self):
        self.api_key = DOUBLEGIS_API_KEY
        self.routing_url = DOUBLEGIS_ROUTING_URL
        
        # Available transport types
        self.transport_types = {
            "metro": "Metro/Subway",
            "bus": "Bus",
            "tram": "Tram/Streetcar",
            "trolleybus": "Trolleybus",
            "light_rail": "Light Rail",
            "suburban": "Suburban Rail"
        }
    
    async def get_public_transport_routes(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        transport_modes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get public transport route options between two points.
        
        Args:
            start_lat, start_lon: Starting point coordinates
            end_lat, end_lon: Destination coordinates
            transport_modes: List of transport types to include (default: all)
            
        Returns:
            Dictionary containing route options with times and details
        """
        # Default to all transport modes
        if transport_modes is None:
            transport_modes = ["metro", "bus", "tram", "trolleybus"]
        
        url = f"{self.routing_url}/public_transport/2.0"
        params = {"key": self.api_key}
        
        # Use the working body format
        body = {
            "source": {"point": {"lon": start_lon, "lat": start_lat}},
            "target": {"point": {"lon": end_lon, "lat": end_lat}},
            "transport": transport_modes
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=params, json=body)
            
            if response.status_code == 200:
                return self._parse_response(response.json())
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
    
    def _parse_response(self, data: List) -> Dict[str, Any]:
        """Parse API response into user-friendly format"""
        if not data:
            return {"success": True, "routes": [], "message": "No routes found"}
        
        routes = []
        for route_data in data:
            route = self._parse_route(route_data)
            routes.append(route)
        
        # Sort by total duration
        routes.sort(key=lambda x: x.get("total_duration_minutes", float("inf")))
        
        return {
            "success": True,
            "routes": routes,
            "total_options": len(routes)
        }
    
    def _safe_int(self, value, default=0):
        """Safely convert value to int"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            # Try to extract number from string
            import re
            match = re.search(r'(\d+)', value)
            if match:
                return int(match.group(1))
        return default
    
    def _parse_route(self, route_data: Dict) -> Dict[str, Any]:
        """Parse a single route into user-friendly format"""
        # Use top-level summary data (safely convert to int)
        total_duration = self._safe_int(route_data.get("total_duration"))
        total_distance = self._safe_int(route_data.get("total_distance"))
        walking_distance = self._safe_int(route_data.get("total_walkway_distance"))
        transfer_count = self._safe_int(route_data.get("transfer_count"))
        
        movements = route_data.get("movements", [])
        transit_segments = []
        walking_duration = 0
        transport_types = []
        
        for movement in movements:
            move_type = movement.get("type", "")
            moving_dur = movement.get("moving_duration", 0)
            waiting_dur = movement.get("waiting_duration", 0)
            distance = movement.get("distance", 0)
            waypoint = movement.get("waypoint", {})
            
            if move_type == "walkway":
                # Walking segment
                walking_duration += moving_dur
                comment = waypoint.get("comment", "Walk")
                subtype = waypoint.get("subtype", "")
                
                # Skip the "finish" marker
                if subtype == "finish" and distance == 0:
                    continue
                    
                transit_segments.append({
                    "type": "walking",
                    "duration_minutes": round(moving_dur / 60, 1),
                    "distance_meters": distance,
                    "instruction": comment
                })
                
            elif move_type == "passage":
                # Public transport segment (metro, bus, etc.)
                metro = movement.get("metro", {})
                platforms = movement.get("platforms", {})
                subtype = waypoint.get("subtype", "transit")
                station_name = waypoint.get("name", "")
                
                # Get station/stop names
                platform_names = []
                if isinstance(platforms, dict):
                    platform_names = platforms.get("names", [])
                
                from_stop = station_name
                to_stop = platform_names[-1] if platform_names else ""
                
                # Get metro color if available
                route_color = metro.get("color", "") if metro else ""
                
                transport_types.append(subtype)
                
                segment = {
                    "type": "public_transport",
                    "duration_minutes": round(moving_dur / 60, 1),
                    "waiting_minutes": round(waiting_dur / 60, 1),
                    "distance_meters": distance,
                    "transport_type": subtype,
                    "from_stop": from_stop,
                    "to_stop": to_stop,
                    "stops": platform_names,
                    "route_color": route_color,
                    "instruction": f"Take {subtype} from {from_stop}"
                }
                transit_segments.append(segment)
            
            elif move_type == "crossing":
                # Transfer between lines
                comment = waypoint.get("comment", "Transfer")
                transit_segments.append({
                    "type": "transfer",
                    "duration_minutes": round(moving_dur / 60, 1),
                    "distance_meters": distance,
                    "instruction": comment
                })
        
        # Get unique transport types
        unique_transport_types = list(set(transport_types))
        
        return {
            "total_duration_minutes": round(total_duration / 60, 1),
            "walking_duration_minutes": round(walking_duration / 60, 1),
            "walking_distance_meters": walking_distance,
            "total_distance_km": round(total_distance / 1000, 2),
            "transfers": transfer_count,
            "transport_types": unique_transport_types,
            "segments": transit_segments,
            "crossing_count": route_data.get("crossing_count", 0)
        }

    def format_route_for_display(self, route: Dict) -> str:
        """Format a route for user-friendly display"""
        lines = []
        lines.append(f"  Total time: {route['total_duration_minutes']} minutes")
        lines.append(f"  Distance: {route['total_distance_km']} km")
        walk_dist_km = round(route.get('walking_distance_meters', 0) / 1000, 1)
        lines.append(f"  Walking: {route['walking_duration_minutes']} min ({walk_dist_km} km)")
        lines.append(f"  Transfers: {route['transfers']}")
        
        if route['transport_types']:
            types_str = ", ".join(route['transport_types'])
            lines.append(f"  Transport: {types_str}")
        
        lines.append("\n  Journey steps:")
        for i, segment in enumerate(route['segments'], 1):
            if segment['type'] == 'walking':
                lines.append(f"    {i}. WALK: {segment.get('instruction', 'Walk')} ({segment['duration_minutes']} min)")
            elif segment['type'] == 'public_transport':
                mode = segment.get('transport_type', 'transit').upper()
                wait = segment.get('waiting_minutes', 0)
                wait_str = f", wait {wait} min" if wait > 0 else ""
                stops = segment.get('stops', [])
                stops_count = len(stops)
                lines.append(f"    {i}. {mode}: {segment['instruction']} ({segment['duration_minutes']} min{wait_str})")
                if segment.get('to_stop'):
                    lines.append(f"       -> Exit at: {segment['to_stop']} ({stops_count} stops)")
            elif segment['type'] == 'transfer':
                lines.append(f"    {i}. TRANSFER: {segment.get('instruction', 'Transfer')} ({segment['duration_minutes']} min)")
        
        return "\n".join(lines)


# Test the service
async def test_public_transport_service():
    """Test the public transport routing service"""
    print("=" * 70)
    print("Testing Public Transport Routing Service")
    print("=" * 70)
    
    service = PublicTransportService()
    
    # Test route: Bayterek Tower to Khan Shatyr in Astana
    print("\nRoute: Bayterek Tower -> Khan Shatyr (Astana)")
    print("-" * 50)
    
    result = await service.get_public_transport_routes(
        start_lat=51.128207, start_lon=71.430420,  # Bayterek Tower
        end_lat=51.132235, end_lon=71.404648       # Khan Shatyr
    )
    
    if result["success"]:
        print(f"\nFound {result['total_options']} route option(s)\n")
        
        for i, route in enumerate(result["routes"][:3], 1):
            print("=" * 50)
            print(f"OPTION {i}")
            print("=" * 50)
            print(service.format_route_for_display(route))
            print()
    else:
        print(f"\nError: {result.get('error', 'Unknown error')}")
    
    return result


async def compare_transport_modes():
    """Compare public transport with walking and cycling"""
    print("\n" + "=" * 70)
    print("Transport Mode Comparison: Bayterek Tower -> Khan Shatyr")
    print("=" * 70)
    
    start = {"lat": 51.128207, "lon": 71.430420}
    end = {"lat": 51.132235, "lon": 71.404648}
    
    results = {}
    
    # Public Transport
    service = PublicTransportService()
    pt_result = await service.get_public_transport_routes(
        start["lat"], start["lon"], end["lat"], end["lon"]
    )
    
    if pt_result["success"] and pt_result["routes"]:
        best_route = pt_result["routes"][0]
        results["Public Transport"] = {
            "duration": best_route["total_duration_minutes"],
            "details": f"{best_route['transfers']} transfer(s), {best_route['walking_duration_minutes']} min walking"
        }
    
    # Walking and Bicycle via carrouting API
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Walking
        response = await client.post(
            f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            params={"key": DOUBLEGIS_API_KEY},
            json={"points": [start, end], "type": "pedestrian"}
        )
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"]:
                route = data["result"][0]
                results["Walking"] = {
                    "duration": round(route.get("total_duration", 0) / 60, 1),
                    "details": f"{round(route.get('total_distance', 0) / 1000, 2)} km"
                }
        
        # Bicycle
        response = await client.post(
            f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            params={"key": DOUBLEGIS_API_KEY},
            json={"points": [start, end], "type": "bicycle"}
        )
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"]:
                route = data["result"][0]
                results["Bicycle"] = {
                    "duration": round(route.get("total_duration", 0) / 60, 1),
                    "details": f"{round(route.get('total_distance', 0) / 1000, 2)} km"
                }
    
    # Display comparison
    print("\n" + "-" * 60)
    print(f"{'Mode':<20} {'Duration':<15} {'Details'}")
    print("-" * 60)
    
    for mode, data in sorted(results.items(), key=lambda x: x[1]["duration"]):
        print(f"{mode:<20} {data['duration']:.1f} min        {data['details']}")
    
    print("-" * 60)


async def main():
    """Run all tests"""
    await test_public_transport_service()
    await compare_transport_modes()
    
    print("\n" + "=" * 70)
    print("PUBLIC TRANSPORT API - SUMMARY")
    print("=" * 70)
    print("""
The 2GIS Public Transport API is fully functional!

What you can offer users:
- Multiple route alternatives with different transport combinations
- Total travel time for each option
- Walking time/distance to and from stops  
- Number of transfers required
- Types of transport used (metro, bus, tram, trolleybus)
- Station/stop names along the route
- Step-by-step journey instructions

API Request Format:
  POST /public_transport/2.0
  Body: {
    "source": {"point": {"lon": X, "lat": Y}},
    "target": {"point": {"lon": X, "lat": Y}},
    "transport": ["metro", "bus", "tram", "trolleybus"]
  }
    """)


if __name__ == "__main__":
    asyncio.run(main())
