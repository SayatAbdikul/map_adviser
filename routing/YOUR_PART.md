# 2GIS API Integration - Your Part

Your responsibility: 2GIS API calls for searching places and building routes.

## Your Files

- **[doublegis_service.py](doublegis_service.py)** - Main 2GIS service (YOUR CODE)
- **[test_2gis.py](test_2gis.py)** - Test your integration independently
- **[app_2gis_only.py](app_2gis_only.py)** - Simplified API for testing
- **[models.py](models.py)** - Data models (shared)
- **[config.py](config.py)** - Configuration (2GIS API key already set)

## Quick Start - Test Your Part

### 1. Install Dependencies
```bash
pip install fastapi uvicorn httpx pydantic python-dotenv
```

### 2. Run Tests
```bash
python test_2gis.py
```

This will test:
- ✅ Searching places
- ✅ Building routes
- ✅ Multiple search queries

### 3. Run Your API
```bash
python app_2gis_only.py
```

Visit http://localhost:8000/docs to test your endpoints interactively.

## Your API Endpoints

### GET /search
Search for places in 2GIS.

**Example:**
```bash
curl "http://localhost:8000/search?query=restaurants&city=moscow&limit=5"
```

**Response:**
```json
[
  {
    "id": "70000001018442532",
    "name": "Restaurant Name",
    "address": "Street Address",
    "lat": 55.7558,
    "lon": 37.6173,
    "type": "building"
  }
]
```

### POST /route
Build a route through places.

**Example:**
```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "1",
      "name": "Start",
      "address": "Address 1",
      "lat": 55.7558,
      "lon": 37.6173
    },
    {
      "id": "2",
      "name": "End",
      "address": "Address 2",
      "lat": 55.7600,
      "lon": 37.6200
    }
  ]'
```

**Response:**
```json
{
  "places": [...],
  "total_distance": 5000,
  "total_distance_km": 5.0,
  "total_duration": 900,
  "total_duration_min": 15.0,
  "route_url": "https://2gis.com/directions?points=...",
  "route_data": {...}
}
```

## 2GIS Service Methods

Your `DoubleGISService` class provides:

### `search_places(query, city, limit)`
Search for places in 2GIS.
- **query**: "restaurants", "museums", "parks", etc.
- **city**: "moscow", "spb", etc.
- **limit**: max results (default 10)
- **Returns**: List of Place objects

### `build_route(places)`
Build a route through multiple places.
- **places**: List of Place objects (min 2)
- **Returns**: dict with distance, duration, route data

### `generate_route_url(places)`
Generate a 2GIS URL to view the route.
- **places**: List of Place objects
- **Returns**: URL string

## Testing Workflow

1. **Test search**: Can you find places?
   ```bash
   python test_2gis.py
   ```

2. **Test API**: Can others call your endpoints?
   ```bash
   python app_2gis_only.py
   # Then visit http://localhost:8000/docs
   ```

3. **Share with team**: Your teammates will integrate with these endpoints

## API Key

Already configured in `.env`:
```
DOUBLEGIS_API_KEY=ed1537b1-4397-4542-9633-97f7585cb789
```

## When Your Teammates Finish

They will:
- Add Gemini AI integration (`gemini_service.py`)
- Use your `DoubleGISService` class
- Create the full `/plan-route` endpoint in `main.py`

Your 2GIS integration is ready and can be tested independently!

## Questions/Issues?

- Check 2GIS API docs: https://docs.2gis.com/
- Your API key is working and ready
- Test files are ready to run
