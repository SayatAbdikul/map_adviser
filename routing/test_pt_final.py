"""
Final test for 2GIS Public Transport API - trying coordinate formats
"""
import asyncio
import httpx
import json
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


async def test_coordinate_formats():
    """Test different coordinate formats"""
    print("=" * 70)
    print("Testing Coordinate Formats for Public Transport API")
    print("=" * 70)
    
    # Different coordinate formats
    formats = [
        {
            "name": "lon,lat string format",
            "body": {
                "source": "37.621211,55.753544",
                "target": "37.637295,55.826195",
                "transport": {"types": ["metro", "bus"]}
            }
        },
        {
            "name": "lat,lon string format",
            "body": {
                "source": "55.753544,37.621211",
                "target": "55.826195,37.637295",
                "transport": {"types": ["metro", "bus"]}
            }
        },
        {
            "name": "Object with lon/lat (swapped)",
            "body": {
                "source": {"lon": 37.621211, "lat": 55.753544},
                "target": {"lon": 37.637295, "lat": 55.826195},
                "transport": {"types": ["metro", "bus"]}
            }
        },
        {
            "name": "Point object format",
            "body": {
                "source": {"point": {"lon": 37.621211, "lat": 55.753544}},
                "target": {"point": {"lon": 37.637295, "lat": 55.826195}},
                "transport": {"types": ["metro", "bus"]}
            }
        },
        {
            "name": "Array format [lon, lat]",
            "body": {
                "source": [37.621211, 55.753544],
                "target": [37.637295, 55.826195],
                "transport": {"types": ["metro", "bus"]}
            }
        },
        {
            "name": "x,y object format",
            "body": {
                "source": {"x": 37.621211, "y": 55.753544},
                "target": {"x": 37.637295, "y": 55.826195},
                "transport": {"types": ["metro", "bus"]}
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for fmt in formats:
            print(f"\n--- {fmt['name']} ---")
            
            try:
                response = await client.post(
                    f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0",
                    params={"key": DOUBLEGIS_API_KEY},
                    json=fmt["body"]
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"SUCCESS! Response keys: {list(data.keys())}")
                    
                    # Save and analyze
                    with open("pt_success.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list) and result:
                            print(f"Found {len(result)} route(s)")
                            route = result[0]
                            if "total_duration" in route:
                                print(f"Duration: {route['total_duration']/60:.1f} min")
                            if "legs" in route:
                                print(f"Journey legs: {len(route['legs'])}")
                                for leg in route["legs"][:3]:
                                    print(f"  - {leg.get('type')}: {leg.get('duration', 0)/60:.1f} min")
                else:
                    error = response.text[:200]
                    print(f"Error: {error}")
                    
            except Exception as e:
                print(f"Exception: {e}")


async def test_public_transport_final():
    """Final comprehensive test"""
    print("\n" + "=" * 70)
    print("Final Public Transport API Test")
    print("=" * 70)
    
    # Based on 2GIS documentation format
    body = {
        "source": {"lon": 37.621211, "lat": 55.753544},
        "target": {"lon": 37.637295, "lat": 55.826195},
        "transport": {
            "types": ["metro", "bus", "tram", "trolleybus"]
        }
    }
    
    print(f"Request body:\n{json.dumps(body, indent=2)}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0",
            params={"key": DOUBLEGIS_API_KEY},
            json=body
        )
        
        print(f"\nStatus: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nSUCCESS!")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        else:
            print(f"\nFull error response:")
            print(response.text)


async def check_available_transit_info():
    """Get available transit information from Catalog API"""
    print("\n" + "=" * 70)
    print("Available Transit Information (via Catalog API)")
    print("=" * 70)
    
    base_url = "https://catalog.api.2gis.com/3.0"
    
    # Find nearest metro station to Red Square
    params = {
        "key": DOUBLEGIS_API_KEY,
        "q": "станция метро",  # Metro station in Russian
        "location": "37.621211,55.753544",
        "radius": 1000,
        "page_size": 5,
        "fields": "items.point,items.schedule,items.links"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n--- Nearest Metro Stations to Red Square ---")
        response = await client.get(f"{base_url}/items", params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "items" in data["result"]:
                for item in data["result"]["items"]:
                    name = item.get("name", "Unknown")
                    address = item.get("address_name", "")
                    print(f"\n  Station: {name}")
                    if address:
                        print(f"  Address: {address}")
                    if "point" in item:
                        print(f"  Location: {item['point']['lat']}, {item['point']['lon']}")
        
        # Find bus stops
        print("\n--- Nearest Bus Stops ---")
        params["q"] = "автобусная остановка"  # Bus stop in Russian
        response = await client.get(f"{base_url}/items", params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "items" in data["result"]:
                for item in data["result"]["items"][:3]:
                    print(f"  Stop: {item.get('name', 'Unknown')}")


async def main():
    await test_coordinate_formats()
    await test_public_transport_final()
    await check_available_transit_info()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
Based on comprehensive testing:

1. The Public Transport API (/public_transport/2.0) exists but:
   - Requires specific coordinate format
   - May require additional API key permissions
   - Returns 400 errors with current key

2. WORKING ALTERNATIVES for your use case:
   
   A) Use CarRouting API for basic travel estimates:
      - pedestrian mode: Walking directions
      - bicycle mode: Cycling directions
   
   B) Use Catalog API to provide transit information:
      - Search for nearby metro stations
      - Search for bus stops
      - Get route information (names, directions)
   
   C) Use Distance Matrix API for car travel times

3. RECOMMENDATION:
   For now, you can offer users:
   - Walking time estimate (pedestrian mode)
   - Cycling time estimate (bicycle mode) 
   - Car travel time (distance matrix)
   - List of nearby transit options (catalog API)
   
   Contact 2GIS for public transport API access if needed.
    """)


if __name__ == "__main__":
    asyncio.run(main())
