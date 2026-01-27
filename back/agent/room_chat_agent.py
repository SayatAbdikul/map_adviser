"""Room chat agent for processing queries with room context."""

import json
import logging
import os
from typing import TYPE_CHECKING

import litellm

from agent.tools.meeting_place import MemberLocation
from agent.prompts.room_chat_prompts import get_room_chat_system_prompt
from services.gis_places import get_places_client
from services.gis_routing import get_routing_client

if TYPE_CHECKING:
    from room_manager import Room

# Set up logging
logger = logging.getLogger(__name__)

# Configure LiteLLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")


# Tools for room chat
ROOM_CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_meeting_place",
            "description": "Find the best meeting place for all room members. Calculates centroid of all locations and finds places that minimize total travel time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'кафе', 'ресторан', 'парк')"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking"],
                        "description": "Transportation mode (default: driving)"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters from centroid (default: 3000)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nearby_places",
            "description": "Search for places near a specific location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of search center"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of search center"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters (default: 3000)"
                    }
                },
                "required": ["query", "longitude", "latitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_route",
            "description": "Calculate route from all members to a destination point.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination_longitude": {
                        "type": "number",
                        "description": "Destination longitude"
                    },
                    "destination_latitude": {
                        "type": "number",
                        "description": "Destination latitude"
                    },
                    "destination_name": {
                        "type": "string",
                        "description": "Name of the destination"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking"],
                        "description": "Transportation mode"
                    }
                },
                "required": ["destination_longitude", "destination_latitude"]
            }
        }
    },
]


def _get_room_context(room: "Room") -> str:
    """Build a context string describing the room and its members."""
    members_with_loc = room.get_members_with_locations()
    
    context_parts = [
        f"Комната: {room.name}",
        f"Участников: {room.member_count}",
        f"Участников с местоположением: {len(members_with_loc)}",
    ]
    
    if members_with_loc:
        context_parts.append("\nУчастники с координатами:")
        for member, location in members_with_loc:
            context_parts.append(
                f"- {member.nickname}: ({location.lat:.6f}, {location.lon:.6f})"
            )
    
    members_without_loc = [
        m for m in room.members.values() if m.location is None
    ]
    if members_without_loc:
        context_parts.append("\nУчастники БЕЗ местоположения:")
        for member in members_without_loc:
            context_parts.append(f"- {member.nickname}")
    
    return "\n".join(context_parts)


def _get_member_locations(room: "Room") -> list[MemberLocation]:
    """Get member locations as MemberLocation objects for the tool."""
    result = []
    for member, location in room.get_members_with_locations():
        result.append(MemberLocation(
            member_id=member.id,
            member_nickname=member.nickname,
            longitude=location.lon,
            latitude=location.lat,
        ))
    return result


