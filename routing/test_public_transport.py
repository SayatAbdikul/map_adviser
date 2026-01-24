"""
Test file for 2GIS Public Transport Routing API
Explore if we can get public transport options with travel times
"""
import asyncio
import httpx
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


async def test_public_transport_routing():
    """
    Test 2GIS routing API with public transport mode
    """
    print("=" * 60)
    print("Testing 2GIS Public Transport Routing API")
    print("=" * 60)
    
    # Test route: From point A to point B in Astana
    # Example: From Bayterek Tower to Khan Shatyr
    start_point = {"lat": 51.128207, "lon": 71.430420}  # Bayterek Tower
    end_point = {"lat": 51.132235, "lon": 71.404648}    # Khan Shatyr
    
    print(f"\nRoute: Bayterek Tower → Khan Shatyr (Astana)")
    print(f"Start: {start_point}")
    print(f"End: {end_point}")
    
    # Try different transport types
    transport_types = [
        "public_transport",
        "pedestrian", 
        "car"
    ]
    
    for transport_type in transport_types:
        print(f"\n--- Testing {transport_type.upper()} ---")
        await test_route_with_type(start_point, end_point, transport_type)


async def test_route_with_type(start: dict, end: dict, transport_type: str):
    """
    Test routing with a specific transport type
    """
    # 2GIS Directions API endpoint
    url = f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global"
    
    if transport_type == "public_transport":
        # Try the public transport specific endpoint
        url = f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0"
    elif transport_type == "pedestrian":
        url = f"{DOUBLEGIS_ROUTING_URL}/pedestrian/2.0"
    
    params = {
        "key": DOUBLEGIS_API_KEY
    }
    
    # Different body structure for different transport types
    if transport_type == "public_transport":
        json_body = {
            "source": start,
            "target": end,
            "locale": "en"
        }
    else:
        json_body = {
            "points": [start, end],
            "type": transport_type
        }
    
    print(f"URL: {url}")
    print(f"Request body: {json_body}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, params=params, json=json_body)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
                
                # Pretty print the response
                import json
                print(f"\nFull response:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
                
                if isinstance(data, dict):
                    # Extract useful info
                    if "routes" in data:
                        for i, route in enumerate(data["routes"]):
                            print(f"\nRoute {i+1}:")
                            print(f"  Duration: {route.get('duration', 'N/A')} seconds")
                            print(f"  Distance: {route.get('distance', 'N/A')} meters")
                    elif "result" in data:
                        result = data["result"]
                        print(f"\nResult: {result}")
            else:
                print(f"Error response: {response.text[:500]}")
                
        except Exception as e:
            print(f"Error: {e}")


async def test_navi_routes_api():
    """
    Test the 2GIS Navi Routes API which supports multiple transport modes
    """
    print("\n" + "=" * 60)
    print("Testing 2GIS Navi Routes API")
    print("=" * 60)
    
    # From Bayterek Tower to Khan Shatyr in Astana
    start_point = {"lat": 51.128207, "lon": 71.430420}
    end_point = {"lat": 51.132235, "lon": 71.404648}
    
    # Try the routing directions API
    url = f"{DOUBLEGIS_ROUTING_URL}/routing/7.0.0/astana/directions"
    
    params = {
        "key": DOUBLEGIS_API_KEY
    }
    
    json_body = {
        "points": [
            {"type": "stop", "lon": start_point["lon"], "lat": start_point["lat"]},
            {"type": "stop", "lon": end_point["lon"], "lat": end_point["lat"]}
        ],
        "transport": "public_transport",
        "route_mode": "fastest"
    }
    
    print(f"URL: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, params=params, json=json_body)
            print(f"Status: {response.status_code}")
            
            import json
            if response.status_code == 200:
                data = response.json()
                print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
            else:
                print(f"Response: {response.text[:1000]}")
        except Exception as e:
            print(f"Error: {e}")


async def test_online_routing_v1():
    """
    Test the Online Routing API v1 which has public transport support
    Reference: https://docs.2gis.com/en/api/navigation/routing/overview
    """
    print("\n" + "=" * 60)
    print("Testing Online Routing v1 API with different modes")
    print("=" * 60)
    
    start_point = {"lat": 51.128207, "lon": 71.430420}  # Bayterek Tower
    end_point = {"lat": 51.132235, "lon": 71.404648}    # Khan Shatyr
    
    # Try different endpoints
    endpoints_to_try = [
        ("Car Routing", f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global", 
         {"points": [start_point, end_point], "output": "summary"}),
        
        ("Pedestrian", f"{DOUBLEGIS_ROUTING_URL}/pedestrian/2.0/",
         {"points": [start_point, end_point], "output": "summary"}),
        
        ("Public Transport (ctx)", f"{DOUBLEGIS_ROUTING_URL}/ctx/1.0/directions",
         {"source": start_point, "target": end_point}),
         
        ("Directions Get", f"{DOUBLEGIS_ROUTING_URL}/get_directions",
         {"points": [start_point, end_point], "transport": "public"}),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, url, body in endpoints_to_try:
            print(f"\n--- {name} ---")
            print(f"URL: {url}")
            
            params = {"key": DOUBLEGIS_API_KEY}
            
            try:
                response = await client.post(url, params=params, json=body)
                print(f"Status: {response.status_code}")
                
                import json
                if response.status_code == 200:
                    data = response.json()
                    print(f"Keys: {data.keys() if isinstance(data, dict) else type(data)}")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
                else:
                    print(f"Response: {response.text[:500]}")
            except Exception as e:
                print(f"Error: {e}")


async def test_catalog_transport_api():
    """
    Test the 2GIS Catalog API for public transport routes and stops
    """
    print("\n" + "=" * 60)
    print("Testing 2GIS Catalog API for Public Transport Info")
    print("=" * 60)
    
    base_url = "https://catalog.api.2gis.com/3.0"
    
    # Search for metro stations near a location
    params = {
        "key": DOUBLEGIS_API_KEY,
        "q": "metro station",
        "location": "71.430420,51.128207",  # Bayterek Tower area
        "page_size": 5,
        "fields": "items.point,items.address,items.schedule,items.routes"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n--- Searching for Metro Stations ---")
        response = await client.get(f"{base_url}/items", params=params)
        print(f"Status: {response.status_code}")
        
        import json
        if response.status_code == 200:
            data = response.json()
            
            if "result" in data and "items" in data["result"]:
                for item in data["result"]["items"][:5]:
                    print(f"\nStation: {item.get('name', 'Unknown')}")
                    print(f"  Address: {item.get('address_name', 'N/A')}")
                    if "point" in item:
                        print(f"  Location: {item['point']['lat']}, {item['point']['lon']}")
                    if "routes" in item:
                        print(f"  Routes: {item['routes']}")
        
        # Try to get transport route info
        print("\n--- Searching for Bus Stops ---")
        params["q"] = "bus stop"
        response = await client.get(f"{base_url}/items", params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "items" in data["result"]:
                for item in data["result"]["items"][:3]:
                    print(f"\nStop: {item.get('name', 'Unknown')}")
                    print(f"  Type: {item.get('type', 'N/A')}")


async def test_distance_matrix_with_transport():
    """
    Test the Distance Matrix API with different transport types
    """
    print("\n" + "=" * 60)
    print("Testing Distance Matrix API with Transport Options")
    print("=" * 60)
    
    url = f"{DOUBLEGIS_ROUTING_URL}/get_dist_matrix"
    
    start_point = {"lat": 51.128207, "lon": 71.430420}  # Bayterek Tower
    end_point = {"lat": 51.132235, "lon": 71.404648}    # Khan Shatyr
    
    params = {
        "key": DOUBLEGIS_API_KEY,
        "version": "2.0"
    }
    
    # Different transport modes to try
    transport_modes = [None, "car", "pedestrian", "taxi", "truck"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for mode in transport_modes:
            print(f"\n--- Transport mode: {mode or 'default'} ---")
            
            json_body = {
                "points": [start_point, end_point],
                "sources": [0],
                "targets": [1]
            }
            
            if mode:
                json_body["mode"] = mode
            
            try:
                response = await client.post(url, params=params, json=json_body)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if "routes" in data:
                        for route in data["routes"]:
                            if route.get("status") == "OK":
                                duration_mins = route.get("duration", 0) / 60
                                distance_km = route.get("distance", 0) / 1000
                                print(f"  Distance: {distance_km:.2f} km")
                                print(f"  Duration: {duration_mins:.1f} minutes")
                    else:
                        print(f"Response: {data}")
                else:
                    print(f"Response: {response.text[:300]}")
            except Exception as e:
                print(f"Error: {e}")


async def main():
    """Run all public transport tests"""
    print("\n🚌 Starting 2GIS Public Transport API Tests\n")
    
    # Test 1: Direct public transport routing
    await test_public_transport_routing()
    
    # Test 2: Navi routes API
    await test_navi_routes_api()
    
    # Test 3: Online routing with different modes
    await test_online_routing_v1()
    
    # Test 4: Catalog API for transport info
    await test_catalog_transport_api()
    
    # Test 5: Distance matrix with transport types
    await test_distance_matrix_with_transport()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
