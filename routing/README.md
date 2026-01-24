# AI Route Planner

FastAPI application that uses Gemini AI and 2GIS API to plan intelligent routes based on natural language descriptions.

## Features

- 🗣️ Natural language input for route planning
- 🤖 AI-powered place selection using Google Gemini
- 🗺️ Real route building using 2GIS API
- 🎯 Intelligent place ordering for optimal routes

## How It Works

1. **User Input**: User describes what they want to visit (e.g., "I want to visit Italian restaurants and parks")
2. **AI Processing**: Gemini analyzes the description and generates search queries
3. **Place Search**: Searches 2GIS for matching places
4. **AI Selection**: Gemini selects the best places and orders them logically
5. **Route Building**: 2GIS builds an actual route through the selected places
6. **Response**: Returns the route with explanations and 2GIS map URL

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the `.env` file:
```
DOUBLEGIS_API_KEY=ed1537b1-4397-4542-9633-97f7585cb789
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your Gemini API key from: https://makersuite.google.com/app/apikey

### 3. Run the Application

```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --reload
```

The API will be available at: http://localhost:8000

## API Endpoints

### POST /plan-route

Plan a complete route based on natural language description.

**Request:**
```json
{
  "description": "I want to visit Italian restaurants and beautiful parks",
  "city": "moscow"
}
```

**Response:**
```json
{
  "places": [
    {
      "id": "123",
      "name": "Bella Italia",
      "address": "Main Street 10",
      "lat": 55.7558,
      "lon": 37.6173,
      "type": "restaurant"
    }
  ],
  "route_url": "https://2gis.com/directions?points=...",
  "total_distance": 5000,
  "total_duration": 900,
  "gemini_explanation": "I've selected these places because..."
}
```

### POST /search-places

Search for places directly using 2GIS.

**Parameters:**
- `query`: Search term
- `city`: City name (default: "moscow")
- `limit`: Max results (default: 10)

### GET /health

Health check endpoint.

## Example Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/plan-route",
    json={
        "description": "Show me coffee shops and museums in the city center",
        "city": "moscow"
    }
)

route = response.json()
print(f"Visit these places: {[p['name'] for p in route['places']]}")
print(f"Route URL: {route['route_url']}")
print(f"Explanation: {route['gemini_explanation']}")
```

## Project Structure

```
routing/
├── main.py                 # FastAPI application
├── models.py               # Pydantic models
├── config.py               # Configuration
├── doublegis_service.py    # 2GIS API integration
├── gemini_service.py       # Gemini AI integration
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not in git)
├── .env.example            # Example environment file
└── README.md              # This file
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Notes

- The 2GIS API key provided is already configured
- You need to add your own Gemini API key
- Default city is Moscow, but can be changed in requests
- Routes require at least 2 places to be found
