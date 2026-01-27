"""Path finding agent using LiteLLM with Gemini."""

import json
import logging
import os
from typing import Literal

import litellm

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

# Configure LiteLLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")

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



# Define tools for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geocode_address",
            "description": "Convert an address string to geographic coordinates. Use region_id (from search_region) to limit search to a specific city/region.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "The address to geocode (e.g., 'Red Square', 'Nazarbayev University')"
                    },
                    "city": {
                        "type": "string",
                        "description": "Optional city name to narrow the search"
                    },
                    "region_id": {
                        "type": "integer",
                        "description": "Region ID to limit search to a specific city/region (get from search_region tool)"
                    }
                },
                "required": ["address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nearby_places",
            "description": "Search for places by category or name near a specific location or within a region. You can search by location (longitude/latitude) or by region_id (from search_region tool).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'bank', 'cafe', 'pharmacy')"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the search center point (optional if region_id provided)"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the search center point (optional if region_id provided)"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters (default 5000, used with location)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 5)"
                    },
                    "region_id": {
                        "type": "integer",
                        "description": "Region ID to limit search to a specific city/region (get from search_region tool)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_route",
            "description": "Calculate a route through multiple points. Returns: geometry (array of [lon, lat] coordinates for the route polyline), total_distance (meters), total_duration (seconds), segments (distance/duration per leg), maneuvers (turn-by-turn directions with instruction, type, street_name, distance, duration).",
            "parameters": {
                "type": "object",
                "properties": {
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "longitude": {"type": "number"},
                                "latitude": {"type": "number"}
                            },
                            "required": ["longitude", "latitude"]
                        },
                        "description": "List of points with longitude and latitude"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking"],
                        "description": "Transportation mode"
                    },
                    "optimize": {
                        "type": "string",
                        "enum": ["distance", "time"],
                        "description": "What to optimize for"
                    }
                },
                "required": ["points"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_optimal_place",
            "description": "Find the best place of a category that minimizes detour from start to end",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'bank', 'cafe')"
                    },
                    "start_longitude": {"type": "number"},
                    "start_latitude": {"type": "number"},
                    "end_longitude": {"type": "number"},
                    "end_latitude": {"type": "number"},
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking"],
                        "description": "Transportation mode"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of alternatives to consider"
                    }
                },
                "required": ["query", "start_longitude", "start_latitude", "end_longitude", "end_latitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_region",
            "description": "Search for geographic regions by name to get region IDs. Use this when a user mentions a city or region name to find the correct region ID for limiting subsequent searches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "City or region name (e.g., 'Almaty', 'Moscow', 'Dubai')"
                    },
                    "include_bounds": {
                        "type": "boolean",
                        "description": "Whether to include the geographic bounding box"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_region_from_coordinates",
            "description": "Find which region contains the given coordinates. Use this to determine the region for a specific location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the point"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the point"
                    }
                },
                "required": ["longitude", "latitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_location_in_region",
            "description": "Check if coordinates are within a specific region. Use this to validate that a destination is within the user's specified region before building a route.",
            "parameters": {
                "type": "object",
                "properties": {
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the point to validate"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the point to validate"
                    },
                    "region_id": {
                        "type": "integer",
                        "description": "The region ID to validate against (from search_region tool)"
                    }
                },
                "required": ["longitude", "latitude", "region_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_public_transport_route",
            "description": "Calculate a public transport route using buses, metro/subway, trams, trolleybuses, trains, and other public transport modes. Use this when a user wants to travel using public transportation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_longitude": {
                        "type": "number",
                        "description": "Longitude of starting point"
                    },
                    "start_latitude": {
                        "type": "number",
                        "description": "Latitude of starting point"
                    },
                    "end_longitude": {
                        "type": "number",
                        "description": "Longitude of ending point"
                    },
                    "end_latitude": {
                        "type": "number",
                        "description": "Latitude of ending point"
                    },
                    "start_name": {
                        "type": "string",
                        "description": "Human-readable name for starting point (e.g., 'Red Square')"
                    },
                    "end_name": {
                        "type": "string",
                        "description": "Human-readable name for ending point (e.g., 'Central Station')"
                    },
                    "transport_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Allowed transport types: 'metro', 'bus', 'trolleybus', 'tram', 'shuttle_bus', 'suburban_train', 'funicular', 'monorail', 'river_transport'. Default: ['metro', 'bus', 'trolleybus', 'tram']"
                    },
                    "intermediate_points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "longitude": {"type": "number"},
                                "latitude": {"type": "number"},
                                "name": {"type": "string"}
                            },
                            "required": ["longitude", "latitude"]
                        },
                        "description": "Optional list of waypoints to visit between start and end"
                    },
                    "locale": {
                        "type": "string",
                        "description": "Language code for response (default: 'en')"
                    }
                },
                "required": ["start_longitude", "start_latitude", "end_longitude", "end_latitude"]
            }
        }
    }
]


