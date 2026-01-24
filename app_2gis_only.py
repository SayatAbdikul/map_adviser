"""
Simplified FastAPI app with only 2GIS endpoints
For testing your 2GIS integration independently
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from models import Place
from doublegis_service import DoubleGISService

app = FastAPI(
    title="2GIS API Service",
    description="Standalone 2GIS API integration for testing",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
doublegis_service = DoubleGISService()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "2GIS API Service - Ready for testing",
        "your_part": "2GIS API integration",
        "endpoints": {
            "/search": "GET - Search for places",
            "/route": "POST - Build route through places",
            "/health": "GET - Health check"
        }
    }


@app.get("/search", response_model=List[Place])
async def search_places(
    query: str = Query(..., description="Search query (e.g., 'restaurants', 'museums')"),
    city: str = Query("moscow", description="City to search in"),
    limit: int = Query(10, description="Maximum number of results", ge=1, le=50)
):
    """
    Search for places using 2GIS API
    
    Example: /search?query=restaurants&city=moscow&limit=5
    """
    try:
        places = await doublegis_service.search_places(query, city, limit)
        
        if not places:
            raise HTTPException(
                status_code=404,
                detail=f"No places found for query '{query}' in {city}"
            )
        
        return places
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching places: {str(e)}"
        )


@app.post("/route")
async def build_route(places: List[Place]):
    """
    Build a route through multiple places using 2GIS Routing API
    
    Request body: Array of Place objects with at least 2 places
    
    Example:
    ```json
    [
        {
            "id": "123",
            "name": "Place 1",
            "address": "Address 1",
            "lat": 55.7558,
            "lon": 37.6173
        },
        {
            "id": "456",
            "name": "Place 2",
            "address": "Address 2",
            "lat": 55.7600,
            "lon": 37.6200
        }
    ]
    ```
    """
    try:
        if len(places) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 places to build a route"
            )
        
        # Build route
        route_info = await doublegis_service.build_route(places)
        
        # Generate URL
        route_url = doublegis_service.generate_route_url(places)
        
        return {
            "places": places,
            "total_distance": route_info['total_distance'],
            "total_distance_km": round(route_info['total_distance'] / 1000, 2),
            "total_duration": route_info['total_duration'],
            "total_duration_min": round(route_info['total_duration'] / 60, 1),
            "route_url": route_url,
            "route_data": route_info['route_data']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error building route: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "2GIS API Integration",
        "api_key_configured": doublegis_service.api_key is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