async def _execute_room_tool(
    name: str,
    arguments: dict,
    room: "Room"
) -> dict:
    """Execute a room chat tool."""
    try:
        logger.info(f"Executing room tool: {name} with args: {arguments}")
        
        if name == "find_meeting_place":
            member_locations = _get_member_locations(room)
            
            if len(member_locations) < 2:
                return {
                    "error": "Нужно минимум 2 участника с местоположением для поиска места встречи",
                    "members_with_location": len(member_locations),
                }
            
            # Import and call the implementation function directly (not the decorated tool)
            from agent.tools.meeting_place import find_meeting_place_impl
            
            result = await find_meeting_place_impl(
                query=arguments["query"],
                member_locations=member_locations,
                mode=arguments.get("mode", "driving"),
                limit=5,
                radius=arguments.get("radius", 3000),
            )
            logger.info(f"find_meeting_place result: {result}")
            return result
        
        elif name == "search_nearby_places":
            places_client = get_places_client()
            result = await places_client.search_places(
                query=arguments["query"],
                location=(arguments["longitude"], arguments["latitude"]),
                radius=arguments.get("radius", 3000),
                limit=5,
            )
            logger.info(f"search_nearby_places result: {result}")
            return result
        
        elif name == "calculate_route":
            # Calculate routes from all members to destination
            routing_client = get_routing_client()
            member_locations = _get_member_locations(room)
            
            if not member_locations:
                return {"error": "Нет участников с местоположением"}
            
            dest_lon = arguments["destination_longitude"]
            dest_lat = arguments["destination_latitude"]
            dest_name = arguments.get("destination_name", "Место назначения")
            mode = arguments.get("mode", "driving")
            
            routes = []
            combined_geometry = []
            
            for member in member_locations:
                route = await routing_client.get_route(
                    points=[(member.longitude, member.latitude), (dest_lon, dest_lat)],
                    mode=mode,
                    optimize="time",
                )
                
                if "error" not in route:
                    routes.append({
                        "member_id": member.member_id,
                        "member_nickname": member.member_nickname,
                        "distance_meters": route.get("total_distance"),
                        "duration_seconds": route.get("total_duration"),
                        "duration_minutes": round(route.get("total_duration", 0) / 60, 1),
                        "geometry": route.get("geometry", []),
                    })
                    # Add geometry to combined
                    if route.get("geometry"):
                        combined_geometry.extend(route["geometry"])
            
            result = {
                "destination": {
                    "name": dest_name,
                    "coordinates": [dest_lon, dest_lat],
                },
                "member_routes": routes,
                "combined_geometry": combined_geometry,
            }
            logger.info(f"calculate_route result: routes for {len(routes)} members")
            return result
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        logger.error(f"Room tool {name} error: {e}")
        return {"error": str(e)}


async def process_room_chat(room: "Room", query: str) -> dict:
    """
    Process a room chat query with AI agent.
    
    Args:
        room: The Room object with members and their locations
        query: User's natural language query
    
    Returns:
        Dictionary with:
        - response: Text response to display
        - route_data: Optional route data to display on map
    """
    room_context = _get_room_context(room)
    
    system_prompt = get_room_chat_system_prompt(room_context)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    # Track route data if we find a meeting place
    route_data = None
    
    # Agentic loop
    max_iterations = 8
    for iteration in range(max_iterations):
        logger.info(f"Room chat iteration {iteration + 1}")
        
        response = await litellm.acompletion(
            model=GEMINI_MODEL,
            messages=messages,
            tools=ROOM_CHAT_TOOLS,
        )
        
        choice = response.choices[0]
        message = choice.message
        logger.info(f"LLM response - tool_calls: {message.tool_calls}")
        
        # Add assistant message to history
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls if message.tool_calls else None
        })
        
        # If no tool calls, we have the final response
        if not message.tool_calls:
            response_text = message.content or "Не удалось обработать запрос"
            logger.info(f"Final room chat response: {response_text[:200]}...")
            break
        
        # Execute tool calls
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            # Execute the tool
            result = await _execute_room_tool(func_name, func_args, room)
            
            # If this is a meeting place result, extract route data
            if func_name == "find_meeting_place" and "best" in result:
                best = result["best"]
                route_data = {
                    "type": "meeting_place",
                    "destination": {
                        "name": best.get("name"),
                        "address": best.get("address"),
                        "coordinates": best.get("coordinates"),
                    },
                    "member_travel_times": best.get("member_travel_times", []),
                    "centroid": result.get("centroid"),
                }
            
            # If this is a route calculation, store the geometry
            elif func_name == "calculate_route" and "member_routes" in result:
                route_data = {
                    "type": "routes_to_destination",
                    "destination": result.get("destination"),
                    "member_routes": result.get("member_routes", []),
                }
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
    else:
        return {
            "response": "Превышено максимальное количество итераций. Попробуйте переформулировать запрос.",
            "route_data": None,
        }
    
    return {
        "response": response_text,
        "route_data": route_data,
    }
