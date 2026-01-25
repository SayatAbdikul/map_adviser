#!/usr/bin/env python3
"""
2GIS Regions API (API 2.0) Demonstration Suite

This script demonstrates various ways to interact with the 2GIS Regions API,
including text search, coordinate-based search (reverse geocoding), detailed
field retrieval, and region lookup by ID.

The Regions API provides information about geographic regions supported by 2GIS,
including cities, countries, and administrative divisions.

Author: API Demo Suite
Date: 2026
"""

import requests
import json
import os
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode


# =============================================================================
# CONFIGURATION
# =============================================================================

# API Key for 2GIS Regions API
# Load from environment variable for security; fall back to placeholder for documentation
# Set your API key: export TWOGIS_API_KEY="your_api_key_here"
API_KEY = os.environ.get("TWOGIS_API_KEY", "YOUR_API_KEY_HERE")

# Common placeholder patterns that indicate an unconfigured API key
_INVALID_KEY_PATTERNS = [
    "YOUR_API_KEY_HERE",
    "your_api_key_here", 
    "YOUR_API_KEY",
    "your_api_key",
    "API_KEY",
    "api_key",
    "REPLACE_ME",
    "xxx",
    ""
]

# Base URL for the 2GIS Catalog API (Regions use version 2.0)
BASE_URL = "https://catalog.api.2gis.com/2.0"

# Endpoints
REGION_SEARCH_ENDPOINT = f"{BASE_URL}/region/search"
REGION_GET_ENDPOINT = f"{BASE_URL}/region/get"


# =============================================================================
# REGIONS API CLIENT CLASS
# =============================================================================

