"""
Test 2GIS Public Transport API with correct format
"""
import asyncio
import httpx
import json
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


async def test_public_transport_formats():
    """Test different body formats for public transport API"""
    print("=" * 70)
    print("Testing Public Transport API with Different Formats")
    print("=" * 70)
    
    start = {"lat": 55.753544, "lon": 37.621211}
    end = {"lat": 55.826195, "lon": 37.637295}
    
    # Different body formats to try
    formats = [
        {
            "name": "With transport section (empty)",
            "body": {
                "source": start,
                "target": end,
                "transport": {}
            }
        },
        {
            "name": "With transport types array",
            "body": {
                "source": start,
                "target": end,
                "transport": ["metro", "bus", "tram"]
            }
        },
        {
            "name": "With transport object (types array)",
            "body": {
                "source": start,
                "target": end,
                "transport": {
                    "types": ["metro", "bus", "tram", "trolleybus"]
                }
            }
        },
        {
            "name": "With transport and filters",
            "body": {
                "source": start,
                "target": end,
                "transport": {
                    "types": ["metro", "bus", "tram", "trolleybus", "light_rail", "suburban"]
                },
                "filters": {
                    "max_walking_time": 900
                }
            }
        },
        {
            "name": "With locale and alternatives",
            "body": {
                "source": start,
                "target": end,
                "transport": {
                    "types": ["metro", "bus"]
                },
                "locale": "en",
                "alternative_count": 3
            }
        },
        {
            "name": "Full format with all options",
            "body": {
                "source": {"lat": start["lat"], "lon": start["lon"]},
                "target": {"lat": end["lat"], "lon": end["lon"]},
                "transport": {
                    "types": ["metro", "bus", "tram", "trolleybus"]
                },
                "locale": "en"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for fmt in formats:
            print(f"\n--- {fmt['name']} ---")
            print(f"Body: {json.dumps(fmt['body'], indent=2)[:200]}...")
            
            try:
                response = await client.post(
                    f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0",
                    params={"key": DOUBLEGIS_API_KEY},
                    json=fmt["body"]
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"SUCCESS! Keys: {list(data.keys())}")
                    
                    # Save successful response
                    with open(f"pt_success_{fmt['name'][:20].replace(' ', '_')}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list):
                            print(f"Found {len(result)} route option(s)")
                            for i, route in enumerate(result[:2], 1):
                                if "total_duration" in route:
                                    print(f"  Route {i}: {route['total_duration']/60:.1f} min")
                                if "legs" in route:
                                    print(f"    Legs: {len(route['legs'])}")
                                    for leg in route["legs"][:3]:
                                        leg_type = leg.get("type", "unknown")
                                        leg_dur = leg.get("duration", 0) / 60
                                        print(f"      - {leg_type}: {leg_dur:.1f} min")
                else:
                    print(f"Error: {response.text[:300]}")
                    
            except Exception as e:
                print(f"Exception: {e}")


async def test_working_route_comparison():
    """Compare working modes (pedestrian, bicycle) with what we want"""
    print("\n" + "=" * 70)
    print("Working Transport Modes Comparison")
    print("=" * 70)
    
    start = {"lat": 55.753544, "lon": 37.621211}
    end = {"lat": 55.826195, "lon": 37.637295}
    
    # These modes work with carrouting API
    modes = {
        "pedestrian": "Walking",
        "bicycle": "Cycling"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for mode, name in modes.items():
            print(f"\n{name}:")
            
            response = await client.post(
                f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
                params={"key": DOUBLEGIS_API_KEY},
                json={
                    "points": [start, end],
                    "type": mode
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data and isinstance(data["result"], list) and data["result"]:
                    route = data["result"][0]
                    duration = route.get("total_duration", 0) / 60
                    distance = route.get("total_distance", 0) / 1000
                    print(f"  Duration: {duration:.1f} minutes")
                    print(f"  Distance: {distance:.2f} km")


async def explore_api_docs_endpoints():
    """Try endpoints from 2GIS API documentation"""
    print("\n" + "=" * 70)
    print("Exploring 2GIS API Documentation Endpoints")
    print("=" * 70)
    
    start = {"lat": 55.753544, "lon": 37.621211}
    end = {"lat": 55.826195, "lon": 37.637295}
    
    # Based on 2GIS API docs
    endpoints = [
        # Directions API format
        {
            "name": "Directions API (v6 jam)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            "body": {"points": [start, end], "type": "jam"}
        },
        {
            "name": "Directions API (v6 statistic)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            "body": {"points": [start, end], "type": "statistic"}
        },
        # Distance matrix alternative
        {
            "name": "Distance Matrix (no mode)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/get_dist_matrix",
            "params": {"key": DOUBLEGIS_API_KEY, "version": "2.0"},
            "body": {"points": [start, end], "sources": [0], "targets": [1]}
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for ep in endpoints:
            print(f"\n--- {ep['name']} ---")
            
            params = ep.get("params", {"key": DOUBLEGIS_API_KEY})
            
            try:
                response = await client.post(ep["url"], params=params, json=ep["body"])
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "result" in data and isinstance(data["result"], list) and data["result"]:
                        route = data["result"][0]
                        duration = route.get("total_duration", route.get("duration", 0))
                        if duration:
                            print(f"Duration: {duration/60:.1f} min")
                    
                    if "routes" in data and data["routes"]:
                        route = data["routes"][0]
                        if route.get("status") == "OK":
                            print(f"Duration: {route.get('duration', 0)/60:.1f} min")
                            print(f"Distance: {route.get('distance', 0)/1000:.2f} km")
                        else:
                            print(f"Status: {route.get('status')}")
                else:
                    print(f"Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"Error: {e}")


async def main():
    await test_public_transport_formats()
    await test_working_route_comparison()
    await explore_api_docs_endpoints()
    
    print("\n" + "=" * 70)
    print("CONCLUSIONS")
    print("=" * 70)
    print("""
Based on testing:

1. WORKING APIs:
   - Distance Matrix API: Car routing with durations
   - CarRouting API: pedestrian, bicycle modes
   - Catalog API: Search for transit info (routes, stops)

2. PUBLIC TRANSPORT API:
   - Endpoint exists: /public_transport/2.0
   - Requires 'transport' section in request body
   - May need specific API key permissions

3. ALTERNATIVE APPROACH:
   - Use Catalog API to find transit routes/stops
   - Calculate walking to nearest stop
   - Provide transit route information (schedule, stops)
    """)


if __name__ == "__main__":
    asyncio.run(main())
