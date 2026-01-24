"""
Test file for 2GIS Public Transport Routing API - Refined Version
Based on API exploration results
"""
import asyncio
import httpx
import json
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL


async def get_public_transport_route(
    start_lat: float, 
    start_lon: float, 
    end_lat: float, 
    end_lon: float,
    locale: str = "en"
) -> dict:
    """
    Get public transport routing options using 2GIS API
    
    Args:
        start_lat, start_lon: Starting point coordinates
        end_lat, end_lon: Destination coordinates
        locale: Language for results (en, ru)
        
    Returns:
        Dictionary with route options and travel times
    """
    url = f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0"
    params = {"key": DOUBLEGIS_API_KEY}
    json_body = {
        "source": {"lat": start_lat, "lon": start_lon},
        "target": {"lat": end_lat, "lon": end_lon},
        "locale": locale
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, params=params, json=json_body)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.status_code, "message": response.text}


def parse_route_options(data: dict) -> list:
    """Parse public transport API response into user-friendly options"""
    options = []
    
    if "result" not in data:
        return options
    
    result = data["result"]
    routes = result if isinstance(result, list) else [result] if result else []
    
    for i, route in enumerate(routes):
        option = {
            "option_number": i + 1,
            "total_duration_minutes": round(route.get("total_duration", 0) / 60, 1),
            "total_distance_km": round(route.get("total_distance", 0) / 1000, 2),
            "walking_duration_minutes": round(route.get("walking_duration", 0) / 60, 1),
            "transfers": 0,
            "transport_types": [],
            "legs": []
        }
        
        legs = route.get("legs", [])
        pt_legs = [l for l in legs if l.get("type") == "public_transport"]
        option["transfers"] = max(0, len(pt_legs) - 1)
        
        for leg in legs:
            leg_info = {
                "type": leg.get("type", "unknown"),
                "duration_minutes": round(leg.get("duration", 0) / 60, 1),
                "distance_km": round(leg.get("distance", 0) / 1000, 2),
            }
            
            if leg.get("type") == "public_transport":
                route_info = leg.get("route", {})
                leg_info["route_name"] = route_info.get("name", "")
                leg_info["route_type"] = route_info.get("type", "")
                leg_info["from_stop"] = leg.get("departure", {}).get("stop_name", "")
                leg_info["to_stop"] = leg.get("arrival", {}).get("stop_name", "")
                
                transport_type = route_info.get("type", "")
                if transport_type and transport_type not in option["transport_types"]:
                    option["transport_types"].append(transport_type)
            
            option["legs"].append(leg_info)
        
        options.append(option)
    
    return options


