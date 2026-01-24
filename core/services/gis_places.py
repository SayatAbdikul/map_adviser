"""2GIS Places API client for searching places and geocoding."""

import os
from typing import Optional

import httpx

BASE_URL = "https://catalog.api.2gis.com/3.0"
GEOCODE_URL = "https://catalog.api.2gis.com/3.0/items/geocode"

# Singleton instance for connection reuse
_places_client_instance: Optional["GISPlacesClient"] = None


def get_api_key() -> str:
    """Get API key lazily to ensure .env is loaded first."""
    return os.getenv("GIS_API_KEY", "")


def get_places_client() -> "GISPlacesClient":
    """Get or create the singleton GISPlacesClient instance.
    
    This reuses the same HTTP client across calls to avoid
    connection setup overhead.
    """
    global _places_client_instance
    if _places_client_instance is None:
        _places_client_instance = GISPlacesClient()
    return _places_client_instance


async def close_places_client() -> None:
    """Close the singleton client. Call on application shutdown."""
    global _places_client_instance
    if _places_client_instance is not None:
        await _places_client_instance.close()
        _places_client_instance = None


class GISPlacesClient:
    """Client for 2GIS Places/Catalog API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def geocode(self, address: str, city: Optional[str] = None) -> dict:
        """
        Convert address string to coordinates.

        Args:
            address: Address string to geocode
            city: Optional city name to narrow search

        Returns:
            Dict with name, address, coordinates (lon, lat)
        """
        params = {
            "key": self.api_key,
            "q": address,
            "fields": "items.point,items.full_name,items.address_name",
            "type": "building,street,adm_div,attraction",
        }

        if city:
            params["q"] = f"{city}, {address}"

        response = await self.client.get(f"{BASE_URL}/items", params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("result", {}).get("items"):
            return {"error": f"No results found for address: {address}"}

        item = data["result"]["items"][0]
        point = item.get("point", {})

        return {
            "name": item.get("full_name", item.get("name", address)),
            "address": item.get("address_name", address),
            "coordinates": [point.get("lon"), point.get("lat")],
        }

    async def search_places(
        self,
        query: str,
        location: tuple[float, float],
        radius: int = 5000,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search for places by category/name near a location.

        Args:
            query: Search query (e.g., "bank", "cafe", "pharmacy")
            location: Tuple of (longitude, latitude)
            radius: Search radius in meters (default 5000)
            limit: Maximum number of results (default 5)

        Returns:
            List of places with name, address, coordinates, rating
        """
        lon, lat = location
        params = {
            "key": self.api_key,
            "q": query,
            "point": f"{lon},{lat}",
            "radius": radius,
            "page_size": limit,
            "fields": "items.point,items.full_name,items.address_name,items.reviews,items.schedule",
            "type": "branch,building,attraction",
            "sort_point": f"{lon},{lat}",
            "sort": "distance",
        }

        response = await self.client.get(f"{BASE_URL}/items", params=params)
        response.raise_for_status()
        data = response.json()

        places = []
        for item in data.get("result", {}).get("items", []):
            point = item.get("point", {})
            reviews = item.get("reviews", {})

            places.append({
                "id": item.get("id"),
                "name": item.get("full_name", item.get("name", query)),
                "address": item.get("address_name", ""),
                "coordinates": [point.get("lon"), point.get("lat")],
                "rating": reviews.get("rating"),
                "review_count": reviews.get("count", 0),
            })

        return places

    async def search_places_along_route(
        self,
        query: str,
        start: tuple[float, float],
        end: tuple[float, float],
        limit: int = 5,
    ) -> list[dict]:
        """
        Search for places along a route between two points.

        This finds places that minimize detour from the direct route.

        Args:
            query: Search query (e.g., "bank", "cafe")
            start: Starting point (lon, lat)
            end: Ending point (lon, lat)

        Returns:
            List of places sorted by how much they add to the route
        """
        # Calculate midpoint for initial search
        mid_lon = (start[0] + end[0]) / 2
        mid_lat = (start[1] + end[1]) / 2

        # Calculate approximate search radius (half the distance between points)
        import math

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        # Rough distance in meters (approximate for small distances)
        distance = math.sqrt(dx**2 + dy**2) * 111000  # degrees to meters
        radius = max(int(distance / 2), 2000)  # At least 2km radius

        return await self.search_places(query, (mid_lon, mid_lat), radius=radius, limit=limit)


# Convenience functions using shared client
async def geocode_address(address: str, city: Optional[str] = None) -> dict:
    """Geocode an address to coordinates."""
    client = get_places_client()
    return await client.geocode(address, city)


async def search_nearby_places(
    query: str,
    location: tuple[float, float],
    radius: int = 5000,
    limit: int = 5,
) -> list[dict]:
    """Search for places near a location."""
    client = get_places_client()
    return await client.search_places(query, location, radius, limit)
