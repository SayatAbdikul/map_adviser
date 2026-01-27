#!/usr/bin/env python3
"""Debug script to check route registration."""

import main
from fastapi.testclient import TestClient

print("=== Route Registration Debug ===")
print("\nAll registered routes:")
for route in main.app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', {'GET'})
        print(f"  {methods} {route.path}")

print("\n=== Testing with TestClient ===")
client = TestClient(main.app)

# Test health endpoint
print("\nTesting /health endpoint:")
health_response = client.get('/health')
print(f"Status: {health_response.status_code}")
print(f"Response: {health_response.json()}")

# Test room creation endpoint
print("\nTesting /api/rooms endpoint:")
room_response = client.post('/api/rooms', json={'name': 'Debug Test Room'})
print(f"Status: {room_response.status_code}")
if room_response.status_code == 200:
    print(f"Response: {room_response.json()}")
else:
    print(f"Error response: {room_response.text}")

print("\n=== OpenAPI Schema ===")
openapi_response = client.get('/openapi.json')
if openapi_response.status_code == 200:
    openapi_data = openapi_response.json()
    paths = list(openapi_data.get('paths', {}).keys())
    print(f"Available paths in OpenAPI: {paths}")
else:
    print(f"Failed to get OpenAPI schema: {openapi_response.status_code}")