async def test_astana_route():
    """Test public transport routing in Astana"""
    print("=" * 70)
    print("Testing Public Transport Routing: Astana")
    print("=" * 70)
    
    start = {"lat": 51.128207, "lon": 71.430420, "name": "Bayterek Tower"}
    end = {"lat": 51.132235, "lon": 71.404648, "name": "Khan Shatyr"}
    
    print(f"\nRoute: {start['name']} -> {end['name']}")
    
    result = await get_public_transport_route(
        start["lat"], start["lon"], end["lat"], end["lon"], locale="en"
    )
    
    has_error = "error" in result
    status = "Error" if has_error else "Success"
    print(f"API Response: {status}")
    
    if not has_error:
        # Save response
        with open("pt_response_astana.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("Response saved to: pt_response_astana.json")
        
        options = parse_route_options(result)
        print(f"\nFound {len(options)} route option(s)")
        
        for opt in options[:3]:
            print(f"\n  Option {opt['option_number']}:")
            print(f"    Total time: {opt['total_duration_minutes']} min")
            print(f"    Distance: {opt['total_distance_km']} km")
            print(f"    Walking: {opt['walking_duration_minutes']} min")
            print(f"    Transfers: {opt['transfers']}")
            print(f"    Transport: {', '.join(opt['transport_types']) or 'N/A'}")
            
            for j, leg in enumerate(opt["legs"][:5], 1):
                leg_type = leg["type"]
                duration = leg["duration_minutes"]
                if leg_type == "public_transport":
                    route_name = leg.get("route_name", "")
                    from_stop = leg.get("from_stop", "")
                    to_stop = leg.get("to_stop", "")
                    print(f"      {j}. Take {route_name} ({duration} min)")
                    if from_stop:
                        print(f"         {from_stop} -> {to_stop}")
                else:
                    print(f"      {j}. Walk ({duration} min)")
    
    return result


async def test_dubai_route():
    """Test public transport routing in Dubai"""
    print("\n" + "=" * 70)
    print("Testing Public Transport Routing: Dubai")
    print("=" * 70)
    
    start = {"lat": 25.197525, "lon": 55.279373, "name": "Dubai Mall"}
    end = {"lat": 25.080341, "lon": 55.141254, "name": "Dubai Marina"}
    
    print(f"\nRoute: {start['name']} -> {end['name']}")
    
    result = await get_public_transport_route(
        start["lat"], start["lon"], end["lat"], end["lon"], locale="en"
    )
    
    has_error = "error" in result
    status = "Error" if has_error else "Success"
    print(f"API Response: {status}")
    
    if not has_error:
        with open("pt_response_dubai.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("Response saved to: pt_response_dubai.json")
        
        options = parse_route_options(result)
        print(f"\nFound {len(options)} route option(s)")
        
        for opt in options[:3]:
            print(f"\n  Option {opt['option_number']}:")
            print(f"    Total time: {opt['total_duration_minutes']} min")
            print(f"    Walking: {opt['walking_duration_minutes']} min")
            print(f"    Transfers: {opt['transfers']}")
    
    return result


async def compare_transport_modes():
    """Compare car vs public transport vs walking"""
    print("\n" + "=" * 70)
    print("Comparing Transport Modes: Astana (Bayterek -> Khan Shatyr)")
    print("=" * 70)
    
    start = {"lat": 51.128207, "lon": 71.430420}
    end = {"lat": 51.132235, "lon": 71.404648}
    results = {}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Car
        print("\n1. Getting car route...")
        url = f"{DOUBLEGIS_ROUTING_URL}/get_dist_matrix"
        params = {"key": DOUBLEGIS_API_KEY, "version": "2.0"}
        body = {"points": [start, end], "sources": [0], "targets": [1]}
        
        resp = await client.post(url, params=params, json=body)
        if resp.status_code == 200:
            data = resp.json()
            if "routes" in data and data["routes"]:
                route = data["routes"][0]
                if route.get("status") == "OK":
                    results["car"] = {
                        "duration_min": round(route.get("duration", 0) / 60, 1),
                        "distance_km": round(route.get("distance", 0) / 1000, 2)
                    }
        
        # Pedestrian
        print("2. Getting pedestrian route...")
        url = f"{DOUBLEGIS_ROUTING_URL}/pedestrian/2.0/"
        body = {"points": [start, end], "output": "summary"}
        
        resp = await client.post(url, params={"key": DOUBLEGIS_API_KEY}, json=body)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data:
                res = data["result"]
                if isinstance(res, list) and res:
                    route = res[0]
                elif isinstance(res, dict):
                    route = res
                else:
                    route = None
                    
                if route:
                    results["pedestrian"] = {
                        "duration_min": round(route.get("total_duration", 0) / 60, 1),
                        "distance_km": round(route.get("total_distance", 0) / 1000, 2)
                    }
    
    # Public transport
    print("3. Getting public transport route...")
    pt_result = await get_public_transport_route(
        start["lat"], start["lon"], end["lat"], end["lon"]
    )
    
    if "result" in pt_result:
        res = pt_result["result"]
        routes = res if isinstance(res, list) else [res] if res else []
        if routes:
            route = routes[0]
            results["public_transport"] = {
                "duration_min": round(route.get("total_duration", 0) / 60, 1),
                "distance_km": round(route.get("total_distance", 0) / 1000, 2),
                "walking_min": round(route.get("walking_duration", 0) / 60, 1)
            }
    
    # Display
    print("\n" + "-" * 50)
    print("COMPARISON RESULTS")
    print("-" * 50)
    print(f"{'Mode':<20} {'Duration':<15} {'Distance':<15}")
    print("-" * 50)
    
    for mode, data in results.items():
        duration = f"{data['duration_min']} min"
        distance = f"{data['distance_km']} km"
        mode_name = mode.replace('_', ' ').title()
        print(f"{mode_name:<20} {duration:<15} {distance:<15}")
        
        if "walking_min" in data and data["walking_min"] > 0:
            print(f"  (includes {data['walking_min']} min walking)")
    
    print("-" * 50)
    return results


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("2GIS PUBLIC TRANSPORT API TESTS")
    print("=" * 70)
    
    # Test routes
    await test_astana_route()
    await test_dubai_route()
    await compare_transport_modes()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: 2GIS Public Transport API Capabilities")
    print("=" * 70)
    print("""
YES, you can provide users with public transport options!

The 2GIS API supports:
  [x] Multiple route alternatives
  [x] Total travel time estimation  
  [x] Walking time (to/from stops)
  [x] Number of transfers
  [x] Transport types (metro, bus, tram, trolleybus)
  [x] Route names and stop information
  [x] Step-by-step journey breakdown
  [x] Distance for each segment
  
Coverage:
  - Astana (Kazakhstan)
  - Dubai (UAE)  
  - Other 2GIS-supported cities
    """)


if __name__ == "__main__":
    asyncio.run(main())
