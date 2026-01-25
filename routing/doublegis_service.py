import httpx
from typing import List, Optional
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_BASE_URL, DOUBLEGIS_ROUTING_URL
from models import Place


class DoubleGISService:
    """Service for interacting with 2GIS API"""
    
    def __init__(self):
        self.api_key = DOUBLEGIS_API_KEY
        self.base_url = DOUBLEGIS_BASE_URL
        self.routing_url = DOUBLEGIS_ROUTING_URL
    
    async def search_places(self, query: str, city: str = "astana", limit: int = 10) -> List[Place]:
        """
        Search for places using 2GIS API
        
        Args:
            query: Search query (e.g., "restaurants", "museums")
            city: City to search in (use coordinates or region codes)
            limit: Maximum number of results
            
        Returns:
            List of Place objects
        """
        url = f"{self.base_url}/items"
        
        # Map common city names to coordinates (center of city)
        city_coords = {
            "astana": "71.430420,51.128207",   # Astana center (Bayterek)
            "almaty": "76.945465,43.238949",   # Almaty
            "moscow": "37.617635,55.755814",  # Moscow center
            "dubai": "55.296249,25.276987",    # Dubai
        }
        
        # Use coordinates if city is in map, otherwise use as-is
        location = city_coords.get(city.lower(), city)
        
        params = {
            "q": query,
            "location": location,
            "key": self.api_key,
            "page_size": limit,
            "fields": "items.point,items.address"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            places = []
            if "result" in data and "items" in data["result"]:
                for item in data["result"]["items"]:
                    if "point" in item:
                        place = Place(
                            id=item.get("id", ""),
                            name=item.get("name", "Unknown"),
                            address=item.get("address_name", ""),
                            lat=item["point"]["lat"],
                            lon=item["point"]["lon"],
                            type=item.get("type", "")
                        )
                        places.append(place)
            
            return places
    
    async def build_route(self, places: List[Place]) -> dict:
        """
        Build a route through multiple places using 2GIS Routing API (Distance Matrix)
        
        Args:
            places: List of Place objects to visit in order
            
        Returns:
            Dictionary with route information
        """
        if len(places) < 2:
            raise ValueError("Need at least 2 places to build a route")
        
        # 2GIS Distance Matrix API - works with POST and JSON body
        url = f"{self.routing_url}/get_dist_matrix"
        params = {
            "key": self.api_key,
            "version": "2.0"
        }
        
        # Build points array for the API
        points = [{"lat": place.lat, "lon": place.lon} for place in places]
        
        # For sequential routing, we need distances between consecutive points
        # sources: [0, 1, 2, ...] targets: [1, 2, 3, ...]
        sources = list(range(len(places) - 1))
        targets = list(range(1, len(places)))
        
        json_body = {
            "points": points,
            "sources": sources,
            "targets": targets
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, params=params, json=json_body)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Sum up distances and durations for all route segments
                    total_distance = 0
                    total_duration = 0
                    route_segments = []
                    
                    if "routes" in data:
                        for route in data["routes"]:
                            if route.get("status") == "OK":
                                total_distance += route.get("distance", 0)
                                total_duration += route.get("duration", 0)
                                route_segments.append({
                                    "from": sources[route["source_id"]] if route["source_id"] < len(sources) else route["source_id"],
                                    "to": route["target_id"],
                                    "distance": route.get("distance", 0),
                                    "duration": route.get("duration", 0)
                                })
                    
                    return {
                        "total_distance": total_distance,
                        "total_duration": total_duration,
                        "route_data": data,
                        "segments": route_segments
                    }
                else:
                    # Fallback: calculate simple straight-line distances
                    return await self._calculate_simple_route(places)
                    
            except Exception as e:
                # Fallback to simple calculation
                return await self._calculate_simple_route(places)
    
    async def _calculate_simple_route(self, places: List[Place]) -> dict:
        """
        Calculate simple distance and duration estimates between places
        Fallback when routing API is unavailable
        """
        import math
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance between two points in meters"""
            R = 6371000  # Earth radius in meters
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            
            a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
            return R * c
        
        total_distance = 0
        for i in range(len(places) - 1):
            dist = haversine_distance(
                places[i].lat, places[i].lon,
                places[i+1].lat, places[i+1].lon
            )
            total_distance += dist
        
        # Estimate duration (assume 30 km/h average speed in city)
        total_duration = int(total_distance / (30000 / 3600))
        
        return {
            "total_distance": int(total_distance),
            "total_duration": total_duration,
            "route_data": {"note": "Estimated distances (routing API unavailable)"}
        }
    
    def generate_route_url(self, places: List[Place]) -> str:
        """
        Generate a 2GIS URL that shows the route through places
        
        Args:
            places: List of Place objects
            
        Returns:
            URL string to view route on 2GIS
        """
        if not places:
            return ""
        
        # Create route points for URL
        points = [f"{place.lat},{place.lon}" for place in places]
        points_str = "/".join(points)
        
        # 2GIS map URL format
        base_map_url = "https://2gis.com/directions"
        return f"{base_map_url}?points={points_str}"
