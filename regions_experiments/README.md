# 2GIS Regions API (API 2.0) Demonstration Suite

This directory contains a comprehensive Python script demonstrating various ways to interact with the 2GIS Regions API.

## File

- `regions_api_demo.py` - Main demonstration script with multiple test scenarios

## Requirements

```bash
pip install requests
```

## Configuration

The script requires a 2GIS API key. Set it via environment variable (recommended for security):

```bash
# Option 1: Export the variable (persists for session)
export TWOGIS_API_KEY='your_api_key_here'
python regions_api_demo.py

# Option 2: Inline (for quick testing)
TWOGIS_API_KEY='your_api_key_here' python regions_api_demo.py
```

Get your API key from: https://dev.2gis.com/

## Running the Script

```bash
python regions_api_demo.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/region/search` | Search for regions by name or coordinates |
| `/region/get` | Get detailed region information by ID |

## Test Scenarios

### Scenario 1: Simple Text Search
- Searches for a region by name (e.g., "Novosibirsk")
- Prints the region ID found in the result

### Scenario 2: Coordinate Search (Reverse Geocoding)
- Searches for a region using coordinates (lon=37.62, lat=55.75 for Moscow)
- Determines which region contains the specified point

### Scenario 3: Detailed Search with Extra Fields
- Searches for a region (e.g., "Prague")
- Requests additional fields:
  - `items.bounds`: Geographic bounding box
  - `items.time_zone`: Time zone information
  - `items.code`: Region administrative code

### Scenario 4: Get Region by ID
- Fetches detailed information for region ID "32" (Moscow)
- Requests additional fields:
  - `items.flags`: Feature flags (available services)
  - `items.statistics`: Population and demographic data

## Available Fields

| Field | Description |
|-------|-------------|
| `items.bounds` | Geographic bounding box (north, south, east, west) |
| `items.time_zone` | Time zone identifier and UTC offset |
| `items.code` | Administrative region code |
| `items.country_code` | ISO country code |
| `items.flags` | Feature flags indicating available services |
| `items.statistics` | Population and other statistics |

## API Notes

- **Base URL**: `https://catalog.api.2gis.com/2.0`
- **Coordinate Format**: `longitude,latitude` (longitude first!)
- **Region Types**:
  - `region`: Cities and major regions (default)
  - `segment`: Districts and settlements

## Output Format

Each request produces output in the following format:

```
--- TEST: Searching for Region by Name ---
[REQUEST]: GET https://catalog.api.2gis.com/2.0/region/search?q=Novosibirsk&key=YOUR_KEY
[STATUS]: 200 OK
[RESPONSE]:
{
    "meta": { ... },
    "result": { ... }
}
```

## Error Handling

The script includes:
- Retry logic with exponential backoff for transient failures
- Rate limit handling (HTTP 429)
- Server error handling (HTTP 5xx)
- Connection and timeout error handling
- Clear error messages for debugging
