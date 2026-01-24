"""
Test file for 2GIS Routing API
Tests routing between random spots in Moscow without making places API calls
"""
import asyncio
import httpx
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL
from models import Place


# Sample Moscow locations for testing (no places API needed)
MOSCOW_TEST_PLACES = [
    Place(
        id="test_1",
        name="Red Square",
        address="Red Square, Moscow",
        lat=55.753544,
        lon=37.621202
    ),
    Place(
        id="test_2",
        name="Gorky Park",
        address="Krymsky Val, 9, Moscow",
        lat=55.731180,
        lon=37.603514
    ),
    Place(
        id="test_3",
        name="Moscow State University",
        address="Leninskie Gory, 1, Moscow",
        lat=55.703340,
        lon=37.530570
    ),
]


async def test_routing_api_formats():
    """Test different 2GIS routing API endpoint formats"""
    print("=" * 60)
    print("Testing 2GIS Routing API")
    print("=" * 60)
    
    places = MOSCOW_TEST_PLACES[:2]  # Test with 2 points first
    
    print(f"\nRouting from: {places[0].name}")
    print(f"         to: {places[1].name}")
    
    # Different API endpoint formats to try
    endpoints_to_try = [
        # Format 1: Directions API (newer)
        {
            "name": "Directions API (POST with JSON body)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/directions/6.0.0/global",
            "method": "POST",
            "params": {"key": DOUBLEGIS_API_KEY},
            "json_body": {
                "points": [
                    {"lat": places[0].lat, "lon": places[0].lon},
                    {"lat": places[1].lat, "lon": places[1].lon}
                ],
                "type": "jam"
            }
        },
        # Format 2: Car routing with POST (lon,lat format)
        {
            "name": "Car Routing POST (lon,lat format)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            "method": "POST",
            "params": {"key": DOUBLEGIS_API_KEY},
            "json_body": {
                "points": [
                    {"lon": places[0].lon, "lat": places[0].lat},
                    {"lon": places[1].lon, "lat": places[1].lat}
                ],
                "type": "jam"
            }
        },
        # Format 3: Car routing with POST (alternative format)
        {
            "name": "Car Routing POST (shortest)",
            "url": f"{DOUBLEGIS_ROUTING_URL}/carrouting/6.0.0/global",
            "method": "POST",
            "params": {"key": DOUBLEGIS_API_KEY},
            "json_body": {
                "points": [
                    {"lon": places[0].lon, "lat": places[0].lat},
                    {"lon": places[1].lon, "lat": places[1].lat}
                ],
                "type": "shortest"
            }
        },
        # Format 4: Pedestrian routing with POST
        {
            "name": "Pedestrian Routing POST",
            "url": f"{DOUBLEGIS_ROUTING_URL}/pedestrian/6.0.0/global",
            "method": "POST",
            "params": {"key": DOUBLEGIS_API_KEY},
            "json_body": {
                "points": [
                    {"lon": places[0].lon, "lat": places[0].lat},
                    {"lon": places[1].lon, "lat": places[1].lat}
                ]
            }
        },
        # Format 5: Distance matrix
        {
            "name": "Distance Matrix",
            "url": f"{DOUBLEGIS_ROUTING_URL}/get_dist_matrix",
            "method": "POST",
            "params": {"key": DOUBLEGIS_API_KEY, "version": "2.0"},
            "json_body": {
                "points": [
                    {"lat": places[0].lat, "lon": places[0].lon},
                    {"lat": places[1].lat, "lon": places[1].lon}
                ],
                "sources": [0],
                "targets": [1]
            }
        },
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints_to_try:
            print(f"\n--- Testing: {endpoint['name']} ---")
            print(f"URL: {endpoint['url']}")
            
            try:
                if endpoint["method"] == "GET":
                    response = await client.get(
                        endpoint["url"],
                        params=endpoint["params"]
                    )
                else:  # POST
                    response = await client.post(
                        endpoint["url"],
                        params=endpoint["params"],
                        json=endpoint.get("json_body")
                    )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ SUCCESS!")
                    print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                    
                    # Try to extract route info
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list) and len(result) > 0:
                            route = result[0]
                            print(f"Distance: {route.get('total_distance', route.get('distance', 'N/A'))} meters")
                            print(f"Duration: {route.get('total_duration', route.get('duration', 'N/A'))} seconds")
                    elif "routes" in data:
                        routes = data["routes"]
                        if len(routes) > 0:
                            route = routes[0]
                            print(f"Distance: {route.get('distance', 'N/A')} meters")
                            print(f"Duration: {route.get('duration', 'N/A')} seconds")
                    
                    # Print first 500 chars of response for debugging
                    response_text = str(data)[:500]
                    print(f"Response preview: {response_text}...")
                else:
                    print(f"❌ Failed: {response.text[:300]}")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")


async def test_routing_with_service():
    """Test routing using the DoubleGISService class"""
    print("\n" + "=" * 60)
    print("Testing Routing via DoubleGISService")
    print("=" * 60)
    
    from doublegis_service import DoubleGISService
    
    service = DoubleGISService()
    places = MOSCOW_TEST_PLACES
    
    print(f"\nBuilding route through {len(places)} places:")
    for i, place in enumerate(places, 1):
        print(f"  {i}. {place.name} ({place.lat}, {place.lon})")
    
    try:
        route_info = await service.build_route(places)
        
        print(f"\n✅ Route built successfully!")
        print(f"Total Distance: {route_info['total_distance']} meters ({route_info['total_distance']/1000:.2f} km)")
        print(f"Total Duration: {route_info['total_duration']} seconds ({route_info['total_duration']/60:.1f} minutes)")
        
        # Generate URL
        route_url = service.generate_route_url(places)
        print(f"\n2GIS Route URL: {route_url}")
        
        return route_info
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Run routing tests"""
    print("\n🚀 Starting 2GIS Routing API Tests\n")
    print(f"API Key: {DOUBLEGIS_API_KEY[:10]}..." if DOUBLEGIS_API_KEY else "API Key: NOT SET")
    print(f"Routing URL: {DOUBLEGIS_ROUTING_URL}")
    
    # Test various API formats
    await test_routing_api_formats()
    
    # Test via service
    await test_routing_with_service()
    
    print("\n" + "=" * 60)
    print("✅ Routing tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
