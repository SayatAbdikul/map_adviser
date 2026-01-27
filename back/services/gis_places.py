"""2GIS Places API client for searching places and geocoding."""

import logging
import os
from typing import Optional

from services.gis_rate_limiter import create_2gis_async_client

logger = logging.getLogger(__name__)

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
        self.client = create_2gis_async_client(timeout=90.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()



    async def geocode(
        self,
        address: str,
        city: Optional[str] = None,
        region_id: Optional[int] = None,
        validate_region: bool = True,
    ) -> dict:
        """
        Convert address string to coordinates.

        Args:
            address: Address string to geocode
            city: Optional city name to narrow search
            region_id: Optional region ID to limit search to a specific region
            validate_region: Whether to validate that result is in the specified region

        Returns:
            Dict with name, address, coordinates (lon, lat).
            If region_id is provided and result is outside region, includes:
            - region_warning: Warning message
            - actual_region: The region the result is actually in
        """
        params = {
            "key": self.api_key,
            "q": address,
            "fields": "items.point,items.full_name,items.address_name",
            "type": "building,street,adm_div,attraction",
        }

        if city:
            params["q"] = f"{city}, {address}"

        if region_id:
            params["region_id"] = region_id

        response = await self.client.get(f"{BASE_URL}/items", params=params)
        if response.status_code >= 400:
            logger.error(f"Geocode API error: {response.status_code} - {response.text}")
            return {"error": f"Geocode service error: {response.status_code}"}
        data = response.json()

        if not data.get("result", {}).get("items"):
            if region_id:
                # Try searching without region_id to see if address exists elsewhere
                params_no_region = {k: v for k, v in params.items() if k != "region_id"}
                response_no_region = await self.client.get(f"{BASE_URL}/items", params=params_no_region)
                data_no_region = response_no_region.json()

                if data_no_region.get("result", {}).get("items"):
                    # Address exists but not in the specified region
                    from services.gis_regions import get_regions_client
                    regions_client = get_regions_client()

                    item = data_no_region["result"]["items"][0]
                    point = item.get("point", {})
                    lon, lat = point.get("lon"), point.get("lat")

                    if lon and lat:
                        actual_region = await regions_client.search_by_coordinates(lon, lat)
                        expected_region = await regions_client.get_by_id(str(region_id))
                        expected_name = expected_region.get("name") if expected_region else f"region {region_id}"
                        actual_name = actual_region.get("name") if actual_region else "unknown region"

                        return {
                            "error": f"Address '{address}' not found in {expected_name}",
                            "region_warning": f"This address exists in {actual_name}, not in {expected_name}",
                            "actual_region": actual_region,
                            "suggestion": {
                                "name": item.get("full_name", item.get("name", address)),
                                "address": item.get("address_name", address),
                                "coordinates": [lon, lat],
                            }
                        }

            return {"error": f"No results found for address: {address}"}

        item = data["result"]["items"][0]
        point = item.get("point", {})
        lon, lat = point.get("lon"), point.get("lat")

        result = {
            "name": item.get("full_name", item.get("name", address)),
            "address": item.get("address_name", address),
            "coordinates": [lon, lat],
        }

        # Validate that result is in the expected region
        if region_id and validate_region and lon and lat:
            from services.gis_regions import get_regions_client
            regions_client = get_regions_client()

            validation = await regions_client.validate_location_in_region(lon, lat, region_id)

            if not validation["is_valid"]:
                result["region_warning"] = validation["message"]
                result["actual_region"] = validation["actual_region"]

        return result

    async def search_places(
        self,
        query: str,
        location: Optional[tuple[float, float]] = None,
        radius: int = 5000,
        limit: int = 5,
        region_id: Optional[int] = None,
        validate_region: bool = True,
    ) -> dict | list[dict]:
        """
        Search for places by category/name near a location or within a region.

        Args:
            query: Search query (e.g., "bank", "cafe", "pharmacy")
            location: Optional tuple of (longitude, latitude) for location-based search
            radius: Search radius in meters (default 5000, used with location)
            limit: Maximum number of results (default 5)
            region_id: Optional region ID to limit search to a specific region
            validate_region: Whether to validate that results are in the specified region

        Returns:
            List of places with name, address, coordinates, rating.
            If region_id is provided and no results found, returns dict with error
            and suggestions from other regions.
        """
        params = {
            "key": self.api_key,
            "q": query,
            "page_size": limit,
            "fields": "items.point,items.full_name,items.address_name,items.reviews,items.schedule",
            "type": "branch,building,attraction",
        }

        if location:
            lon, lat = location
            params["point"] = f"{lon},{lat}"
            params["radius"] = radius
            params["sort_point"] = f"{lon},{lat}"
            params["sort"] = "distance"

        if region_id:
            params["region_id"] = region_id

        response = await self.client.get(f"{BASE_URL}/items", params=params)
        if response.status_code >= 400:
            logger.error(f"Search API error: {response.status_code} - {response.text}")
            return []
        data = response.json()
        # print('response data', data)

        items = data.get("result", {}).get("items", [])

        # If no results with region_id, check if they exist elsewhere
        if not items and region_id:
            params_no_region = {k: v for k, v in params.items() if k != "region_id"}
            response_no_region = await self.client.get(f"{BASE_URL}/items", params=params_no_region)
            data_no_region = response_no_region.json()
            items_elsewhere = data_no_region.get("result", {}).get("items", [])

            if items_elsewhere:
                from services.gis_regions import get_regions_client
                regions_client = get_regions_client()

                expected_region = await regions_client.get_by_id(str(region_id))
                expected_name = expected_region.get("name") if expected_region else f"region {region_id}"

                # Get regions for first few results
                suggestions = []
                for item in items_elsewhere[:3]:
                    point = item.get("point", {})
                    lon, lat = point.get("lon"), point.get("lat")

                    if lon and lat:
                        actual_region = await regions_client.search_by_coordinates(lon, lat)
                        suggestions.append({
                            "name": item.get("full_name", item.get("name", query)),
                            "address": item.get("address_name", ""),
                            "coordinates": [lon, lat],
                            "region": actual_region.get("name") if actual_region else "unknown",
                        })

                return {
                    "error": f"No '{query}' found in {expected_name}",
                    "region_warning": f"Results exist in other regions but not in {expected_name}",
                    "suggestions_outside_region": suggestions,
                }

            return []

        places = []
        for item in items:
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
