# 2GIS Public Transport API Experiments

This directory contains test scripts for the 2GIS Public Transport Navigation API.

## Files

- `public_transport_api_demo.py` - Comprehensive test harness for the Public Transport API

## Setup

### 1. Set your API key

```bash
export TWOGIS_API_KEY="your_api_key_here"
```

### 2. Install dependencies

```bash
pip install requests
```

## Usage

### Run all scenarios

```bash
python public_transport_api_demo.py
```

### Run a specific scenario

```bash
python public_transport_api_demo.py A  # Simple Route (Metro, Bus, Trolleybus, Tram)
python public_transport_api_demo.py B  # Filtered Transport (Bus & Tram only, English)
python public_transport_api_demo.py C  # Route with Intermediate Points
python public_transport_api_demo.py D  # Detailed Walking Instructions
python public_transport_api_demo.py E  # Astana Route (Kazakhstan)
python public_transport_api_demo.py F  # All Transport Types Enabled
```

## Scenarios

| Code | Description | Features |
|------|-------------|----------|
| A | Simple Route | Metro, Bus, Trolleybus, Tram (Moscow) |
| B | Filtered Transport | Bus & Tram only, English locale |
| C | Intermediate Points | Multi-stop routing with waypoint |
| D | Detailed Walking | Pedestrian instructions enabled |
| E | Astana Route | Different city (Kazakhstan) |
| F | All Transport Types | All modes including suburban train |

## Output Format

The script displays:
- **Request Payload**: Pretty-printed JSON sent to the API
- **Response Summary**: 
  - Total duration and distance
  - Walking time
  - Number of transfers
  - Transport chain (e.g., "Walk → Metro → Walk")
- **Movement Details**: Step-by-step breakdown of the route

## API Documentation

- **Base URL**: `https://routing.api.2gis.com/public_transport/2.0`
- **Method**: POST
- **Authentication**: Query parameter `?key=YOUR_API_KEY`

### Request Structure

```json
{
  "source": {
    "point": {"lat": 55.7558, "lon": 37.6173},
    "name": "Start Point"
  },
  "target": {
    "point": {"lat": 55.7458, "lon": 37.6273},
    "name": "End Point"
  },
  "intermediate_points": [
    {"point": {"lat": 55.7508, "lon": 37.6223}, "name": "Waypoint"}
  ],
  "transport": ["metro", "bus", "tram"],
  "locale": "en",
  "options": ["pedestrian_instructions"]
}
```

### Required Fields

- `source`: Starting point with `point` (lat/lon) - **required**
- `target`: Destination with `point` (lat/lon) - **required**  
- `transport`: List of allowed transport types - **required**

### Valid Transport Types

- `bus` - City buses
- `trolleybus` - Electric trolleybuses
- `tram` - Trams/streetcars
- `shuttle_bus` - Shuttle/minibuses
- `metro` - Subway/underground
- `suburban_train` - Commuter rail
- `funicular` - Cable railways
- `monorail` - Monorail systems
- `river_transport` - Ferries/water transport

### Response Structure

The API returns an array of route alternatives, each containing:
- `total_duration` - Total journey time in seconds
- `total_distance` - Total distance in meters
- `walking_duration` - Walking time in seconds
- `transfer_count` - Number of transfers
- `movements` - Array of journey segments (walk, transit, transfer)
