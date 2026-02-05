"""Room chat agent for processing queries with room context."""

import json
import logging
import os
from typing import TYPE_CHECKING, Any, Optional

from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.tools.meeting_place import MemberLocation
from agent.prompts.room_chat_prompts import get_room_chat_system_prompt
from services.gis_places import get_places_client
from services.gis_routing import get_routing_client

if TYPE_CHECKING:
    from room_manager import Room

# Set up logging
logger = logging.getLogger(__name__)

# Configure OpenAI via LiteLLM
OPENAI_MODEL = os.getenv("GEMINI_MODEL", "gpt-4.1-mini")


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


def _build_room_chat_tools(room: "Room"):
    """Create tool set bound to a specific room."""

    @tool
    async def find_meeting_place(
        query: str,
        mode: str = "driving",
        radius: int = 3000,
    ) -> dict:
        member_locations = _get_member_locations(room)
        if len(member_locations) < 2:
            return {
                "error": "Нужно минимум 2 участника с местоположением для поиска места встречи",
                "members_with_location": len(member_locations),
            }
        from agent.tools.meeting_place import find_meeting_place_impl

        return await find_meeting_place_impl(
            query=query,
            member_locations=member_locations,
            mode=mode,
            limit=5,
            radius=radius,
        )

    @tool
    async def search_nearby_places(
        query: str,
        longitude: float,
        latitude: float,
        radius: int = 3000,
    ) -> dict:
        places_client = get_places_client()
        return await places_client.search_places(
            query=query,
            location=(longitude, latitude),
            radius=radius,
            limit=5,
        )

    @tool
    async def calculate_route(
        destination_longitude: float,
        destination_latitude: float,
        destination_name: str = "Место назначения",
        mode: str = "driving",
    ) -> dict:
        routing_client = get_routing_client()
        member_locations = _get_member_locations(room)

        if not member_locations:
            return {"error": "Нет участников с местоположением"}

        routes = []
        combined_geometry = []

        for member in member_locations:
            route = await routing_client.get_route(
                points=[(member.longitude, member.latitude), (destination_longitude, destination_latitude)],
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
                if route.get("geometry"):
                    combined_geometry.extend(route["geometry"])

        return {
            "destination": {
                "name": destination_name,
                "coordinates": [destination_longitude, destination_latitude],
            },
            "member_routes": routes,
            "combined_geometry": combined_geometry,
        }

    return [find_meeting_place, search_nearby_places, calculate_route]


def _build_room_chat_agent(tools: list, system_prompt: str):
    """Create LangGraph agent for room chat."""
    llm = ChatLiteLLM(model=OPENAI_MODEL, temperature=0)
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )


def _coerce_observation(observation: Any) -> Optional[dict]:
    """Convert tool observations to a dict if possible."""
    if isinstance(observation, dict):
        return observation
    if isinstance(observation, str):
        try:
            return json.loads(observation)
        except json.JSONDecodeError:
            return None
    return None


def _extract_route_data(messages: list) -> Optional[dict]:
    """Derive map payload from the latest relevant tool response."""
    if not messages:
        return None

    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        
        content = msg.content
        parsed = _coerce_observation(content)
        if not parsed:
            continue

        tool_name = msg.name if hasattr(msg, 'name') else None
        if tool_name == "find_meeting_place" and "best" in parsed:
            best = parsed["best"]
            return {
                "type": "meeting_place",
                "destination": {
                    "name": best.get("name"),
                    "address": best.get("address"),
                    "coordinates": best.get("coordinates"),
                },
                "member_travel_times": best.get("member_travel_times", []),
                "centroid": parsed.get("centroid"),
            }

        if tool_name == "calculate_route" and "member_routes" in parsed:
            return {
                "type": "routes_to_destination",
                "destination": parsed.get("destination"),
                "member_routes": parsed.get("member_routes", []),
            }

    return None


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
    logger.info("OpenAI model: %s", OPENAI_MODEL)
    room_context = _get_room_context(room)
    
    system_prompt = get_room_chat_system_prompt(room_context)
    tools = _build_room_chat_tools(room)
    agent = _build_room_chat_agent(tools, system_prompt)

    agent_result = await agent.ainvoke(
        {"messages": [HumanMessage(content=query)]}
    )

    messages = agent_result.get("messages", [])
    response_text = "Не удалось обработать запрос"
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content
            break
    
    if not isinstance(response_text, str):
        response_text = str(response_text)

    route_data = _extract_route_data(messages)

    return {"response": response_text, "route_data": route_data}
