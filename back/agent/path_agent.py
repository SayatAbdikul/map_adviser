"""Path finding agent powered by LangChain with LiteLLM backend."""

import json
import logging
import os
from typing import Any, Literal, Optional

from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

# Prompt helpers
from agent.prompts.path_agent_prompts import (
    build_mode_instructions,
    build_path_agent_user_prompt,
    get_path_agent_system_prompt,
)

# Set up logging
logger = logging.getLogger(__name__)

from services.gis_places import get_places_client
from services.gis_routing import get_routing_client
from services.gis_regions import get_regions_client
from services.public_transport import get_public_transport_client
from services.location_store import get_location_store

# Configure OpenAI via LiteLLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gpt-4.1-mini")

DISTANCE_KEYWORDS = [
    "shortest",
    "short",
    "closest",
    "near",
    "distance",
    "короч",
    "кратчай",
    "ближ",
    "экон",
]
TIME_KEYWORDS = [
    "fast",
    "quick",
    "asap",
    "urgent",
    "hurry",
    "быстр",
    "сроч",
    "скорее",
    "время",
]


def choose_optimization(query: str) -> Literal["distance", "time"]:
    """Prefer shortest path unless query explicitly asks for speed."""
    lower = query.lower()
    if any(keyword in lower for keyword in TIME_KEYWORDS):
        return "time"
    if any(keyword in lower for keyword in DISTANCE_KEYWORDS):
        return "distance"
    return "distance"


def extract_route_points(route: dict) -> list[tuple[float, float]]:
    """Extract ordered (lon, lat) points from route waypoints."""
    waypoints = route.get("waypoints") or []
    if not isinstance(waypoints, list):
        return []
    ordered = sorted(waypoints, key=lambda w: w.get("order", 0))
    points: list[tuple[float, float]] = []
    for waypoint in ordered:
        location = waypoint.get("location") or {}
        lon = location.get("lon", waypoint.get("lon"))
        lat = location.get("lat", waypoint.get("lat"))
        if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
            points.append((float(lon), float(lat)))
    return points


def apply_route_metrics(route: dict, route_result: dict) -> None:
    """Overwrite geometry/metrics with routing API results."""
    total_duration = route_result.get("total_duration")
    route["route_geometry"] = route_result.get("geometry", [])
    route["total_distance_meters"] = route_result.get("total_distance")
    route["total_duration_minutes"] = round(total_duration / 60, 1) if total_duration else None

    segments = []
    for segment in route_result.get("segments", []) or []:
        segments.append({
            "from_waypoint": segment.get("from"),
            "to_waypoint": segment.get("to"),
            "distance_meters": segment.get("distance"),
            "duration_seconds": segment.get("duration"),
        })
    if segments:
        route["segments"] = segments

    directions = []
    for maneuver in route_result.get("maneuvers", []) or []:
        directions.append({
            "instruction": maneuver.get("instruction", ""),
            "type": maneuver.get("type", ""),
            "street_name": maneuver.get("street_name", ""),
            "distance_meters": maneuver.get("distance"),
            "duration_seconds": maneuver.get("duration"),
        })
    if directions:
        route["directions"] = directions



@tool
async def geocode_address(
    address: str,
    city: Optional[str] = None,
    region_id: Optional[int] = None,
) -> dict:
    """Convert an address string to geographic coordinates."""
    logger.info("geocode_address args: %s", {"address": address, "city": city, "region_id": region_id})
    places_client = get_places_client()
    return await places_client.geocode(address, city, region_id)


@tool
async def search_nearby_places(
    query: str,
    longitude: Optional[float] = None,
    latitude: Optional[float] = None,
    radius: int = 5000,
    limit: int = 5,
    region_id: Optional[int] = None,
) -> dict:
    """Search for places by category or name near a location or within a region."""
    logger.info(
        "search_nearby_places args: %s",
        {"query": query, "longitude": longitude, "latitude": latitude, "radius": radius, "limit": limit, "region_id": region_id},
    )
    location = None
    if longitude is not None and latitude is not None:
        location = (longitude, latitude)
    places_client = get_places_client()
    return await places_client.search_places(query, location, radius, limit, region_id)


@tool
async def calculate_route(
    points: list[dict[str, float]],
    mode: str = "driving",
    optimize: str = "time",
) -> dict:
    """Calculate a route through multiple points."""
    logger.info("calculate_route args: %s", {"points": points, "mode": mode, "optimize": optimize})
    routing_client = get_routing_client()
    coords: list[tuple[float, float]] = []
    for point in points:
        lon = point.get("longitude")
        lat = point.get("latitude")
        if lon is None or lat is None:
            continue
        coords.append((lon, lat))
    if len(coords) < 2:
        return {"error": "At least two points are required to build a route"}
    return await routing_client.get_route(coords, mode, optimize)


