"""FastAPI application for the path finding agent."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.path_agent import plan_route
from models.schemas import ErrorResponse, RouteRequest, RouteResponse
from services.gis_places import close_places_client
from services.gis_routing import close_routing_client

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Validate required environment variables on startup
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY environment variable is required")
    if not os.getenv("GIS_API_KEY"):
        raise RuntimeError("GIS_API_KEY environment variable is required")
    yield
    # Cleanup: close shared HTTP clients on shutdown
    await close_places_client()
    await close_routing_client()


app = FastAPI(
    title="Path Finder Agent",
    description="AI agent for finding optimal routes through multiple locations",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post(
    "/route",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_route(request: RouteRequest):
    """
    Plan an optimal route based on natural language request.

    The LLM will automatically decide whether to optimize for time or distance
    based on the user's query context.

    Example request:
    ```json
    {
        "query": "Go from Red Square to a bank, then to a cafe, then to Gorky Park",
        "mode": "driving"
    }
    ```
    """
    try:
        result = await plan_route(
            query=request.query,
            mode=request.mode,
        )

        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": result.get("error", "Unknown error"),
                    "raw_response": result.get("raw_response", "")
                },
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
