"""FastAPI application for the path finding agent."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.path_agent import plan_route
from models.schemas import ErrorResponse, RouteRequest, RouteResponse
from room_manager import room_manager
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
    
    # Start room cleanup task
    room_manager.start_cleanup_task()
    
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

    uvicorn.run(app, host="0.0.0.0", port=8001)


# ==================== Room Sync API ====================

class CreateRoomRequest(BaseModel):
    """Request to create a new room."""
    name: str = "Trip Room"


class CreateRoomResponse(BaseModel):
    """Response after creating a room."""
    code: str
    name: str


class RoomInfoResponse(BaseModel):
    """Room information response."""
    code: str
    name: str
    member_count: int


@app.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(request: CreateRoomRequest):
    """Create a new collaboration room."""
    room = room_manager.create_room(name=request.name)
    return CreateRoomResponse(code=room.code, name=room.name)


@app.get("/api/rooms/{code}", response_model=RoomInfoResponse)
async def get_room(code: str):
    """Get room information by code."""
    room = room_manager.get_room(code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomInfoResponse(
        code=room.code,
        name=room.name,
        member_count=room.member_count,
    )


@app.delete("/api/rooms/{code}")
async def delete_room(code: str):
    """Delete a room (close it)."""
    if room_manager.delete_room(code.upper()):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Room not found")


@app.websocket("/ws/room/{code}")
async def websocket_room(websocket: WebSocket, code: str, nickname: str = "Anonymous"):
    """
    WebSocket endpoint for real-time room synchronization.
    
    Query params:
    - nickname: Display name for the user
    
    Message types (client -> server):
    - {"type": "location", "lat": float, "lon": float, "heading": float?, "accuracy": float?}
    - {"type": "heartbeat"}
    
    Message types (server -> client):
    - {"type": "room_state", ...} - Full room state on join
    - {"type": "member_joined", ...}
    - {"type": "member_left", ...}
    - {"type": "location_update", ...}
    - {"type": "host_changed", ...}
    - {"type": "error", "message": str}
    """
    room = room_manager.get_room(code.upper())
    if not room:
        await websocket.close(code=4004, reason="Room not found")
        return
    
    await websocket.accept()
    
    # Join the room
    member = await room_manager.join_room(room, websocket, nickname)
    
    # Send initial room state to the new member
    room_state = room_manager.get_room_state(room)
    room_state["type"] = "room_state"
    room_state["your_id"] = member.id
    room_state["your_color"] = member.color
    await websocket.send_json(room_state)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "location":
                await room_manager.update_location(
                    room=room,
                    member_id=member.id,
                    lat=data.get("lat"),
                    lon=data.get("lon"),
                    heading=data.get("heading"),
                    accuracy=data.get("accuracy"),
                )
            
            elif msg_type == "heartbeat":
                await room_manager.heartbeat(room, member.id)
                await websocket.send_json({"type": "heartbeat_ack"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        await room_manager.leave_room(room, member.id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await room_manager.leave_room(room, member.id)
    uvicorn.run(app, host="0.0.0.0", port=8000)