class TwoGISRegionsClient:
    """
    A client class for interacting with the 2GIS Regions API.
    
    This class provides methods for searching regions by name or coordinates,
    and retrieving detailed region information by ID.
    
    The Regions API (version 2.0) is separate from the Places/Items API (version 3.0)
    and focuses on geographic region metadata rather than business listings.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the 2GIS Regions API client.
        
        Args:
            api_key: Your 2GIS API key for authentication.
        """
        self.api_key = api_key
        self.search_url = REGION_SEARCH_ENDPOINT
        self.get_url = REGION_GET_ENDPOINT
    
    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        test_name: str,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a request to the 2GIS API and handle the response.
        
        This helper function builds the URL, sends the request, handles errors,
        and returns the parsed JSON response. Includes retry logic with
        exponential backoff for transient failures.
        
        Args:
            endpoint: The API endpoint URL.
            params: Dictionary of query parameters.
            test_name: Human-readable name of the test being performed.
            max_retries: Maximum number of retry attempts for transient errors.
            base_delay: Base delay in seconds for exponential backoff.
            
        Returns:
            Parsed JSON response as a dictionary, or None if an error occurred.
        """
        # Add API key to parameters (required for authentication)
        params['key'] = self.api_key
        
        # Build the full URL with query parameters for display
        full_url = f"{endpoint}?{urlencode(params)}"
        
        # Print test header and request information
        print("\n" + "=" * 80)
        print(f"--- TEST: {test_name} ---")
        print("=" * 80)
        print(f"[REQUEST]: GET {full_url}")
        
        for attempt in range(max_retries):
            try:
                # Send the GET request
                response = requests.get(endpoint, params=params, timeout=30)
                
                # Handle rate limiting (429) with retry
                if response.status_code == 429:
                    # Parse Retry-After header safely; fall back to exponential backoff
                    try:
                        retry_after = int(response.headers.get('Retry-After', ''))
                    except (ValueError, TypeError):
                        retry_after = int(base_delay * (2 ** attempt))
                    
                    if attempt < max_retries - 1:
                        print(f"[WARNING]: Rate limited (429). Retrying in {retry_after}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_after)
                        continue
                    else:
                        print(f"[STATUS]: 429 Too Many Requests")
                        print(f"[ERROR]: Rate limit exceeded. Please try again later.")
                        return None
                
                # Handle server errors (5xx) with retry
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[WARNING]: Server error ({response.status_code}). Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"[STATUS]: {response.status_code} Server Error")
                        print(f"[ERROR]: Server error after {max_retries} attempts.")
                        return None
                
                # Print status
                status_text = f"{response.status_code} {'OK' if response.status_code == 200 else response.reason}"
                print(f"[STATUS]: {status_text}")
                
                # Check for non-200 status codes
                if response.status_code != 200:
                    print(f"[ERROR]: Request failed with status {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"[RESPONSE]:\n{json.dumps(error_data, indent=4, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        print(f"[RESPONSE]: {response.text[:500]}")
                    return None
                
                # Parse JSON response
                data = response.json()
                
                # Pretty-print the full JSON response
                print(f"[RESPONSE]:\n{json.dumps(data, indent=4, ensure_ascii=False)}")
                
                return data
                
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[WARNING]: Connection error. Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[STATUS]: Connection Error")
                    print(f"[ERROR]: Could not connect to the API server after {max_retries} attempts.")
                    return None
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[WARNING]: Request timeout. Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[STATUS]: Timeout")
                    print(f"[ERROR]: Request timed out after {max_retries} attempts.")
                    return None
                
            except requests.exceptions.RequestException as e:
                print(f"[STATUS]: Request Error")
                print(f"[ERROR]: {e}")
                return None
                
            except json.JSONDecodeError:
                print(f"[STATUS]: JSON Parse Error")
                print(f"[ERROR]: Could not parse the API response as JSON.")
                return None
        
        return None
    
    def search_by_name(
        self,
        query: str,
        fields: Optional[str] = None,
        region_type: str = "region"
    ) -> Optional[Dict[str, Any]]:
        """
        Search for regions by name (text query).
        
        This method searches for regions matching a city or region name.
        
        Args:
            query: Text query - a city or region name (e.g., "Moscow", "Dubai").
            fields: Extra fields to retrieve (comma-separated).
                    Available fields include:
                    - items.bounds: Geographic bounding box of the region
                    - items.time_zone: Time zone information
                    - items.code: Region code
                    - items.country_code: ISO country code
                    - items.statistics: Population and other statistics
                    - items.flags: Feature flags for the region
            region_type: Type of region to search for:
                        - "region": Cities and regions (default)
                        - "segment": Districts and settlements
            
        Returns:
            Parsed JSON response or None if an error occurred.
        """
        params = {
            'q': query,
            'type': region_type
        }
        
        if fields:
            params['fields'] = fields
        
        test_name = f"Searching for Region by Name: '{query}'"
        return self._make_request(self.search_url, params, test_name)
    
    def search_by_coordinates(
        self,
        longitude: float,
        latitude: float,
        fields: Optional[str] = None,
        region_type: str = "region"
    ) -> Optional[Dict[str, Any]]:
        """
        Search for regions by coordinates (reverse geocoding).
        
        This method finds which region contains the given coordinates.
        The coordinates are passed in "longitude,latitude" format as per 2GIS convention.
        
        Args:
            longitude: Longitude of the point (e.g., 37.62 for Moscow).
            latitude: Latitude of the point (e.g., 55.75 for Moscow).
            fields: Extra fields to retrieve (comma-separated).
            region_type: Type of region to search for ("region" or "segment").
            
        Returns:
            Parsed JSON response or None if an error occurred.
        """
        # 2GIS uses "longitude,latitude" format (longitude first!)
        params = {
            'q': f"{longitude},{latitude}",
            'type': region_type
        }
        
        if fields:
            params['fields'] = fields
        
        test_name = f"Searching for Region by Coordinates: lon={longitude}, lat={latitude}"
        return self._make_request(self.search_url, params, test_name)
    
    def get_by_id(
        self,
        region_id: str,
        fields: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed region information by ID.
        
        This method retrieves comprehensive information about a specific region
        using its unique numeric identifier.
        
        Args:
            region_id: The unique numeric ID of the region (e.g., "32" for Moscow).
            fields: Extra fields to retrieve (comma-separated).
                    Useful fields for this endpoint:
                    - items.flags: Feature flags indicating what's available in the region
                    - items.statistics: Population and other statistics
                    - items.bounds: Geographic bounding box
                    - items.time_zone: Time zone information
                    - items.country_code: ISO country code
            
        Returns:
            Parsed JSON response or None if an error occurred.
        """
        params = {
            'id': region_id
        }
        
        if fields:
            params['fields'] = fields
        
        test_name = f"Getting Region by ID: {region_id}"
        return self._make_request(self.get_url, params, test_name)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_region_ids(response: Dict[str, Any]) -> List[str]:
    """
    Extract region IDs from a search response.
    
    Args:
        response: The API response dictionary.
        
    Returns:
        List of region ID strings found in the response.
    """
    ids = []
    if response and 'result' in response:
        items = response['result'].get('items', [])
        for item in items:
            if 'id' in item:
                ids.append(str(item['id']))
    return ids