@tool
async def find_optimal_place(
    query: str,
    start_longitude: float,
    start_latitude: float,
    end_longitude: float,
    end_latitude: float,
    mode: str = "driving",
    limit: int = 5,
) -> dict:
    """Find the best place of a category that minimizes detour from start to end."""
    logger.info(
        "find_optimal_place args: %s",
        {
            "query": query,
            "start": (start_longitude, start_latitude),
            "end": (end_longitude, end_latitude),
            "mode": mode,
            "limit": limit,
        },
    )
    places_client = get_places_client()
    routing_client = get_routing_client()

    places = await places_client.search_places_along_route(
        query,
        (start_longitude, start_latitude),
        (end_longitude, end_latitude),
        limit=limit,
    )

    if not places:
        return {"error": f"No {query} found along the route"}

    places_with_detour = []
    for place in places:
        coords = place["coordinates"]
        if coords[0] is None or coords[1] is None:
            continue

        via = (coords[0], coords[1])
        detour = await routing_client.calculate_detour(
            (start_longitude, start_latitude),
            (end_longitude, end_latitude),
            via,
            mode,
        )

        if "error" not in detour:
            places_with_detour.append(
                {
                    **place,
                    "extra_distance": detour["extra_distance"],
                    "extra_duration": detour["extra_duration"],
                }
            )

    if not places_with_detour:
        return {
            "best": places[0],
            "alternatives": places[1:] if len(places) > 1 else [],
        }

    places_with_detour.sort(key=lambda p: p["extra_duration"])
    return {
        "best": places_with_detour[0],
        "alternatives": places_with_detour[1:],
    }


@tool
async def search_region(query: str, include_bounds: bool = False) -> dict:
    """Search for geographic regions by name to get region IDs."""
    regions_client = get_regions_client()
    result = await regions_client.search_by_name(query, include_bounds=include_bounds)
    logger.info("search_region result count: %s", len(result) if hasattr(result, "__len__") else "n/a")
    return result


@tool
async def get_region_from_coordinates(longitude: float, latitude: float) -> dict:
    """Find which region contains the given coordinates."""
    regions_client = get_regions_client()
    result = await regions_client.search_by_coordinates(longitude, latitude)
    if result is None:
        return {"error": f"No region found for coordinates ({longitude}, {latitude})"}
    return result


@tool
async def validate_location_in_region(longitude: float, latitude: float, region_id: int) -> dict:
    """Check if coordinates are within a specific region."""
    regions_client = get_regions_client()
    return await regions_client.validate_location_in_region(longitude, latitude, region_id)


@tool
async def calculate_public_transport_route(
    start_longitude: float,
    start_latitude: float,
    end_longitude: float,
    end_latitude: float,
    start_name: str = "Start Point",
    end_name: str = "End Point",
    transport_types: Optional[list[str]] = None,
    intermediate_points: Optional[list[dict[str, Any]]] = None,
    locale: str = "en",
) -> dict:
    """Calculate a public transport route."""
    public_transport_client = get_public_transport_client()

    parsed_intermediate: Optional[list[tuple[float, float, str]]] = None
    if intermediate_points:
        parsed_intermediate = []
        for point in intermediate_points:
            lon = point.get("longitude")
            lat = point.get("latitude")
            if lon is None or lat is None:
                continue
            parsed_intermediate.append((lon, lat, point.get("name", "Waypoint")))

    return await public_transport_client.get_public_transport_route(
        source_point=(start_longitude, start_latitude),
        target_point=(end_longitude, end_latitude),
        source_name=start_name,
        target_name=end_name,
        intermediate_points=parsed_intermediate,
        transport_types=transport_types,
        locale=locale,
        include_pedestrian_instructions=True,
    )


@tool
async def save_location(
    key: str,
    longitude: float,
    latitude: float,
    description: Optional[str] = None,
) -> dict:
    """Save a named location with coordinates."""
    store = await get_location_store()
    return await store.save_location(
        key=key,
        longitude=longitude,
        latitude=latitude,
        description=description,
    )


@tool
async def search_saved_locations(query: str, limit: int = 5) -> dict:
    """Search saved locations by keyword and return best matches."""
    store = await get_location_store()
    return await store.search(query=query, limit=limit)


PATH_AGENT_TOOLS = [
    geocode_address,
    search_nearby_places,
    calculate_route,
    find_optimal_place,
    search_region,
    get_region_from_coordinates,
    validate_location_in_region,
    calculate_public_transport_route,
    save_location,
    search_saved_locations,
]


def _build_path_agent(system_prompt: str):
    """Create a LangGraph agent for routing tasks."""
    llm = ChatLiteLLM(model=GEMINI_MODEL, temperature=0)
    return create_react_agent(
        model=llm,
        tools=PATH_AGENT_TOOLS,
        prompt=system_prompt,
    )


