"""
Debug test for 2GIS Public Transport Routing API
Exploring all available endpoints
"""
import asyncio
import httpx
import json
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


async def debug_public_transport():
    """Debug various public transport API endpoints"""
    print("=" * 70)
    print("DEBUG: Testing 2GIS Public Transport Endpoints")
    print("=" * 70)
    
    start = {"lat": 55.753544, "lon": 37.621211}  # Red Square
    end = {"lat": 55.826195, "lon": 37.637295}    # VDNH
    
    # List of endpoints to try
    endpoints = [
        # Public Transport endpoints
        {
            "name": "Public Transport 2.0",
            "url": f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0",
            "body": {
                "source": start,
                "target": end,
                "locale": "en"
            }
        },
        {
            "name": "Public Transport 2.0 (alternative body)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0",
            "body": {
                "points": [start, end],
                "locale": "en"
            }
        },
        {
            "name": "CTX Routing",
            "url": f"{DOUBLEGIS_ROUTING_URL}/ctx/1.0/directions",
            "body": {
                "source": start,
                "target": end
            }
        },
        {
            "name": "Car Routing (working baseline)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/get_dist_matrix",
            "body": {
                "points": [start, end],
                "sources": [0],
                "targets": [1]
            },
            "extra_params": {"version": "2.0"}
        },
        {
            "name": "Pedestrian 2.0",
            "url": f"{DOUBLEGIS_ROUTING_URL}/pedestrian/2.0/",
            "body": {
                "points": [start, end],
                "output": "summary"
            }
        },
        {
            "name": "CarRouting 6.0 Global",
            "url": f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            "body": {
                "points": [start, end],
                "type": "jam"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for ep in endpoints:
            print(f"\n{'='*60}")
            print(f"Testing: {ep['name']}")
            print(f"URL: {ep['url']}")
            print(f"{'='*60}")
            
            params = {"key": DOUBLEGIS_API_KEY}
            if "extra_params" in ep:
                params.update(ep["extra_params"])
            
            try:
                response = await client.post(ep["url"], params=params, json=ep["body"])
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Response keys: {list(data.keys())}")
                    
                    # Check for routes/result
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list):
                            print(f"Found {len(result)} route(s)")
                            if result:
                                route = result[0]
                                if isinstance(route, dict):
                                    print(f"First route keys: {list(route.keys())}")
                                    if "total_duration" in route:
                                        print(f"Duration: {route['total_duration']/60:.1f} min")
                                    if "legs" in route:
                                        print(f"Has {len(route['legs'])} leg(s)")
                        elif isinstance(result, dict):
                            print(f"Result keys: {list(result.keys())}")
                    
                    if "routes" in data:
                        routes = data["routes"]
                        print(f"Found {len(routes)} route(s)")
                        if routes:
                            route = routes[0]
                            print(f"Route status: {route.get('status')}")
                            if route.get("status") == "OK":
                                print(f"Distance: {route.get('distance', 0)/1000:.2f} km")
                                print(f"Duration: {route.get('duration', 0)/60:.1f} min")
                    
                else:
                    print(f"Error: {response.text[:500]}")
                    
            except Exception as e:
                print(f"Exception: {e}")


async def test_catalog_transit_api():
    """Test catalog API for transit information"""
    print("\n" + "=" * 70)
    print("Testing 2GIS Catalog API for Transit Info")
    print("=" * 70)
    
    base_url = "https://catalog.api.2gis.com/3.0"
    
    # Search for transit routes
    queries = [
        ("Metro routes near Red Square", "metro"),
        ("Bus routes near Red Square", "bus route"),
        ("Transit near Red Square", "transit"),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for desc, query in queries:
            print(f"\n--- {desc} ---")
            params = {
                "key": DOUBLEGIS_API_KEY,
                "q": query,
                "location": "37.621211,55.753544",
                "page_size": 5,
                "type": "route"
            }
            
            response = await client.get(f"{base_url}/items", params=params)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data and "items" in data["result"]:
                    items = data["result"]["items"]
                    print(f"Found {len(items)} items")
                    for item in items[:3]:
                        print(f"  - {item.get('name', 'N/A')} ({item.get('type', 'N/A')})")


async def test_routing_directions():
    """Test the routing directions API with transport modes"""
    print("\n" + "=" * 70)
    print("Testing Routing Directions API")
    print("=" * 70)
    
    start = {"lat": 55.753544, "lon": 37.621211}
    end = {"lat": 55.826195, "lon": 37.637295}
    
    # Try different transport modes with the directions API
    modes = ["car", "pedestrian", "bicycle", "public_transport", "taxi"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for mode in modes:
            print(f"\n--- Mode: {mode} ---")
            
            # Try carrouting/directions style endpoint
            url = f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global"
            params = {"key": DOUBLEGIS_API_KEY}
            body = {
                "points": [start, end],
                "type": mode
            }
            
            try:
                response = await client.post(url, params=params, json=body)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list) and result:
                            route = result[0]
                            duration = route.get("total_duration", route.get("duration", 0))
                            print(f"Duration: {duration/60:.1f} min")
                else:
                    error_msg = response.text[:200]
                    print(f"Error: {error_msg}")
            except Exception as e:
                print(f"Exception: {e}")


async def check_api_key_permissions():
    """Check what the API key has access to"""
    print("\n" + "=" * 70)
    print("Checking API Key Permissions")
    print("=" * 70)
    
    print(f"\nAPI Key (first 10 chars): {DOUBLEGIS_API_KEY[:10]}...")
    print(f"Routing URL: {DOUBLEGIS_ROUTING_URL}")
    
    # Test basic catalog search (should always work)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://catalog.api.2gis.com/3.0/items",
            params={
                "key": DOUBLEGIS_API_KEY,
                "q": "cafe",
                "location": "37.621211,55.753544",
                "page_size": 1
            }
        )
        print(f"\nCatalog API: {response.status_code}")
        
        # Test routing API
        response = await client.post(
            f"{DOUBLEGIS_ROUTING_URL}/get_dist_matrix",
            params={"key": DOUBLEGIS_API_KEY, "version": "2.0"},
            json={
                "points": [{"lat": 55.753544, "lon": 37.621211}, {"lat": 55.826195, "lon": 37.637295}],
                "sources": [0],
                "targets": [1]
            }
        )
        print(f"Distance Matrix API: {response.status_code}")
        
        # Test public transport API
        response = await client.post(
            f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0",
            params={"key": DOUBLEGIS_API_KEY},
            json={
                "source": {"lat": 55.753544, "lon": 37.621211},
                "target": {"lat": 55.826195, "lon": 37.637295}
            }
        )
        print(f"Public Transport API: {response.status_code}")
        if response.status_code != 200:
            print(f"  Error: {response.text[:300]}")


async def main():
    """Run all debug tests"""
    await check_api_key_permissions()
    await debug_public_transport()
    await test_catalog_transit_api()
    await test_routing_directions()
    
    print("\n" + "=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
