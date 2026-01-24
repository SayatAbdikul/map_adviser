#!/usr/bin/env python3
"""
2GIS Public Transport API Demonstration Suite

This script demonstrates various ways to interact with the 2GIS Public Transport
Navigation API, including simple routing, filtered transport modes, intermediate
waypoints, and detailed walking instructions.

Author: Sayat Abdikul
Date: 2026
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

# Configure logging for better error tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# API Key for 2GIS Public Transport API
# Load from environment variable for security; fall back to placeholder for documentation
# Set your API key: export TWOGIS_API_KEY="your_api_key_here"
API_KEY = os.environ.get("TWOGIS_API_KEY", "YOUR_2GIS_API_KEY")

# Base URL for the 2GIS Public Transport API
BASE_URL = "https://routing.api.2gis.com/public_transport/2.0"

# Default request headers
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Moscow coordinates for testing scenarios
MOSCOW_CENTER = {"lat": 55.7558, "lon": 37.6173}  # Red Square area
MOSCOW_TARGET = {"lat": 55.7458, "lon": 37.6273}  # Slightly southeast
MOSCOW_INTERMEDIATE = {"lat": 55.7508, "lon": 37.6223}  # Between source and target

# Astana coordinates (alternative for testing)
ASTANA_BAITEREK = {"lat": 51.1282, "lon": 71.4305}  # Baiterek Tower
ASTANA_KHAN_SHATYR = {"lat": 51.1325, "lon": 71.4044}  # Khan Shatyr
ASTANA_MEGA_SILK_WAY = {"lat": 51.0906, "lon": 71.4189}  # Mega Silk Way


# =============================================================================
# HELPER CLASSES
# =============================================================================

def _supports_ansi_colors() -> bool:
    """
    Check if the terminal supports ANSI color codes.
    
    Returns True for:
    - Unix/Linux/macOS terminals
    - Windows Terminal, PowerShell, and WSL
    - Any terminal with TERM environment variable set
    
    Returns False for:
    - Windows CMD without ANSI support
    - Non-TTY outputs (pipes, redirects)
    """
    # Not a TTY = no colors (piped output)
    if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
        return False
    
    # Check for explicit color override
    if os.environ.get('FORCE_COLOR', '').lower() in ('1', 'true', 'yes'):
        return True
    if os.environ.get('NO_COLOR', '').lower() in ('1', 'true', 'yes'):
        return False
    
    # Unix-like systems generally support ANSI
    if sys.platform != 'win32':
        return True
    
    # Windows: Check for modern terminal support
    # Windows Terminal, PowerShell Core, and WSL support ANSI
    if os.environ.get('WT_SESSION'):  # Windows Terminal
        return True
    if os.environ.get('TERM_PROGRAM') == 'vscode':  # VS Code terminal
        return True
    if 'ANSICON' in os.environ:  # ANSICON installed
        return True
    
    # Try to enable ANSI on Windows 10+
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # Enable ANSI escape sequences on Windows 10+
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        return True
    except Exception:
        pass
    
    return False


class Colors:
    """
    ANSI color codes for terminal output with Windows fallback.
    
    On terminals that don't support ANSI codes, all color values are empty strings.
    """
    _enabled = _supports_ansi_colors()
    
    HEADER = '\033[95m' if _enabled else ''
    BLUE = '\033[94m' if _enabled else ''
    CYAN = '\033[96m' if _enabled else ''
    GREEN = '\033[92m' if _enabled else ''
    YELLOW = '\033[93m' if _enabled else ''
    RED = '\033[91m' if _enabled else ''
    ENDC = '\033[0m' if _enabled else ''
    BOLD = '\033[1m' if _enabled else ''
    UNDERLINE = '\033[4m' if _enabled else ''


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_separator(char: str = "=", length: int = 80) -> None:
    """Print a separator line."""
    print(char * length)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print()
    print_separator()
    print(f"{Colors.BOLD}{Colors.HEADER}📋 {text}{Colors.ENDC}")
    print_separator()


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.ENDC}")


def format_duration(seconds: int) -> str:
    """
    Format duration from seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds.
        
    Returns:
        Formatted string like "15 min" or "1h 30min".
    """
    if seconds < 60:
        return f"{seconds} sec"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes == 0:
        return f"{hours}h"
    return f"{hours}h {remaining_minutes}min"


def format_distance(meters: int) -> str:
    """
    Format distance from meters to human-readable string.
    
    Args:
        meters: Distance in meters.
        
    Returns:
        Formatted string like "500m" or "2.5 km".
    """
    if meters < 1000:
        return f"{meters}m"
    
    km = meters / 1000
    return f"{km:.2f} km"


def extract_transport_chain(movements: List[Dict]) -> str:
    """
    Extract transport types from movements to show the journey chain.
    
    Args:
        movements: List of movement objects from the API response.
        
    Returns:
        String like "Walk → Bus → Walk → Metro → Walk".
        Returns "No movements" if the list is empty or None.
    """
    # Handle empty or None movements list
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
            
            chain.append("🚶 Walk")
            
        elif movement_type == "passage":
            # Check for metro info first (more detailed)
            metro = movement.get("metro", {})
            if metro:
                line_name = metro.get("line_name", "Metro")
                chain.append(f"🚇 {line_name}")
            else:
                # Check for routes array
                routes = movement.get("routes", [])
                if routes:
                    route_info = routes[0]
                    transport_type = route_info.get("type", "transit")
                    route_name = route_info.get("name", "")
                    
                    # Map transport type to emoji and name
                    transport_map = {
                        "bus": "🚌",
                        "trolleybus": "🚎",
                        "tram": "🚃",
                        "shuttle_bus": "🚐",
                        "metro": "🚇",
                        "suburban_train": "🚆",
                        "funicular": "🚡",
                        "monorail": "🚝",
                        "river_transport": "⛴️",
                    }
                    emoji = transport_map.get(transport_type, "🚍")
                    
                    if route_name:
                        chain.append(f"{emoji} {route_name}")
                    else:
                        chain.append(f"{emoji} {transport_type.title()}")
                else:
                    chain.append("🚍 Transit")
                    
        elif movement_type == "transfer":
            chain.append("🔄 Transfer")
    
    return " → ".join(chain) if chain else "Walking only"


def parse_route_details(route: Dict) -> Dict[str, Any]:
    """
    Parse a single route from the API response and extract key details.
    
    Args:
        route: A route object from the API response.
        
    Returns:
        Dictionary with parsed route information.
    """
    movements = route.get("movements", [])
    
    # Calculate totals
    total_duration = route.get("total_duration", 0)
    total_distance = route.get("total_distance", 0)
    walking_duration = route.get("walking_duration", 0)
    transfer_count = route.get("transfer_count", 0)
    
    # Extract transport chain
    transport_chain = extract_transport_chain(movements)
    
    # Extract individual movement details
    movement_details = []
    for i, movement in enumerate(movements):
        mov_type = movement.get("type", "unknown")
        distance = movement.get("distance", 0)
        
        # Skip empty finish markers
        waypoint = movement.get("waypoint", {})
        subtype = waypoint.get("subtype", "")
        if mov_type == "walkway" and subtype == "finish" and distance == 0:
            continue
        
        detail = {
            "order": len(movement_details) + 1,
            "type": mov_type,
            "duration": movement.get("moving_duration", 0),
            "distance": distance,
        }
        
        # Add route info for transit movements (passage)
        if mov_type == "passage":
            # Check for metro info
            metro = movement.get("metro", {})
            if metro:
                detail["route_name"] = metro.get("line_name", "Metro")
                detail["transport_type"] = "metro"
                detail["direction"] = metro.get("ui_direction_suggest", "")
            else:
                # Check for routes array
                routes = movement.get("routes", [])
                if routes:
                    route_info = routes[0]
                    detail["route_name"] = route_info.get("name", "N/A")
                    detail["transport_type"] = route_info.get("type", "N/A")
            
            # Count platforms/stops
            alternatives = movement.get("alternatives", [])
            if alternatives:
                platforms = alternatives[0].get("platforms", [])
                detail["stops_count"] = len(platforms) if platforms else 0
            else:
                detail["stops_count"] = 0
        
        # Add waypoint info
        if waypoint:
            detail["from"] = waypoint.get("name", "Unknown")
        
        movement_details.append(detail)
    
    return {
        "total_duration": total_duration,
        "total_distance": total_distance,
        "walking_duration": walking_duration,
        "transfer_count": transfer_count,
        "transport_chain": transport_chain,
        "movement_count": len(movement_details),
        "movements": movement_details,
    }


# =============================================================================
# MAIN API FUNCTION
# =============================================================================

def fetch_route(
    payload: Dict[str, Any],
    description: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """
    Send a request to the 2GIS Public Transport API and process the response.
    
    This function handles the full request lifecycle including:
    - Printing the scenario description and request payload
    - Sending the POST request with retry logic
    - Processing and formatting the response
    - Error handling for various failure scenarios
    
    Args:
        payload: The JSON payload to send to the API.
        description: Human-readable description of the scenario being tested.
        max_retries: Maximum number of retry attempts for transient errors.
        base_delay: Base delay in seconds for exponential backoff.
        
    Returns:
        Parsed JSON response as a dictionary, or None if an error occurred.
    """
    # Print scenario header
    print_header(f"SCENARIO: {description}")
    
    # Validate API key
    if API_KEY == "YOUR_2GIS_API_KEY":
        print_warning("Using placeholder API key. Set TWOGIS_API_KEY environment variable.")
    
    # Print request details
    print(f"\n{Colors.BLUE}📤 REQUEST PAYLOAD:{Colors.ENDC}")
    print("-" * 40)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("-" * 40)
    
    # Build the request URL with API key
    url = f"{BASE_URL}?key={API_KEY}"
    
    print(f"\n{Colors.CYAN}🔗 Endpoint: {BASE_URL}{Colors.ENDC}")
    print(f"{Colors.CYAN}📡 Method: POST{Colors.ENDC}")
    
    # Retry loop for transient errors
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Send the POST request
            print(f"\n⏳ Sending request (attempt {attempt + 1}/{max_retries})...")
            
            response = requests.post(
                url,
                headers=HEADERS,
                json=payload,
                timeout=30,
            )
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                # Parse Retry-After header safely (can be integer seconds or HTTP date)
                retry_after_raw = response.headers.get("Retry-After", "")
                try:
                    retry_after = int(retry_after_raw)
                except (ValueError, TypeError):
                    # Retry-After might be an HTTP date or invalid; use exponential backoff
                    retry_after = base_delay * (2 ** attempt)
                    logger.warning(f"Could not parse Retry-After header '{retry_after_raw}', using {retry_after}s")
                
                if attempt < max_retries - 1:
                    print_warning(f"Rate limited (429). Retrying in {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                else:
                    print_error("Rate limited (429). Max retries exceeded.")
                    return None
            
            # Handle server errors (5xx)
            if response.status_code >= 500:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print_warning(f"Server error ({response.status_code}). Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    print_error(f"Server error ({response.status_code}). Max retries exceeded.")
                    return None
            
            # Handle client errors (4xx)
            if response.status_code >= 400:
                print_error(f"Client error ({response.status_code})")
                try:
                    error_data = response.json()
                    print(f"   Error details: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except json.JSONDecodeError:
                    print(f"   Response text: {response.text[:500]}")
                return None
            
            # Parse successful response
            data = response.json()
            
            # Print response summary
            print(f"\n{Colors.GREEN}📥 RESPONSE RECEIVED{Colors.ENDC}")
            print("-" * 40)
            
            # Check if we got routes - API should return a list of route alternatives
            # Handle both empty lists and error dict responses
            if not data:
                print_warning("Empty response from API.")
                return data
            
            if isinstance(data, dict):
                # API returned an error object instead of a list of routes
                error_code = data.get("error_code") or data.get("code") or data.get("error")
                error_message = data.get("error_message") or data.get("message") or data.get("description")
                if error_code or error_message:
                    print_error(f"API returned error: {error_code} - {error_message}")
                    logger.error(f"API error response: {json.dumps(data, ensure_ascii=False)}")
                else:
                    print_warning("Unexpected dict response format.")
                    print(f"Raw response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return None
            
            if not isinstance(data, list) or len(data) == 0:
                print_warning("No routes found in response.")
                print(f"Raw response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return data
            
            # Process each route alternative
            print(f"\n{Colors.BOLD}Found {len(data)} route alternative(s):{Colors.ENDC}\n")
            
            for idx, route in enumerate(data):
                print(f"{Colors.YELLOW}═══ Route {idx + 1} ═══{Colors.ENDC}")
                
                # Parse route details
                details = parse_route_details(route)
                
                # Print summary
                print(f"  ⏱️  Total Duration: {Colors.BOLD}{format_duration(details['total_duration'])}{Colors.ENDC}")
                print(f"  📏 Total Distance: {Colors.BOLD}{format_distance(details['total_distance'])}{Colors.ENDC}")
                print(f"  🚶 Walking Time: {format_duration(details['walking_duration'])}")
                print(f"  🔄 Transfers: {details['transfer_count']}")
                print(f"  🚌 Transport Chain: {details['transport_chain']}")
                
                # Print movement details
                if details["movements"]:
                    print(f"\n  {Colors.CYAN}Movement Details:{Colors.ENDC}")
                    for movement in details["movements"]:
                        mov_type = movement["type"]
                        duration = format_duration(movement["duration"])
                        distance = format_distance(movement["distance"])
                        
                        if mov_type == "walkway":
                            print(f"    {movement['order']}. 🚶 Walk: {duration}, {distance}")
                        elif mov_type == "passage":
                            route_name = movement.get("route_name", "N/A")
                            transport = movement.get("transport_type", "transit")
                            stops = movement.get("stops_count", 0)
                            print(f"    {movement['order']}. 🚌 {transport.title()} ({route_name}): {duration}, {stops} stops")
                        elif mov_type == "transfer":
                            print(f"    {movement['order']}. 🔄 Transfer: {duration}")
                
                print()
            
            print_success("Route data retrieved successfully!")
            return data
            
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print_warning(f"Connection error. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                print_error(f"Connection error: Could not connect to the API server.")
                logger.error(f"Connection failed after {max_retries} attempts: {e}")
                return None
                
        except requests.exceptions.Timeout as e:
            last_exception = e
            logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print_warning(f"Request timed out. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                print_error("Request timed out after multiple attempts.")
                logger.error(f"Timeout after {max_retries} attempts: {e}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {e}")
            print_error(f"Request error: {e}")
            return None
            
        except json.JSONDecodeError as e:
            # response is guaranteed to be defined here because JSONDecodeError
            # only occurs when calling response.json() after a successful request
            response_text = response.text[:500] if 'response' in dir() and response is not None else 'No response body'
            logger.error(f"JSON decode error: {e}. Response text: {response_text}")
            print_error(f"Failed to parse JSON response: {e}")
            print(f"Raw response: {response_text}")
            return None
    
    # Log final failure with exception details
    if last_exception:
        logger.error(f"All {max_retries} retry attempts failed. Last exception: {type(last_exception).__name__}: {last_exception}")
        print_error(f"All retry attempts failed. Last error: {type(last_exception).__name__}: {last_exception}")
    else:
        logger.error(f"All {max_retries} retry attempts failed with no captured exception.")
        print_error("All retry attempts failed.")
    return None


# =============================================================================
# TEST SCENARIOS
# =============================================================================

def scenario_a_simple_route() -> Optional[Dict]:
    """
    Scenario A: Simple Route (Defaults)
    
    Basic source-to-target request with default transport options.
    Uses all common transport types.
    """
    payload = {
        "source": {
            "point": MOSCOW_CENTER,
            "name": "Red Square (Start)",
        },
        "target": {
            "point": MOSCOW_TARGET,
            "name": "Target Location",
        },
        "transport": ["metro", "bus", "trolleybus", "tram"],
    }
    
    return fetch_route(
        payload=payload,
        description="Simple Route (Defaults) - Moscow Center to Target",
    )


def scenario_b_filtered_transport() -> Optional[Dict]:
    """
    Scenario B: Filtered Transport (Bus & Tram only)
    
    Source to target with transport limited to bus and tram.
    Also sets locale to English for response localization.
    """
    payload = {
        "source": {
            "point": MOSCOW_CENTER,
            "name": "Red Square (Start)",
        },
        "target": {
            "point": MOSCOW_TARGET,
            "name": "Target Location",
        },
        "transport": ["bus", "tram"],
        "locale": "en",
    }
    
    return fetch_route(
        payload=payload,
        description="Filtered Transport (Bus & Tram only, English locale)",
    )


def scenario_c_intermediate_points() -> Optional[Dict]:
    """
    Scenario C: Complex Route (Intermediate Points)
    
    Source to target passing through an intermediate waypoint.
    Demonstrates multi-stop routing capability.
    """
    payload = {
        "source": {
            "point": MOSCOW_CENTER,
            "name": "Red Square (Start)",
        },
        "target": {
            "point": MOSCOW_TARGET,
            "name": "Final Destination",
        },
        "intermediate_points": [
            {
                "point": MOSCOW_INTERMEDIATE,
                "name": "Intermediate Stop",
            }
        ],
        "transport": ["metro", "bus", "trolleybus", "tram"],
    }
    
    return fetch_route(
        payload=payload,
        description="Complex Route with Intermediate Point",
    )


def scenario_d_detailed_walking() -> Optional[Dict]:
    """
    Scenario D: Detailed Walking Instructions
    
    Source to target with pedestrian_instructions option enabled.
    This provides detailed geometry for walking segments.
    """
    payload = {
        "source": {
            "point": MOSCOW_CENTER,
            "name": "Red Square (Start)",
        },
        "target": {
            "point": MOSCOW_TARGET,
            "name": "Target Location",
        },
        "transport": ["metro", "bus", "trolleybus", "tram"],
        "options": ["pedestrian_instructions"],
    }
    
    return fetch_route(
        payload=payload,
        description="Detailed Walking Instructions",
    )


def scenario_e_astana_metro() -> Optional[Dict]:
    """
    Scenario E: Astana Route (Metro & Bus)
    
    Route in Astana, Kazakhstan using metro and bus.
    Tests the API with different city coordinates.
    """
    payload = {
        "source": {
            "point": ASTANA_BAITEREK,
            "name": "Baiterek Tower",
        },
        "target": {
            "point": ASTANA_KHAN_SHATYR,
            "name": "Khan Shatyr",
        },
        "transport": ["metro", "bus"],
        "locale": "ru",
    }
    
    return fetch_route(
        payload=payload,
        description="Astana Route (Baiterek to Khan Shatyr)",
    )


def scenario_f_all_transport_types() -> Optional[Dict]:
    """
    Scenario F: All Transport Types
    
    Source to target allowing all available transport types.
    Useful for finding the most comprehensive routes.
    """
    payload = {
        "source": {
            "point": MOSCOW_CENTER,
            "name": "Red Square (Start)",
        },
        "target": {
            "point": MOSCOW_TARGET,
            "name": "Target Location",
        },
        "transport": [
            "bus",
            "trolleybus",
            "tram",
            "shuttle_bus",
            "metro",
            "suburban_train",
        ],
        "locale": "ru",
    }
    
    return fetch_route(
        payload=payload,
        description="All Transport Types Enabled",
    )


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def run_all_scenarios() -> None:
    """
    Execute all test scenarios sequentially.
    
    This function runs each scenario with a delay between them
    to avoid overwhelming the API.
    """
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "2GIS PUBLIC TRANSPORT API TEST SUITE" + " " * 21 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Check API key
    if API_KEY == "YOUR_2GIS_API_KEY":
        print_warning("No API key configured!")
        print_info("Set your API key: export TWOGIS_API_KEY='your_key_here'")
        print_info("Continuing with placeholder key (requests will likely fail)...")
        print()
    else:
        print_success(f"API Key configured: {API_KEY[:8]}...{API_KEY[-4:]}")
        print()
    
    # Define scenarios to run
    scenarios = [
        ("A", "Simple Route (Defaults)", scenario_a_simple_route),
        ("B", "Filtered Transport", scenario_b_filtered_transport),
        ("C", "Intermediate Points", scenario_c_intermediate_points),
        ("D", "Detailed Walking", scenario_d_detailed_walking),
        ("E", "Astana Route", scenario_e_astana_metro),
        ("F", "All Transport Types", scenario_f_all_transport_types),
    ]
    
    results = {}
    
    for code, name, scenario_func in scenarios:
        try:
            print(f"\n{'🔷' * 30}")
            print(f"  Running Scenario {code}: {name}")
            print(f"{'🔷' * 30}\n")
            
            result = scenario_func()
            results[code] = "✅ Success" if result else "⚠️ No data"
            
            # Delay between scenarios to avoid rate limiting
            print("\n⏳ Waiting 2 seconds before next scenario...")
            time.sleep(2)
            
        except Exception as e:
            print_error(f"Scenario {code} failed with exception: {e}")
            results[code] = f"❌ Error: {str(e)[:50]}"
    
    # Print summary
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 30 + "TEST SUMMARY" + " " * 36 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    for code, status in results.items():
        scenario_name = next((s[1] for s in scenarios if s[0] == code), "Unknown")
        print(f"  Scenario {code} ({scenario_name}): {status}")
    
    print()
    print_success("All scenarios completed!")


def run_single_scenario(scenario_code: str) -> None:
    """
    Run a single scenario by its code.
    
    Args:
        scenario_code: Single letter code (A, B, C, D, E, or F).
    """
    scenarios = {
        "A": scenario_a_simple_route,
        "B": scenario_b_filtered_transport,
        "C": scenario_c_intermediate_points,
        "D": scenario_d_detailed_walking,
        "E": scenario_e_astana_metro,
        "F": scenario_f_all_transport_types,
    }
    
    scenario_code = scenario_code.upper()
    
    if scenario_code not in scenarios:
        print_error(f"Unknown scenario: {scenario_code}")
        print_info(f"Available scenarios: {', '.join(scenarios.keys())}")
        return
    
    scenarios[scenario_code]()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Run specific scenario
        scenario_code = sys.argv[1]
        run_single_scenario(scenario_code)
    else:
        # Run all scenarios
        run_all_scenarios()