async def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool and return the result."""
    logger.info(f"Executing tool: {name} with args: {arguments}")
    places_client = get_places_client()
    routing_client = get_routing_client()
    regions_client = get_regions_client()
    from services.public_transport import get_public_transport_client
    public_transport_client = get_public_transport_client()

    try:
        if name == "geocode_address":
            logger.info('geocode_address called with', arguments)
            result = await places_client.geocode(
                arguments["address"],
                arguments.get("city"),
                arguments.get("region_id")
            )
            logger.info(f"geocode_address result: {result}")
            return result

        elif name == "search_nearby_places":
            logger.info('search_nearby_places called with', arguments)
            location = None
            if "longitude" in arguments and "latitude" in arguments:
                location = (arguments["longitude"], arguments["latitude"])
            result = await places_client.search_places(
                arguments["query"],
                location,
                arguments.get("radius", 5000),
                arguments.get("limit", 5),
                arguments.get("region_id")
            )
            logger.info(f"search_nearby_places result: {result}")
            return result

        elif name == "calculate_route":
            points = [(p["longitude"], p["latitude"]) for p in arguments["points"]]
            result = await routing_client.get_route(
                points,
                arguments.get("mode", "driving"),
                arguments.get("optimize", "time")
            )
            logger.info(f"calculate_route result: {result}")
            return result

        elif name == "find_optimal_place":
            # Search for places along the route
            places = await places_client.search_places_along_route(
                arguments["query"],
                (arguments["start_longitude"], arguments["start_latitude"]),
                (arguments["end_longitude"], arguments["end_latitude"]),
                limit=arguments.get("limit", 5)
            )

            if not places:
                return {"error": f"No {arguments['query']} found along the route"}

            # Calculate detour for each place
            start = (arguments["start_longitude"], arguments["start_latitude"])
            end = (arguments["end_longitude"], arguments["end_latitude"])
            mode = arguments.get("mode", "driving")

            places_with_detour = []
            for place in places:
                coords = place["coordinates"]
                if coords[0] is None or coords[1] is None:
                    continue

                via = (coords[0], coords[1])
                detour = await routing_client.calculate_detour(start, end, via, mode)

                if "error" not in detour:
                    places_with_detour.append({
                        **place,
                        "extra_distance": detour["extra_distance"],
                        "extra_duration": detour["extra_duration"],
                    })

            if not places_with_detour:
                return {
                    "best": places[0],
                    "alternatives": places[1:] if len(places) > 1 else [],
                }

            places_with_detour.sort(key=lambda p: p["extra_duration"])

            result = {
                "best": places_with_detour[0],
                "alternatives": places_with_detour[1:],
            }
            logger.info(f"find_optimal_place result: {result}")
            return result

        elif name == "search_region":
            result = await regions_client.search_by_name(
                arguments["query"],
                include_bounds=arguments.get("include_bounds", False)
            )
            logger.info(f"search_region result: {result}")
            return result

        elif name == "get_region_from_coordinates":
            result = await regions_client.search_by_coordinates(
                arguments["longitude"],
                arguments["latitude"]
            )
            if result is None:
                result = {"error": f"No region found for coordinates ({arguments['longitude']}, {arguments['latitude']})"}
            logger.info(f"get_region_from_coordinates result: {result}")
            return result

        elif name == "validate_location_in_region":
            result = await regions_client.validate_location_in_region(
                arguments["longitude"],
                arguments["latitude"],
                arguments["region_id"]
            )
            logger.info(f"validate_location_in_region result: {result}")
            return result

        elif name == "calculate_public_transport_route":
            # Parse intermediate points if provided
            intermediate_points = None
            if "intermediate_points" in arguments and arguments["intermediate_points"]:
                intermediate_points = [
                    (pt["longitude"], pt["latitude"], pt.get("name", "Waypoint"))
                    for pt in arguments["intermediate_points"]
                ]

            result = await public_transport_client.get_public_transport_route(
                source_point=(arguments["start_longitude"], arguments["start_latitude"]),
                target_point=(arguments["end_longitude"], arguments["end_latitude"]),
                source_name=arguments.get("start_name", "Start Point"),
                target_name=arguments.get("end_name", "End Point"),
                intermediate_points=intermediate_points,
                transport_types=arguments.get("transport_types"),
                locale=arguments.get("locale", "en"),
                include_pedestrian_instructions=True,
            )
            logger.info(f"calculate_public_transport_route result: {result}")
            return result

        else:
            result = {"error": f"Unknown tool: {name}"}
            logger.info(f"Tool {name} result: {result}")
            return result

    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return {"error": str(e)}


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
    mode_instructions = build_mode_instructions(mode)
    system_prompt = get_path_agent_system_prompt()
    user_prompt = build_path_agent_user_prompt(query, mode_instructions)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Agentic loop - keep calling until we get a final response
    max_iterations = 10
    for iteration in range(max_iterations):
        logger.info(f"Agent iteration {iteration + 1}")
        response = await litellm.acompletion(
            model=GEMINI_MODEL,
            messages=messages,
            tools=TOOLS,
        )

        choice = response.choices[0]
        message = choice.message
        logger.info(f"LLM response - content: {message.content[:200] if message.content else 'None'}...\n\n\n")
        logger.info(f"LLM response - tool_calls: {message.tool_calls}\n\n\n")

        # Add assistant message to history
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls if message.tool_calls else None
        })

        # If no tool calls, we have the final response
        if not message.tool_calls:
            response_text = message.content or ""
            logger.info(f"Final response: {response_text}...\n\n\n")
            break

        # Execute tool calls
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            # Execute the tool
            result = await execute_tool(func_name, func_args)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
    else:
        return {"error": "Max iterations reached without final response"}

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
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
        return {
            "error": f"Failed to parse agent response: {str(e)}",
            "raw_response": response_text,
        }
