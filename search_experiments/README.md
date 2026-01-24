# 2GIS Places API (Search API 3.0) Demonstration Suite

This directory contains a comprehensive Python script demonstrating various ways to interact with the 2GIS Places API.

## File

- `gis_api_demo.py` - Main demonstration script with multiple test scenarios

## Requirements

```bash
pip install requests
```

## Configuration

The script requires a 2GIS API key. Set it via environment variable (recommended for security):

```bash
# Option 1: Export the variable (persists for session)
export TWOGIS_API_KEY='your_api_key_here'
python gis_api_demo.py

# Option 2: Inline (for quick testing)
TWOGIS_API_KEY='your_api_key_here' python gis_api_demo.py
```

Get your API key from: https://dev.2gis.com/

## Running the Script

```bash
python gis_api_demo.py
```

## Scenarios Demonstrated

### Scenario A: Basic Text Search
- Searches for "Пицца" (Pizza) in Moscow
- Shows names and addresses of top 3 results

### Scenario B: Geo-Radius Search
- Searches for "Аптека" (Pharmacy) within 500m of Moscow center
- Coordinates: lon=37.62, lat=55.75
- Calculates and displays distance from search point

### Scenario C: Detailed Information (Extra Fields)
- Searches for "Сбербанк" (Sberbank)
- Requests additional fields: `items.schedule`, `items.contact_groups`
- Displays operating hours and contact information

### Scenario D: Sort by Distance
- Searches for "Банкомат" (ATM)
- Sorts results by distance from user location
- Displays calculated distances for each result

### Scenario E: Lookup by ID
- Performs a specific lookup using a 2GIS item ID
- Uses an ID obtained from Scenario A to ensure validity
- Displays detailed information including schedule

## API Notes

- **Coordinate Format**: All coordinates use `lon,lat` format (longitude first!)
- **Region ID**: Moscow = 32
- **Maximum page_size**: 50
- **Sort Options**: `distance`, `relevance`, `rating`
- **Extra Fields**: `items.point`, `items.schedule`, `items.contact_groups`, `items.address`

## API Documentation

For more information about the 2GIS API, visit:
- https://dev.2gis.com/
- https://api.2gis.ru/doc/catalog/
