"""
Test the Routing Middleware
"""
import asyncio
from routing_middleware import get_directions, routing_middleware, RoutingRequest, RoutePoint, TransportMode


async def test_middleware():
    print("=" * 70)
    print("Testing Routing Middleware")
    print("=" * 70)
    
    # Test points: Bayterek Tower to Khan Shatyr (Astana)
    points = [
        {"lat": 51.128207, "lon": 71.430420, "name": "Bayterek Tower"},
        {"lat": 51.132235, "lon": 71.404648, "name": "Khan Shatyr"}
    ]
    
    # Test 1: Car route
    print("\n1. CAR ROUTE")
    print("-" * 50)
    result = await get_directions(points, mode="car")
    print(f"Success: {result['success']}")
    print(f"Distance: {result['total_distance_meters']} m")
    print(f"Duration: {result['total_duration_text']}")
    
    # Test 2: Walking route
    print("\n2. WALKING ROUTE")
    print("-" * 50)
    result = await get_directions(points, mode="pedestrian")
    print(f"Success: {result['success']}")
    print(f"Distance: {result['total_distance_meters']} m")
    print(f"Duration: {result['total_duration_text']}")
    
    # Test 3: Bicycle route
    print("\n3. BICYCLE ROUTE")
    print("-" * 50)
    result = await get_directions(points, mode="bicycle")
    print(f"Success: {result['success']}")
    print(f"Distance: {result['total_distance_meters']} m")
    print(f"Duration: {result['total_duration_text']}")
    
    # Test 4: Public transport
    print("\n4. PUBLIC TRANSPORT ROUTE")
    print("-" * 50)
    result = await get_directions(points, mode="public_transport")
    print(f"Success: {result['success']}")
    print(f"Distance: {result['total_distance_meters']} m")
    print(f"Duration: {result['total_duration_text']}")
    print(f"Transfers: {result.get('transfers', 'N/A')}")
    print(f"Transport types: {result.get('transport_types', [])}")
    
    if result.get('steps'):
        print("\nJourney steps:")
        for i, step in enumerate(result['steps'], 1):
            step_type = step['type'].upper()
            duration = step['duration_minutes']
            instruction = step.get('instruction', '')
            print(f"  {i}. [{step_type}] {instruction} ({duration} min)")
    
    # Test 5: Check alternatives
    if result.get('alternatives'):
        print(f"\nAlternative routes: {len(result['alternatives'])}")
        for i, alt in enumerate(result['alternatives'], 1):
            dur_min = round(alt['total_duration_seconds'] / 60, 1)
            transfers = alt.get('transfers', 0)
            types = ", ".join(alt.get('transport_types', []))
            print(f"  Option {i}: {dur_min} min, {transfers} transfer(s), via {types}")
    
    print("\n" + "=" * 70)
    print("COMPARISON TEST")
    print("=" * 70)
    
    modes = ["car", "pedestrian", "bicycle", "public_transport"]
    comparison = {}
    
    for mode in modes:
        result = await get_directions(points, mode=mode)
        if result['success']:
            comparison[mode] = {
                "duration": result['total_duration_text'],
                "distance_km": round(result['total_distance_meters'] / 1000, 2)
            }
    
    print("\nMode Comparison:")
    print("-" * 50)
    sorted_modes = sorted(comparison.items(), key=lambda x: x[1].get('duration', '99h'))
    for mode, data in sorted_modes:
        print(f"  {mode:<20} {data['duration']:<15} {data['distance_km']} km")
    
    print("\n" + "=" * 70)
    print("JSON RESPONSE SAMPLE (for frontend)")
    print("=" * 70)
    
    import json
    result = await get_directions(points, mode="public_transport")
    # Remove raw_response for cleaner output
    result_clean = {k: v for k, v in result.items() if k != 'raw_response'}
    print(json.dumps(result_clean, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(test_middleware())
