"""
Standalone test file for 2GIS API integration
Test your 2GIS service independently without needing Gemini or other components
"""
import asyncio
from doublegis_service import DoubleGISService
from models import Place


async def test_search_places():
    """Test searching for places"""
    print("=" * 50)
    print("Testing 2GIS Place Search")
    print("=" * 50)
    
    service = DoubleGISService()
    
    # Test query
    query = "restaurants"
    city = "moscow"
    
    print(f"\nSearching for: {query} in {city}")
    places = await service.search_places(query, city, limit=5)
    
    print(f"\nFound {len(places)} places:")
    for i, place in enumerate(places, 1):
        print(f"\n{i}. {place.name}")
        print(f"   Address: {place.address}")
        print(f"   Coordinates: {place.lat}, {place.lon}")
        print(f"   ID: {place.id}")
    
    return places


async def test_build_route():
    """Test building a route through multiple places"""
    print("\n" + "=" * 50)
    print("Testing 2GIS Route Building")
    print("=" * 50)
    
    service = DoubleGISService()
    
    # First, search for some places
    places = await service.search_places("cafes", "moscow", limit=3)
    
    if len(places) < 2:
        print("\nNot enough places found to build a route")
        return
    
    print(f"\nBuilding route through {len(places)} places:")
    for i, place in enumerate(places, 1):
        print(f"{i}. {place.name}")
    
    # Build the route
    route_info = await service.build_route(places)
    
    print("\nRoute Information:")
    print(f"Total Distance: {route_info['total_distance']} meters ({route_info['total_distance']/1000:.2f} km)")
    print(f"Total Duration: {route_info['total_duration']} seconds ({route_info['total_duration']/60:.1f} minutes)")
    
    # Generate route URL
    route_url = service.generate_route_url(places)
    print(f"\n2GIS Route URL:")
    print(route_url)
    
    return route_info


async def test_multiple_searches():
    """Test multiple different search queries"""
    print("\n" + "=" * 50)
    print("Testing Multiple Search Queries")
    print("=" * 50)
    
    service = DoubleGISService()
    
    queries = ["museums", "parks", "shopping centers"]
    
    for query in queries:
        print(f"\n--- Searching: {query} ---")
        places = await service.search_places(query, "moscow", limit=3)
        print(f"Found {len(places)} places:")
        for place in places:
            print(f"  • {place.name} - {place.address}")


async def main():
    """Run all tests"""
    print("\n🚀 Starting 2GIS API Tests\n")
    
    try:
        # Test 1: Search places
        places = await test_search_places()
        
        # Test 2: Build route
        if places and len(places) >= 2:
            await test_build_route()
        
        # Test 3: Multiple searches
        await test_multiple_searches()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
