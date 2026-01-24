from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from models import PlaceRequest, RouteResponse, Place
from doublegis_service import DoubleGISService
from routing_middleware import (
    routing_middleware, 
    RoutingRequest, 
    RoutingResponse, 
    RoutePoint, 
    TransportMode,
    get_directions
)

# Optional Gemini service (requires google-generativeai package)
try:
    from gemini_service import GeminiService
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GeminiService = None

app = FastAPI(
    title="AI Route Planner",
    description="Plan routes through places using natural language with 2GIS and Gemini AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
doublegis_service = DoubleGISService()
gemini_service = GeminiService() if GEMINI_AVAILABLE else None


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Route Planner API",
        "version": "1.0.0",
        "gemini_available": GEMINI_AVAILABLE,
        "endpoints": {
            "/plan-route": "POST - Plan a route based on natural language description",
            "/search-places": "POST - Search for places using 2GIS",
            "/api/directions": "POST - Get directions between two points",
            "/api/directions/simple": "GET - Simple directions with query params",
            "/api/compare-routes": "POST - Compare all transport modes"
        }
    }


@app.post("/plan-route", response_model=RouteResponse)
async def plan_route(request: PlaceRequest):
    """
    Main endpoint: Takes user's textual description and returns a complete route
    
    Process:
    1. User provides description
    2. Gemini parses it into search queries
    3. Search places in 2GIS
    4. Gemini selects best places
    5. Build route through selected places
    6. Return route with explanation
    
    Note: Requires google-generativeai package to be installed.
    """
    if not GEMINI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Gemini AI service not available. Install google-generativeai package."
        )
    
    try:
        # Step 1: Parse user request with Gemini
        search_queries = await gemini_service.parse_user_request(
            request.description, 
            request.city
        )
        
        if not search_queries:
            raise HTTPException(
                status_code=400, 
                detail="Could not understand your request. Please be more specific."
            )
        
        # Step 2: Search for places using 2GIS
        all_places = []
        for query in search_queries:
            places = await doublegis_service.search_places(query, request.city, limit=5)
            all_places.extend(places)
        
        if not all_places:
            raise HTTPException(
                status_code=404,
                detail="No places found matching your description."
            )
        
        # Remove duplicates based on ID
        unique_places = {place.id: place for place in all_places}.values()
        all_places = list(unique_places)
        
        # Step 3: Let Gemini select and order the best places
        selected_places, selection_explanation = await gemini_service.select_best_places(
            request.description,
            all_places,
            max_places=5
        )
        
        if len(selected_places) < 2:
            raise HTTPException(
                status_code=400,
                detail="Not enough suitable places found. Try a different description."
            )
        
        # Step 4: Build route through selected places
        route_info = await doublegis_service.build_route(selected_places)
        
        # Step 5: Generate route URL for 2GIS
        route_url = doublegis_service.generate_route_url(selected_places)
        
        # Step 6: Generate natural language explanation
        route_description = await gemini_service.generate_route_description(
            request.description,
            selected_places,
            route_info
        )
        
        # Combine explanations
        full_explanation = f"{selection_explanation}\n\n{route_description}"
        
        return RouteResponse(
            places=selected_places,
            route_url=route_url,
            total_distance=route_info.get("total_distance"),
            total_duration=route_info.get("total_duration"),
            gemini_explanation=full_explanation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error planning route: {str(e)}")


@app.post("/search-places", response_model=List[Place])
async def search_places(query: str, city: str = "astana", limit: int = 10):
    """
    Search for places in 2GIS
    
    Args:
        query: Search query (e.g., "restaurants", "museums")
        city: City to search in (default: astana)
        limit: Maximum number of results
    """
    try:
        places = await doublegis_service.search_places(query, city, limit)
        return places
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching places: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============================================================================
# ROUTING MIDDLEWARE ENDPOINTS
# ============================================================================

@app.post("/api/directions", response_model=RoutingResponse)
async def get_route_directions(request: RoutingRequest):
    """
    Get directions/route between places
    
    Accepts JSON with:
    - points: List of {lat, lon, name?} objects
    - mode: "car" | "pedestrian" | "bicycle" | "public_transport"
    - transport_types: (optional) for public transport ["metro", "bus", "tram", "trolleybus"]
    
    Returns route with distance, duration, and step-by-step directions
    """
    try:
        response = await routing_middleware.get_route(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing error: {str(e)}")


@app.post("/api/directions/simple")
async def get_simple_directions(
    points: List[dict],
    mode: str = "car",
    transport_types: List[str] = None
):
    """
    Simplified directions endpoint
    
    Example request body:
    {
        "points": [
            {"lat": 55.753544, "lon": 37.621211, "name": "Red Square"},
            {"lat": 55.826195, "lon": 37.637295, "name": "VDNH"}
        ],
        "mode": "public_transport",
        "transport_types": ["metro", "bus"]
    }
    """
    try:
        result = await get_directions(points, mode, transport_types)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing error: {str(e)}")


@app.post("/api/compare-routes")
async def compare_route_modes(points: List[dict]):
    """
    Compare all transport modes for the same route
    
    Returns times for car, walking, bicycle, and public transport
    """
    try:
        results = {}
        modes = ["car", "pedestrian", "bicycle", "public_transport"]
        
        for mode in modes:
            result = await get_directions(points, mode)
            if result["success"]:
                results[mode] = {
                    "duration_seconds": result["total_duration_seconds"],
                    "duration_text": result["total_duration_text"],
                    "distance_meters": result["total_distance_meters"]
                }
                if mode == "public_transport":
                    results[mode]["transfers"] = result.get("transfers", 0)
                    results[mode]["transport_types"] = result.get("transport_types", [])
            else:
                results[mode] = {"error": result.get("error", "Failed")}
        
        # Sort by duration
        sorted_modes = sorted(
            [(k, v) for k, v in results.items() if "duration_seconds" in v],
            key=lambda x: x[1]["duration_seconds"]
        )
        
        return {
            "comparison": results,
            "fastest_mode": sorted_modes[0][0] if sorted_modes else None,
            "sorted_by_time": [m[0] for m in sorted_modes]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
