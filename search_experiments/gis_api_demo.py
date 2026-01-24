#!/usr/bin/env python3
"""
2GIS Places API (Search API 3.0) Demonstration Suite

This script demonstrates various ways to interact with the 2GIS Places API,
including text search, geo-radius search, detailed field retrieval, sorting,
and ID lookups.

Author: Sayat Abdikul
Date: 2026
"""

import requests
import json
import math
import os
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode


# =============================================================================
# CONFIGURATION
# =============================================================================

# API Key for 2GIS Places API
# Load from environment variable for security; fall back to placeholder for documentation
# Set your API key: export TWOGIS_API_KEY="your_api_key_here"
API_KEY = os.environ.get("TWOGIS_API_KEY", "YOUR_API_KEY_HERE")

# Base URLs for the 2GIS Catalog API
BASE_URL = "https://catalog.api.2gis.com/3.0/items"
BYID_URL = "https://catalog.api.2gis.com/3.0/items/byid"


# =============================================================================
# API CLIENT CLASS
# =============================================================================

class TwoGISClient:
    """
    A client class for interacting with the 2GIS Places API.
    
    This class provides methods for various search operations including
    text search, geo-radius search, and ID lookups.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the 2GIS API client.
        
        Args:
            api_key: Your 2GIS API key for authentication.
        """
        self.api_key = api_key
        self.base_url = BASE_URL
        self.byid_url = BYID_URL
    
    def make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        description: str,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a request to the 2GIS API and handle the response.
        
        This helper function builds the URL, sends the request, handles errors,
        and returns the parsed JSON response. Includes retry logic with
        exponential backoff for transient failures (429, 5xx errors).
        
        Args:
            endpoint: The API endpoint URL.
            params: Dictionary of query parameters.
            description: Human-readable description of what this request does.
            max_retries: Maximum number of retry attempts for transient errors.
            base_delay: Base delay in seconds for exponential backoff.
            
        Returns:
            Parsed JSON response as a dictionary, or None if an error occurred.
        """
        # Add API key to parameters (required for authentication)
        params['key'] = self.api_key
        
        # Build the full URL with query parameters
        full_url = f"{endpoint}?{urlencode(params)}"
        
        # Print request information
        print("\n" + "=" * 80)
        print(f"📋 DESCRIPTION: {description}")
        print("=" * 80)
        print(f"🔗 REQUEST URL: {full_url}")
        print("-" * 80)
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Send the GET request
                response = requests.get(endpoint, params=params, timeout=30)
                
                # Handle rate limiting (429) with retry
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** attempt)))
                    if attempt < max_retries - 1:
                        print(f"⚠️  RATE LIMITED (429): Retrying in {retry_after}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_after)
                        continue
                    else:
                        print(f"❌ RATE LIMITED (429): Max retries exceeded. Try again later.")
                        return None
                
                # Handle server errors (5xx) with retry
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️  SERVER ERROR ({response.status_code}): Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ SERVER ERROR ({response.status_code}): Max retries exceeded.")
                        return None
                
                # Check for other HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                
                # Check for API-level errors
                if 'meta' in data and data['meta'].get('code') != 200:
                    error_msg = data['meta'].get('error', {}).get('message', 'Unknown API error')
                    print(f"❌ API ERROR: {error_msg}")
                    return None
                
                return data
                
            except requests.exceptions.HTTPError as e:
                print(f"❌ HTTP ERROR: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        print(f"   Error details: {json.dumps(error_data, indent=2)}")
                    except:
                        print(f"   Response text: {e.response.text[:500]}")
                return None
                
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"⚠️  CONNECTION ERROR: Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print("❌ CONNECTION ERROR: Could not connect to the API server after multiple attempts.")
                    return None
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"⚠️  TIMEOUT: Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print("❌ TIMEOUT ERROR: The request timed out after multiple attempts.")
                    return None
                
            except requests.exceptions.RequestException as e:
                print(f"❌ REQUEST ERROR: {e}")
                return None
                
            except json.JSONDecodeError:
                print("❌ JSON ERROR: Could not parse the API response.")
                return None
        
        return None
    
    def search(
        self,
        query: str,
        description: str,
        region_id: Optional[int] = None,
        point: Optional[str] = None,
        radius: Optional[int] = None,
        location: Optional[str] = None,
        sort: Optional[str] = None,
        fields: Optional[str] = None,
        page_size: int = 10,
        obj_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Perform a text-based search on the 2GIS API.
        
        Args:
            query: Text query (e.g., "cafe", "Pizza").
            description: Human-readable description of the search.
            region_id: Region ID to search within (e.g., 32 for Moscow).
            point: Center point for geo-search as "lon,lat" (longitude first!).
            radius: Search radius in meters (used with point).
            location: User context as "lon,lat" for distance sorting.
            sort: Sorting method ('distance', 'relevance', 'rating').
            fields: Extra fields to retrieve (comma-separated).
            page_size: Number of results to return (max 50).
            obj_type: Object type filter (e.g., 'branch', 'building', 'street').
            
        Returns:
            Parsed JSON response or None if an error occurred.
        """
        params = {
            'q': query,
            'page_size': page_size
        }
        
        # Add optional parameters if provided
        if region_id:
            params['region_id'] = region_id
        if point:
            params['point'] = point
        if radius:
            params['radius'] = radius
        if location:
            params['location'] = location
        if sort:
            params['sort'] = sort
        if fields:
            params['fields'] = fields
        if obj_type:
            params['type'] = obj_type
        
        return self.make_request(self.base_url, params, description)
    
    def lookup_by_id(self, item_id: str, description: str, fields: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Look up a specific item by its 2GIS ID.
        
        Args:
            item_id: The unique 2GIS item ID.
            description: Human-readable description of the lookup.
            fields: Extra fields to retrieve (comma-separated).
            
        Returns:
            Parsed JSON response or None if an error occurred.
        """
        params = {'id': item_id}
        
        if fields:
            params['fields'] = fields
        
        return self.make_request(self.byid_url, params, description)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two coordinates using the Haversine formula.
    
    Args:
        lat1: Latitude of point 1 (in degrees).
        lon1: Longitude of point 1 (in degrees).
        lat2: Latitude of point 2 (in degrees).
        lon2: Longitude of point 2 (in degrees).
        
    Returns:
        Distance in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


# =============================================================================
# RESULT FORMATTING FUNCTIONS
# =============================================================================

def format_item_basic(item: Dict[str, Any], index: int = 0, **kwargs) -> str:
    """
    Format a single item with basic information (name, address, coordinates).
    
    Args:
        item: The item dictionary from the API response.
        index: The result index number.
        
    Returns:
        Formatted string with item details.
    """
    name = item.get('name', 'N/A')
    
    # Extract address - can be in different formats
    address_name = item.get('address_name', '')
    full_address = item.get('full_address_name', '')
    address = full_address or address_name or 'Address not available'
    
    # Extract coordinates
    point = item.get('point', {})
    if point:
        lat = point.get('lat', 'N/A')
        lon = point.get('lon', 'N/A')
        coords_str = f"{lat}, {lon}"
    else:
        coords_str = "N/A"
    
    return f"  {index + 1}. 📍 {name}\n     📫 {address}\n     🌍 Coordinates: {coords_str}"


def format_item_with_distance(
    item: Dict[str, Any], 
    index: int = 0, 
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None
) -> str:
    """
    Format a single item with distance information.
    
    Args:
        item: The item dictionary from the API response.
        index: The result index number.
        user_lat: User's latitude for distance calculation.
        user_lon: User's longitude for distance calculation.
        
    Returns:
        Formatted string with item details including distance.
    """
    name = item.get('name', 'N/A')
    address = item.get('address_name', item.get('full_address_name', 'N/A'))
    
    # Calculate distance from user location if point data is available
    distance_str = "N/A"
    coords_str = "N/A"
    point = item.get('point', {})
    if point:
        item_lat = point.get('lat')
        item_lon = point.get('lon')
        if item_lat and item_lon:
            coords_str = f"{item_lat}, {item_lon}"
            if user_lat is not None and user_lon is not None:
                distance = calculate_distance(user_lat, user_lon, item_lat, item_lon)
                distance_str = f"{distance:.0f}m"
    
    return f"  {index + 1}. 📍 {name}\n     📫 {address}\n     🌍 Coordinates: {coords_str}\n     📏 Distance: {distance_str}"


def format_item_detailed(item: Dict[str, Any], index: int = 0) -> str:
    """
    Format a single item with detailed information including schedule and contacts.
    
    Args:
        item: The item dictionary from the API response.
        index: The result index number.
        
    Returns:
        Formatted string with detailed item information.
    """
    name = item.get('name', 'N/A')
    address = item.get('address_name', item.get('full_address_name', 'N/A'))
    
    # Extract website from contact_groups (if available)
    website = "N/A"
    phone = "N/A"
    contact_groups = item.get('contact_groups', [])
    for group in contact_groups:
        contacts = group.get('contacts', [])
        for contact in contacts:
            contact_type = contact.get('type', '')
            if contact_type == 'website' and website == "N/A":
                website = contact.get('value', 'N/A')
            elif contact_type == 'phone' and phone == "N/A":
                phone = contact.get('value', 'N/A')
    
    # Parse schedule - 2GIS API returns day-keyed dictionary with working_hours
    schedule = item.get('schedule', {})
    schedule_info = []
    is_open = "Unknown"
    
    if schedule:
        # Day order for consistent output
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_names = {
            'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday',
            'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'
        }
        
        for day in day_order:
            if day in schedule:
                day_data = schedule[day]
                working_hours = day_data.get('working_hours', [])
                if working_hours:
                    # Handle multiple time ranges per day (split shifts)
                    time_ranges = []
                    for hours in working_hours:
                        from_time = hours.get('from', '??')
                        to_time = hours.get('to', '??')
                        time_ranges.append(f"{from_time} - {to_time}")
                    schedule_info.append(f"{day_names[day]}: {', '.join(time_ranges)}")
        
        if schedule_info:
            is_open = "See schedule below"
    
    # Extract coordinates
    point = item.get('point', {})
    if point:
        lat = point.get('lat', 'N/A')
        lon = point.get('lon', 'N/A')
        coords_str = f"{lat}, {lon}"
    else:
        coords_str = "N/A"
    
    output = f"""  {index + 1}. 📍 {name}
     📫 {address}
     🌍 Coordinates: {coords_str}
     📞 Phone: {phone}
     🌐 Website: {website}
     ⏰ Status: {is_open}"""
    
    # Add schedule details if available (show first 3 days to keep output concise)
    if schedule_info:
        output += "\n     📅 Schedule:"
        for day_info in schedule_info[:5]:  # Show up to 5 days
            output += f"\n        - {day_info}"
    
    return output


def print_results_summary(
    data: Dict[str, Any], 
    formatter_func, 
    max_results: int = 5,
    **formatter_kwargs
) -> None:
    """
    Print a formatted summary of search results.
    
    Args:
        data: The full API response dictionary.
        formatter_func: Function to format each item.
        max_results: Maximum number of results to display.
        **formatter_kwargs: Additional keyword arguments to pass to the formatter function.
    """
    if not data:
        print("📭 No data received.")
        return
    
    # Get result items
    result = data.get('result', {})
    items = result.get('items', [])
    total = result.get('total', 0)
    
    print(f"\n📊 RESPONSE SUMMARY:")
    print(f"   Total results found: {total}")
    print(f"   Showing: {min(len(items), max_results)} results")
    print("-" * 40)
    
    if not items:
        print("   No items found matching your query.")
        return
    
    for i, item in enumerate(items[:max_results]):
        print(formatter_func(item, i, **formatter_kwargs))
        print()


# =============================================================================
# TEST SCENARIOS
# =============================================================================

def scenario_a_basic_text_search(client: TwoGISClient) -> Optional[str]:
    """
    Scenario A: Basic Text Search
    
    Search for "Пицца" (Pizza) in Moscow (region_id=32) and show the names 
    and addresses of the top 3 results.
    
    Returns:
        The ID of the first result (for use in Scenario E), or None.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO A: Basic Text Search")
    print("# Search for 'Пицца' (Pizza) in Moscow, show top 3 results")
    print("#" * 80)
    
    # region_id=32 is Moscow in the 2GIS system
    # We request only 3 results using page_size
    # Using Russian "Пицца" for better results in the Russian API
    data = client.search(
        query="Пицца",  # "Pizza" in Russian for better search results
        description="Basic text search for 'Пицца' (Pizza) in Moscow (top 3 results)",
        region_id=32,  # Moscow region ID
        page_size=3,
        fields="items.point"  # Request coordinates
    )
    
    print_results_summary(data, format_item_basic, max_results=3)
    
    # Return the first item's ID for use in Scenario E
    if data:
        items = data.get('result', {}).get('items', [])
        if items:
            return items[0].get('id')
    return None


def scenario_b_geo_radius_search(client: TwoGISClient) -> None:
    """
    Scenario B: Geo-Radius Search
    
    Search for "Аптека" (Pharmacy) within 500 meters of coordinates 
    (longitude: 37.62, latitude: 55.75).
    Note: 2GIS uses "lon,lat" format (longitude first!).
    """
    print("\n" + "#" * 80)
    print("# SCENARIO B: Geo-Radius Search")
    print("# Search for 'Аптека' (Pharmacy) within 500m of lon:37.62, lat:55.75")
    print("#" * 80)
    
    # User coordinates for this search
    user_lon, user_lat = 37.62, 55.75
    
    # Point format is "longitude,latitude" - longitude comes first!
    # This is near the center of Moscow (Red Square area)
    # Using Russian "Аптека" for better results
    # Request items.point field to calculate distance
    data = client.search(
        query="Аптека",  # "Pharmacy" in Russian
        description="Geo-radius search for 'Аптека' (Pharmacy) within 500m of Moscow center",
        point=f"{user_lon},{user_lat}",  # lon,lat format (longitude first!)
        radius=500,  # 500 meters
        page_size=5,
        fields="items.point"  # Request coordinates to calculate distance
    )
    
    print_results_summary(
        data, format_item_with_distance, max_results=5,
        user_lat=user_lat, user_lon=user_lon
    )


def scenario_c_detailed_fields(client: TwoGISClient) -> None:
    """
    Scenario C: Detailed Information with Extra Fields
    
    Search for "Сбербанк" (Sberbank) and request extra fields including:
    - items.schedule (operating hours)
    - items.contact_groups (phones, websites)
    
    Using Sberbank as it commonly has schedule and contact info available.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO C: Detailed Information (Extra Fields)")
    print("# Search for 'Сбербанк' (Sberbank) with schedule and contact information")
    print("#" * 80)
    
    # Request additional fields using comma-separated values
    # items.schedule - returns operating hours
    # items.contact_groups - returns phones, websites, emails
    # Using Сбербанк as banks typically have complete schedule/contact data
    data = client.search(
        query="Сбербанк",  # Sberbank - major Russian bank with complete data
        description="Search for 'Сбербанк' (Sberbank) with schedule and contact fields",
        region_id=32,  # Moscow
        fields="items.schedule,items.contact_groups,items.point",  # Include coordinates
        page_size=3,
        obj_type="branch"  # Filter to branch type for better results
    )
    
    print_results_summary(data, format_item_detailed, max_results=3)


def scenario_d_sort_by_distance(client: TwoGISClient) -> None:
    """
    Scenario D: Sort by Distance
    
    Search for "Банкомат" (ATM) sorted by distance from the user's location.
    User location: longitude 37.62, latitude 55.75.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO D: Sort by Distance")
    print("# Search for 'Банкомат' (ATM) sorted by distance from user location")
    print("#" * 80)
    
    # User coordinates
    user_lon, user_lat = 37.62, 55.75
    
    # The 'location' parameter sets the user's context for distance calculation
    # The 'sort' parameter with 'distance' sorts results by proximity
    # Using Russian "Банкомат" for ATM machines
    # Request items.point field to calculate distance
    data = client.search(
        query="Банкомат",  # "ATM" in Russian
        description="Search for 'Банкомат' (ATM) sorted by distance from lon:37.62, lat:55.75",
        location=f"{user_lon},{user_lat}",  # User's location (lon,lat)
        sort="distance",  # Sort by distance from user
        page_size=5,
        fields="items.point"  # Request coordinates to calculate distance
    )
    
    print_results_summary(
        data, format_item_with_distance, max_results=5,
        user_lat=user_lat, user_lon=user_lon
    )


def scenario_e_lookup_by_id(client: TwoGISClient, item_id: Optional[str] = None) -> None:
    """
    Scenario E: Lookup by ID
    
    Perform a specific lookup for an object using its 2GIS ID.
    Requires a valid ID from a previous search for reliable results.
    
    Args:
        item_id: The ID to look up. Must be provided from a prior search result.
    """
    print("\n" + "#" * 80)
    print("# SCENARIO E: Lookup by ID")
    print("# Retrieve specific object by its 2GIS ID")
    print("#" * 80)
    
    # Require a valid ID from prior search results
    if not item_id:
        print("\n⚠️  SKIPPED: No valid item ID available from previous searches.")
        print("   This scenario requires an ID obtained from a prior search result.")
        print("   Ensure Scenario A completes successfully to provide an ID.")
        return
    
    print(f"   (Using ID obtained from Scenario A: {item_id})")
    lookup_id = item_id
    
    data = client.lookup_by_id(
        item_id=lookup_id,
        description=f"Lookup specific item by ID: {lookup_id}",
        fields="items.schedule,items.contact_groups,items.point"
    )
    
    if data:
        result = data.get('result', {})
        items = result.get('items', [])
        
        print(f"\n📊 RESPONSE SUMMARY:")
        
        if items:
            item = items[0]
            print(f"   Found item:")
            print(format_item_detailed(item, 0))
        else:
            print("   Item not found. This ID may not exist or may have been removed.")
            print("   In production, use IDs obtained from search results.")
    else:
        print("\n📊 RESPONSE SUMMARY:")
        print("   Could not retrieve item. The ID may be invalid or expired.")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main function to run all demonstration scenarios.
    """
    print("=" * 80)
    print("  2GIS Places API (Search API 3.0) - Demonstration Suite")
    print("=" * 80)
    
    # Check if API key is set
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ ERROR: API key not configured.")
        print("")
        print("   To set your API key, use one of these methods:")
        print("")
        print("   Option 1 - Environment variable (recommended):")
        print("     export TWOGIS_API_KEY='your_api_key_here'")
        print("     python gis_api_demo.py")
        print("")
        print("   Option 2 - Inline (for quick testing):")
        print("     TWOGIS_API_KEY='your_api_key_here' python gis_api_demo.py")
        print("")
        print("   Get your API key from: https://dev.2gis.com/")
        return
    
    print(f"\n✅ API Key configured: {API_KEY[:10]}...{API_KEY[-5:]}")
    print(f"✅ Base URL: {BASE_URL}")
    
    # Initialize the API client
    client = TwoGISClient(API_KEY)
    
    # Run all test scenarios
    print("\n" + "=" * 80)
    print("  Running Test Scenarios...")
    print("=" * 80)
    
    # Scenario A: Basic Text Search
    # Returns the first item's ID for use in Scenario E
    first_item_id = scenario_a_basic_text_search(client)
    
    # Scenario B: Geo-Radius Search
    scenario_b_geo_radius_search(client)
    
    # Scenario C: Detailed Information with Fields
    scenario_c_detailed_fields(client)
    
    # Scenario D: Sort by Distance
    scenario_d_sort_by_distance(client)
    
    # Scenario E: Lookup by ID (using ID from Scenario A)
    scenario_e_lookup_by_id(client, first_item_id)
    
    # Final summary
    print("\n" + "=" * 80)
    print("  All scenarios completed!")
    print("=" * 80)
    print("\n📝 Notes:")
    print("   - All coordinates use 'lon,lat' format (longitude first)")
    print("   - Region ID 32 = Moscow")
    print("   - Maximum page_size is 50")
    print("   - Use 'fields' parameter to request additional data")
    print("   - Available sort options: 'distance', 'relevance', 'rating'")


if __name__ == "__main__":
    main()