def print_region_summary(response: Dict[str, Any]) -> None:
    """
    Print a summary of regions found in the response.
    
    Args:
        response: The API response dictionary.
    """
    if not response or 'result' not in response:
        print("\n[SUMMARY]: No results to summarize.")
        return
    
    items = response['result'].get('items', [])
    total = response['result'].get('total', len(items))
    
    print(f"\n[SUMMARY]: Found {total} region(s)")
    print("-" * 40)
    
    for i, item in enumerate(items[:5]):  # Show first 5
        region_id = item.get('id', 'N/A')
        name = item.get('name', 'N/A')
        region_type = item.get('type', 'N/A')
        country = item.get('country_code', item.get('country', {}).get('code', 'N/A'))
        
        print(f"  {i + 1}. ID: {region_id}")
        print(f"     Name: {name}")
        print(f"     Type: {region_type}")
        print(f"     Country: {country}")
        print()


# =============================================================================
# TEST SCENARIOS
# =============================================================================

def test_simple_text_search(client: TwoGISRegionsClient) -> Optional[str]:
    """
    Test Scenario 1: Simple Text Search
    
    Search for a region by name and print the ID found in the result.
    This demonstrates the basic search capability of the Regions API.
    
    Returns:
        The ID of the first region found, or None.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO 1: Simple Text Search")
    print("# Search for a region by name and retrieve basic information")
    print("#" * 80)
    
    # Search for Novosibirsk - a major Russian city
    # This demonstrates basic text search without additional fields
    response = client.search_by_name("Novosibirsk")
    
    if response:
        print_region_summary(response)
        
        # Extract and return the first ID
        ids = extract_region_ids(response)
        if ids:
            print(f"[RESULT]: Primary Region ID found: {ids[0]}")
            return ids[0]
    
    return None


def test_coordinate_search(client: TwoGISRegionsClient) -> Optional[str]:
    """
    Test Scenario 2: Coordinate Search (Reverse Geocoding)
    
    Search for a region using coordinates. This is useful for determining
    which region a specific point belongs to.
    
    Returns:
        The ID of the region found at the coordinates, or None.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO 2: Coordinate Search (Reverse Geocoding)")
    print("# Find which region contains specific coordinates")
    print("#" * 80)
    
    # Coordinates for central Moscow (Red Square area)
    # Using lon=37.62, lat=55.75 as specified
    # Note: 2GIS uses longitude,latitude format (longitude first!)
    longitude = 37.62
    latitude = 55.75
    
    response = client.search_by_coordinates(longitude, latitude)
    
    if response:
        print_region_summary(response)
        
        ids = extract_region_ids(response)
        if ids:
            print(f"[RESULT]: Region at coordinates ({longitude}, {latitude}): ID = {ids[0]}")
            return ids[0]
    
    return None