def _format_reasoning_steps(messages: list) -> list[dict[str, Any]]:
    """Convert LangGraph messages into a concise trace."""
    formatted: list[dict[str, Any]] = []
    if not messages:
        return formatted

    idx = 0
    for msg in messages:
        if isinstance(msg, ToolMessage):
            idx += 1
            tool_name = msg.name if hasattr(msg, 'name') else "tool"
            output_preview = ""
            content = msg.content
            if isinstance(content, (dict, list)):
                try:
                    output_preview = json.dumps(content, ensure_ascii=False)[:400]
                except Exception:
                    output_preview = str(content)[:400]
            else:
                output_preview = str(content)[:400]

            formatted.append(
                {
                    "id": idx,
                    "title": f"Tool result: {tool_name}",
                    "tool": tool_name,
                    "input": "",
                    "output": output_preview,
                }
            )
        elif isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                idx += 1
                tool_name = tool_call.get("name", "tool")
                input_preview = json.dumps(tool_call.get("args", {}), ensure_ascii=False)[:300]
                formatted.append(
                    {
                        "id": idx,
                        "title": f"Call {tool_name}",
                        "tool": tool_name,
                        "input": input_preview,
                        "output": "",
                    }
                )
    return formatted


async def plan_route(
    query: str,
    mode: Literal["driving", "walking", "public_transport"] = "driving",
) -> dict:
    """
    Plan a route based on natural language query.

    Args:
        query: Natural language route request
        mode: Transportation mode - "driving", "walking", or "public_transport"

    Returns:
        Route response dictionary
    """
    logger.info("OpenAI model: %s", GEMINI_MODEL)
    mode_instructions = build_mode_instructions(mode)
    system_prompt = get_path_agent_system_prompt()
    user_prompt = build_path_agent_user_prompt(query, mode_instructions)
    agent = _build_path_agent(system_prompt)

    agent_result = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_prompt)]}
    )

    messages = agent_result.get("messages", [])
    response_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content
            break
    
    if not isinstance(response_text, str):
        response_text = str(response_text)
    logger.info("Agent output (first 200 chars): %s", response_text[:200])
    reasoning_steps = _format_reasoning_steps(messages)

    # Parse the response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        # Try to parse JSON
        result = json.loads(response_text)
        logger.info(f"Successfully parsed JSON response")
        if mode != "public_transport":
            routing_client = get_routing_client()
            optimize = choose_optimization(query)
            request_summary = result.get("request_summary") or {}
            request_summary["optimization_choice"] = optimize
            request_summary["transport_mode"] = mode
            result["request_summary"] = request_summary

            routes = result.get("routes") or []
            for route in routes:
                points = extract_route_points(route)
                if len(points) < 2:
                    continue
                route_result = await routing_client.get_route(points, mode=mode, optimize=optimize)
                if "error" in route_result:
                    logger.warning(f"Routing API error for route {route.get('route_id')}: {route_result.get('error')}")
                    continue
                apply_route_metrics(route, route_result)
        else:
            public_transport_client = get_public_transport_client()
            request_summary = result.get("request_summary") or {}
            request_summary["transport_mode"] = mode
            result["request_summary"] = request_summary

            routes = result.get("routes") or []
            for route in routes:
                waypoints = route.get("waypoints") or []
                if len(waypoints) < 2:
                    continue
                ordered = sorted(waypoints, key=lambda w: w.get("order", 0))
                start = ordered[0]
                end = ordered[-1]
                start_loc = start.get("location") or {}
                end_loc = end.get("location") or {}
                start_point = (start_loc.get("lon"), start_loc.get("lat"))
                end_point = (end_loc.get("lon"), end_loc.get("lat"))
                if None in start_point or None in end_point:
                    continue

                intermediate_points = []
                for waypoint in ordered[1:-1]:
                    loc = waypoint.get("location") or {}
                    lon = loc.get("lon")
                    lat = loc.get("lat")
                    if lon is None or lat is None:
                        continue
                    intermediate_points.append((lon, lat, waypoint.get("name", "Waypoint")))

                pt_result = await public_transport_client.get_public_transport_route(
                    source_point=(start_point[0], start_point[1]),
                    target_point=(end_point[0], end_point[1]),
                    source_name=start.get("name", "Start Point"),
                    target_name=end.get("name", "End Point"),
                    intermediate_points=intermediate_points or None,
                    transport_types=None,
                    locale="en",
                    include_pedestrian_instructions=True,
                )

                alternatives = pt_result.get("routes") if isinstance(pt_result, dict) else None
                if not alternatives:
                    logger.warning("Public transport route had no alternatives for geometry enrichment.")
                    continue

                best = alternatives[0]
                route["route_geometry"] = best.get("route_geometry", [])
                if best.get("total_distance_meters") is not None:
                    route["total_distance_meters"] = best.get("total_distance_meters")
                if best.get("total_duration_seconds") is not None:
                    route["total_duration_minutes"] = round(best.get("total_duration_seconds") / 60, 1)
                if best.get("walking_duration_seconds") is not None:
                    route["walking_duration_minutes"] = round(best.get("walking_duration_seconds") / 60, 1)
                if best.get("transfer_count") is not None:
                    route["transfer_count"] = best.get("transfer_count")
                if best.get("transport_chain"):
                    route["transport_chain"] = best.get("transport_chain")
        if reasoning_steps:
            result["reasoning"] = reasoning_steps
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
        return {
            "error": f"Failed to parse agent response: {str(e)}",
            "raw_response": response_text,
            "reasoning": reasoning_steps,
        }
