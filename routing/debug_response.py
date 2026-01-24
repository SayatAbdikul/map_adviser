"""Debug the public transport API response structure"""
import httpx
import json
from config import DOUBLEGIS_API_KEY, DOUBLEGIS_ROUTING_URL

url = f"{DOUBLEGIS_ROUTING_URL}/public_transport/2.0"
params = {"key": DOUBLEGIS_API_KEY}
body = {
    "source": {"point": {"lon": 37.621211, "lat": 55.753544}},
    "target": {"point": {"lon": 37.637295, "lat": 55.826195}},
    "transport": ["metro", "bus"]
}

r = httpx.post(url, params=params, json=body)
data = r.json()

print(f"Number of routes: {len(data)}")
print("=" * 60)

for i, route in enumerate(data[:2]):  # First 2 routes
    print(f"\n--- ROUTE {i+1} ---")
    print(f"Route keys: {list(route.keys())}")
    print(f"crossing_count: {route.get('crossing_count')}")
    
    movements = route.get("movements", [])
    print(f"\nNumber of movements: {len(movements)}")
    
    for j, mov in enumerate(movements):
        print(f"\n  Movement {j+1}:")
        print(f"    type: {mov.get('type')}")
        print(f"    distance: {mov.get('distance')}")
        print(f"    moving_duration: {mov.get('moving_duration')}")
        print(f"    waiting_duration: {mov.get('waiting_duration')}")
        
        if "waypoint" in mov:
            wp = mov["waypoint"]
            print(f"    waypoint: name={wp.get('name')}, comment={wp.get('comment')}, subtype={wp.get('subtype')}")
        
        if "metro" in mov and mov["metro"]:
            m = mov["metro"]
            print(f"    metro: {m.get('name')}, color={m.get('color')}")
            
        if "routes" in mov and mov["routes"]:
            for r_info in mov["routes"]:
                print(f"    route: {r_info.get('name')}, type={r_info.get('type')}, subtype={r_info.get('subtype')}")
        
        if "platforms" in mov and mov["platforms"]:
            plats = mov["platforms"]
            if isinstance(plats, list):
                print(f"    platforms: {len(plats)} stops")
                if len(plats) > 0:
                    first = plats[0]
                    last = plats[-1]
                    print(f"      from: {first.get('name', '?')}")
                    print(f"      to: {last.get('name', '?')}")
            elif isinstance(plats, dict):
                print(f"    platforms (dict): {plats}")