def test_detailed_search_with_fields(client: TwoGISRegionsClient) -> None:
    """
    Test Scenario 3: Detailed Search with Extra Fields
    
    Search for a region and request additional fields:
    - items.bounds: Geographic bounding box (useful for map display)
    - items.time_zone: Time zone information (useful for scheduling)
    - items.code: Region code (administrative identifier)
    
    This demonstrates how to retrieve extended metadata about regions.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO 3: Detailed Search with Extra Fields")
    print("# Search for a region with extended metadata")
    print("#" * 80)
    
    # Search for Prague with extra fields
    # - items.bounds: Returns the geographic bounding box (north, south, east, west)
    #   useful for setting map viewport or spatial queries
    # - items.time_zone: Returns time zone identifier and UTC offset
    #   useful for displaying local times or scheduling
    # - items.code: Returns the administrative region code
    #   useful for data integration with other systems
    fields = "items.bounds,items.time_zone,items.code"
    
    response = client.search_by_name("Prague", fields=fields)
    
    if response:
        print_region_summary(response)
        
        # Highlight the extra fields in the response
        items = response.get('result', {}).get('items', [])
        if items:
            item = items[0]
            print("[EXTRA FIELDS RETRIEVED]:")
            
            if 'bounds' in item:
                bounds = item['bounds']
                print(f"  📍 Bounds:")
                try:
                    # Bounds can be returned in different formats depending on API version
                    if isinstance(bounds, str):
                        # WKT format: POLYGON((lon1 lat1, lon2 lat2, ...))
                        print(f"     (WKT format): {bounds[:70]}..." if len(bounds) > 70 else f"     {bounds}")
                    elif isinstance(bounds, dict):
                        # Nested object format with northEast/southWest
                        if 'northEast' in bounds and 'southWest' in bounds:
                            print(f"     North: {bounds.get('northEast', {}).get('lat', 'N/A')}")
                            print(f"     South: {bounds.get('southWest', {}).get('lat', 'N/A')}")
                            print(f"     East: {bounds.get('northEast', {}).get('lon', 'N/A')}")
                            print(f"     West: {bounds.get('southWest', {}).get('lon', 'N/A')}")
                        else:
                            # Unknown dict structure - print raw
                            print(f"     (raw): {bounds}")
                    elif isinstance(bounds, list):
                        # Array format - print summary
                        print(f"     (array with {len(bounds)} points)")
                    else:
                        # Unknown format - print type and value
                        print(f"     (unknown format - {type(bounds).__name__}): {str(bounds)[:80]}")
                except Exception as e:
                    print(f"     (parse error): {bounds}")
            
            if 'time_zone' in item:
                tz = item['time_zone']
                offset = tz.get('offset', 0)
                # Convert minutes to hours:minutes format
                # Use abs() on total offset first, then apply sign, to handle negative offsets correctly
                # e.g., -570 minutes = -9:30, not -10:30
                abs_offset = abs(offset)
                offset_hours = abs_offset // 60
                offset_mins = abs_offset % 60
                sign = "+" if offset >= 0 else "-"
                offset_str = f"{sign}{offset_hours}:{offset_mins:02d}"
                print(f"  🕐 Time Zone: {tz.get('name', 'N/A')} (UTC{offset_str})")
            
            if 'code' in item:
                print(f"  🏷️  Region Code: {item['code']}")


def test_get_region_by_id(client: TwoGISRegionsClient, region_id: Optional[str] = None) -> None:
    """
    Test Scenario 4: Get Region by ID
    
    Fetch detailed information about a specific region using its ID.
    Requests extra fields:
    - items.flags: Feature flags indicating what services are available
    - items.statistics: Population and other demographic data
    
    Args:
        region_id: The region ID to look up. Defaults to "32" (Moscow) if not provided.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO 4: Get Region by ID")
    print("# Retrieve comprehensive information about a specific region")
    print("#" * 80)
    
    # Use provided ID or default to Moscow (ID: 32)
    lookup_id = region_id or "32"
    
    if region_id:
        print(f"   (Using ID from previous search: {lookup_id})")
    else:
        print(f"   (Using default ID: {lookup_id} - Moscow)")
    
    # Request extra fields:
    # - items.flags: Boolean flags indicating available features in the region
    #   (e.g., has_public_transport, has_traffic, has_flamp, etc.)
    #   Useful for determining which API features are supported
    # - items.statistics: Demographic and geographic statistics
    #   (e.g., population, area, address count, etc.)
    #   Useful for analytics and display purposes
    fields = "items.flags,items.statistics"
    
    response = client.get_by_id(lookup_id, fields=fields)
    
    if response:
        print_region_summary(response)
        
        # Highlight the extra fields
        items = response.get('result', {}).get('items', [])
        if items:
            item = items[0]
            print("[EXTRA FIELDS RETRIEVED]:")
            
            if 'flags' in item:
                flags = item['flags']
                print(f"  🚩 Feature Flags:")
                for flag_name, flag_value in list(flags.items())[:10]:  # Show first 10 flags
                    status = "✅" if flag_value else "❌"
                    print(f"     {status} {flag_name}")
                if len(flags) > 10:
                    print(f"     ... and {len(flags) - 10} more flags")
            
            if 'statistics' in item:
                stats = item['statistics']
                print(f"  📊 Statistics:")
                for stat_name, stat_value in stats.items():
                    print(f"     {stat_name}: {stat_value:,}" if isinstance(stat_value, int) else f"     {stat_name}: {stat_value}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main function to run all demonstration scenarios.
    """
    print("=" * 80)
    print("  2GIS Regions API (API 2.0) - Demonstration Suite")
    print("=" * 80)
    
    # Check if API key is set and not a placeholder
    if not API_KEY or API_KEY.lower().strip() in [p.lower() for p in _INVALID_KEY_PATTERNS]:
        print("\n❌ ERROR: API key not configured.")
        print("")
        print("   To set your API key, use one of these methods:")
        print("")
        print("   Option 1 - Environment variable (recommended):")
        print("     export TWOGIS_API_KEY='your_api_key_here'")
        print("     python regions_api_demo.py")
        print("")
        print("   Option 2 - Inline (for quick testing):")
        print("     TWOGIS_API_KEY='your_api_key_here' python regions_api_demo.py")
        print("")
        print("   Get your API key from: https://dev.2gis.com/")
        return
    
    print(f"\n✅ API Key configured: {API_KEY[:10]}...{API_KEY[-5:]}")
    print(f"✅ Base URL: {BASE_URL}")
    print(f"✅ Search Endpoint: {REGION_SEARCH_ENDPOINT}")
    print(f"✅ Get Endpoint: {REGION_GET_ENDPOINT}")
    
    # Initialize the API client
    client = TwoGISRegionsClient(API_KEY)
    
    # Run all test scenarios
    print("\n" + "=" * 80)
    print("  Running Test Scenarios...")
    print("=" * 80)
    
    # Scenario 1: Simple Text Search
    # Returns the first region ID for potential use in Scenario 4
    first_region_id = test_simple_text_search(client)
    
    # Scenario 2: Coordinate Search (Reverse Geocoding)
    test_coordinate_search(client)
    
    # Scenario 3: Detailed Search with Extra Fields
    test_detailed_search_with_fields(client)
    
    # Scenario 4: Get Region by ID
    # Chain results: use the ID from Scenario 1 if available, otherwise fall back to Moscow (32)
    # This demonstrates dynamic result chaining across scenarios
    scenario_4_id = first_region_id if first_region_id else "32"
    test_get_region_by_id(client, region_id=scenario_4_id)
    
    # Final summary
    print("\n" + "=" * 80)
    print("  All test scenarios completed!")
    print("=" * 80)
    print("\n📝 API Notes:")
    print("   - Base URL: https://catalog.api.2gis.com/2.0")
    print("   - Coordinate format: 'longitude,latitude' (longitude first!)")
    print("   - Region types: 'region' (cities) or 'segment' (districts)")
    print("   - Common fields: items.bounds, items.time_zone, items.flags, items.statistics")


if __name__ == "__main__":
    main()
