"""2GIS Regions API client for searching and managing geographic regions."""

import os
from typing import Optional

import httpx

BASE_URL = "https://catalog.api.2gis.com/2.0"
REGION_SEARCH_URL = f"{BASE_URL}/region/search"
REGION_GET_URL = f"{BASE_URL}/region/get"

# Singleton instance for connection reuse
_regions_client_instance: Optional["GISRegionsClient"] = None


def get_api_key() -> str:
    """Get API key lazily to ensure .env is loaded first."""
    return os.getenv("GIS_API_KEY", "")


def get_regions_client() -> "GISRegionsClient":
    """Get or create the singleton GISRegionsClient instance.

    This reuses the same HTTP client across calls to avoid
    connection setup overhead.
    """
    global _regions_client_instance
    if _regions_client_instance is None:
        _regions_client_instance = GISRegionsClient()
    return _regions_client_instance


async def close_regions_client() -> None:
    """Close the singleton client. Call on application shutdown."""
    global _regions_client_instance
    if _regions_client_instance is not None:
        await _regions_client_instance.close()
        _regions_client_instance = None


class GISRegionsClient:
    """Client for 2GIS Regions API (version 2.0).

    The Regions API provides information about geographic regions supported by 2GIS,
    including cities, countries, and administrative divisions. It can be used to:
    - Search for regions by name or coordinates
    - Get region IDs to limit searches in the Places API
    - Retrieve region metadata (bounds, timezone, statistics)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def search_by_name(
        self,
        query: str,
        region_type: str = "region",
        include_bounds: bool = False,
    ) -> list[dict]:
        """
        Search for regions by name.

        Args:
            query: City or region name to search for (e.g., "Almaty", "Moscow")
            region_type: Type of region to search for:
                - "region": Cities and regions (default)
                - "segment": Districts and settlements
            include_bounds: Whether to include geographic bounding box

        Returns:
            List of matching regions with id, name, country, and optionally bounds
        """
        params = {
            "key": self.api_key,
            "q": query,
            "type": region_type,
        }

        if include_bounds:
            params["fields"] = "items.bounds"

        response = await self.client.get(REGION_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

        regions = []
        for item in data.get("result", {}).get("items", []):
            region = {
                "id": item.get("id"),
                "name": item.get("name"),
                "type": item.get("type"),
                "country_code": item.get("country_code"),
            }

            if include_bounds and "bounds" in item:
                region["bounds"] = item["bounds"]

            regions.append(region)

        return regions

    async def search_by_coordinates(
        self,
        longitude: float,
        latitude: float,
        region_type: str = "region",
    ) -> Optional[dict]:
        """
        Find which region contains the given coordinates (reverse geocoding).

        Args:
            longitude: Longitude of the point
            latitude: Latitude of the point
            region_type: Type of region ("region" or "segment")

        Returns:
            The region containing the coordinates, or None
        """
        # 2GIS uses "longitude,latitude" format
        params = {
            "key": self.api_key,
            "q": f"{longitude},{latitude}",
            "type": region_type,
        }

        response = await self.client.get(REGION_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

        items = data.get("result", {}).get("items", [])
        if not items:
            return None

        item = items[0]
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
            "country_code": item.get("country_code"),
        }

    async def get_by_id(
        self,
        region_id: str,
        include_details: bool = False,
    ) -> Optional[dict]:
        """
        Get detailed region information by ID.

        Args:
            region_id: The unique numeric ID of the region
            include_details: Whether to include statistics and flags

        Returns:
            Region details or None if not found
        """
        params = {
            "key": self.api_key,
            "id": region_id,
        }

        if include_details:
            params["fields"] = "items.flags,items.statistics,items.bounds,items.time_zone"

        response = await self.client.get(REGION_GET_URL, params=params)
        response.raise_for_status()
        data = response.json()

        items = data.get("result", {}).get("items", [])
        if not items:
            return None

        item = items[0]
        region = {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
            "country_code": item.get("country_code"),
        }

        if include_details:
            if "bounds" in item:
                region["bounds"] = item["bounds"]
            if "time_zone" in item:
                region["time_zone"] = item["time_zone"]
            if "statistics" in item:
                region["statistics"] = item["statistics"]
            if "flags" in item:
                region["flags"] = item["flags"]

        return region

    async def validate_location_in_region(
        self,
        longitude: float,
        latitude: float,
        expected_region_id: int,
    ) -> dict:
        """
        Check if coordinates are within the expected region.

        Args:
            longitude: Longitude of the point
            latitude: Latitude of the point
            expected_region_id: The region ID we expect the point to be in

        Returns:
            Dict with:
            - is_valid: True if location is in the expected region
            - actual_region: The region the coordinates are actually in
            - expected_region_id: The expected region ID
            - message: Human-readable message about the validation
        """
        actual_region = await self.search_by_coordinates(longitude, latitude)

        if actual_region is None:
            return {
                "is_valid": False,
                "actual_region": None,
                "expected_region_id": expected_region_id,
                "message": f"Could not determine region for coordinates ({longitude}, {latitude})",
            }

        actual_region_id = actual_region.get("id")
        is_valid = actual_region_id == expected_region_id

        if is_valid:
            message = f"Location is within {actual_region.get('name')}"
        else:
            # Get expected region name
            expected_region = await self.get_by_id(str(expected_region_id))
            expected_name = expected_region.get("name") if expected_region else f"region {expected_region_id}"
            message = f"Location is in {actual_region.get('name')}, not in {expected_name}"

        return {
            "is_valid": is_valid,
            "actual_region": actual_region,
            "expected_region_id": expected_region_id,
            "message": message,
        }


# Convenience functions using shared client
async def search_region(query: str, include_bounds: bool = False) -> list[dict]:
    """Search for regions by name."""
    client = get_regions_client()
    return await client.search_by_name(query, include_bounds=include_bounds)


async def get_region_for_coordinates(
    longitude: float, latitude: float
) -> Optional[dict]:
    """Find which region contains the given coordinates."""
    client = get_regions_client()
    return await client.search_by_coordinates(longitude, latitude)
