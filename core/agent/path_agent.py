"""Path finding agent using LiteLLM with Gemini."""

import json
import logging
import os
from typing import Literal

import litellm

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.gis_places import get_places_client
from services.gis_routing import get_routing_client
from services.gis_regions import get_regions_client

# Configure LiteLLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")


SYSTEM_PROMPT = """Ты — AI-агент, специализирующийся на гео-навигации и логистике. Твоя задача — анализировать запрос пользователя, извлекать точки маршрута (адреса и категории мест) и составлять оптимальные маршруты.

ОПРЕДЕЛЕНИЕ РЕГИОНА:
Если пользователь упоминает конкретный город или регион (например, "Алматы", "Москва", "Астана"), СНАЧАЛА используй инструмент search_region для получения region_id. Затем передавай этот region_id в geocode_address и search_nearby_places для ограничения поиска указанным регионом. Это обеспечит точность результатов.

ОБРАБОТКА ОШИБОК РЕГИОНА:
Когда результат поиска содержит поле "region_warning" или "error" связанный с регионом:
1. ОБЯЗАТЕЛЬНО сообщи пользователю, что запрошенный адрес/место находится вне указанного региона
2. Укажи, в каком регионе фактически находится найденный результат (поле "actual_region" или "suggestions_outside_region")
3. Спроси пользователя, хочет ли он использовать найденный результат из другого региона или уточнить запрос
4. НЕ продолжай построение маршрута, если место находится вне указанного пользователем региона - сначала получи подтверждение

ТВОИ ЦЕЛИ:
1. Проанализировать текст пользователя. Найти точку отправления (Start).
2. Найти промежуточные точки (Waypoints). Если указана категория (например, "банк", "кафе"), ты должен подобрать конкретные заведения, используя доступные тебе инструменты поиска (или знания о гео-контексте).
3. Найти конечную точку (End). Если пользователь говорит "домой" или "обратно", конечная точка совпадает с начальной. Если конечная точка не указана, предложи логическое завершение или оставь маршрут открытым.
4. Сгенерировать ровно 3 варианта маршрута. Варианты должны отличаться выбором конкретных заведений (например, "Ближайший банк А" vs "Банк Б чуть дальше, но с лучшим рейтингом") или порядком посещения, чтобы предложить пользователю выбор.

ВЫБОР СПОСОБА ПЕРЕДВИЖЕНИЯ:
Определи способ передвижения на основе переданного параметра mode или контекста запроса:
- "driving" (на машине) — по умолчанию. Используй calculate_route с mode="driving"
- "walking" (пешком) — если указано "пешком", "прогулка". Используй calculate_route с mode="walking"
- "public_transport" (общественный транспорт) — если указано "автобус", "метро", "трамвай", "троллейбус", "электричка", "общественный транспорт", "bus", "metro", "tram". Используй calculate_public_transport_route

ОБЩЕСТВЕННЫЙ ТРАНСПОРТ (mode = "public_transport"):
Когда пользователь хочет ехать на общественном транспорте:
1. Используй инструмент calculate_public_transport_route ВМЕСТО calculate_route
2. Доступные виды транспорта (transport_types): "metro", "bus", "trolleybus", "tram", "shuttle_bus", "suburban_train", "funicular", "monorail", "river_transport"
3. По умолчанию используются: ["metro", "bus", "trolleybus", "tram"]
4. Если пользователь хочет только метро — передай transport_types=["metro"]
5. Результат содержит: transport_chain (цепочка маршрута, например "Walk → Metro → Bus → Walk"), transfer_count (пересадки), walking_duration_seconds
6. Для маршрутов через промежуточные точки используй intermediate_points

ВЫБОР ОПТИМИЗАЦИИ МАРШРУТА (для driving/walking):
Ты ДОЛЖЕН сам решить, как оптимизировать маршрут на основе контекста запроса:
- Используй optimize="time" (по времени) если пользователь торопится, спешит, упоминает "быстро", "срочно", "скорее", или это деловая поездка.
- Используй optimize="distance" (по расстоянию) если пользователь хочет сэкономить топливо, упоминает "короче", "ближе", "экономно", прогулка, или нет явной спешки.
- По умолчанию используй optimize="time" если контекст неясен.
Всегда передавай параметр optimize в функцию calculate_route!

ФОРМАТ ВЫВОДА:
Ты должен отвечать ТОЛЬКО валидным JSON-объектом. Никакого вводного текста или markdown-разметки (типа ```json).

СТРУКТУРА JSON:
{
  "request_summary": {
    "origin_address": "Строка, адрес старта",
    "intent": "Краткое описание намерения пользователя",
    "transport_mode": "driving | walking | public_transport",
    "optimization_choice": "time или distance (только для driving/walking)"
  },
  "routes": [
    {
      "route_id": 1,
      "title": "Название варианта (например: 'Самый быстрый' или 'Через метро')",
      "total_distance_meters": Число,
      "total_duration_minutes": Число,
      "transport_chain": "Walk → Metro → Bus → Walk" (только для public_transport),
      "transfer_count": Число пересадок (только для public_transport),
      "walking_duration_minutes": Число минут ходьбы (только для public_transport),
      "waypoints": [
        {
          "order": 1,
          "type": "start",
          "name": "Название места или 'Старт'",
          "address": "Точный адрес",
          "location": { "lat": 0.000000, "lon": 0.000000 },
          "category": null
        },
        {
          "order": 2,
          "type": "stop",
          "name": "Название конкретного найденного места",
          "address": "Адрес этого места",
          "location": { "lat": 0.000000, "lon": 0.000000 },
          "category": "cafe" (категория из запроса)
        },
        ...
        {
          "order": N,
          "type": "end",
          "name": "Название места или 'Финиш'",
          "address": "Точный адрес",
          "location": { "lat": 0.000000, "lon": 0.000000 },
          "category": null
        }
      ]
    },
    ... (еще 2 варианта)
  ]
}

ПРАВИЛА ГЕНЕРАЦИИ:
1. Если пользователь дает неточный адрес (например, только улицу), выбери наиболее вероятные координаты или центр улицы.
2. Для категорий ("аптека", "магазин") подбирай реально существующие или правдоподобные места в радиусе от предыдущей точки.
3. Координаты (lat, lon) обязательны для каждой точки, чтобы фронтенд мог поставить маркеры.
4. Поле title должно коротко объяснять, чем этот маршрут отличается (например, "Через центр", "Минимальная ходьба")."""

# SYSTEM_PROMPT = """You are a path planning assistant that helps users find optimal routes through multiple locations.

# Your job is to:
# 1. Parse the user's natural language request to identify:
#    - Starting point (origin)
#    - Ending point (destination)
#    - Intermediate stops (places to visit along the way)

# 2. For each location:
#    - If it's a specific address, use geocode_address to get coordinates
#    - If it's a category (like "bank", "cafe", "pharmacy"), use find_optimal_place to find the best option that minimizes detour

# 3. Once all waypoints are determined, use calculate_route to get the full route

# 4. Return the final result as a JSON object with this structure:
# {
#   "waypoints": [
#     {
#       "name": "...",
#       "address": "...",
#       "coordinates": [lon, lat],
#       "type": "origin|destination|waypoint",
#       "category": "bank|cafe|etc (only for category stops)",
#       "alternatives": [...] (only for category stops)
#     }
#   ],
#   "route": {
#     "geometry": [[lon, lat], ...],
#     "segments": [{"from": 0, "to": 1, "distance": ..., "duration": ...}]
#   },
#   "total_distance": ...,
#   "total_duration": ...,
#   "mode": "driving|walking",
#   "optimize": "distance|time"
# }

# Important guidelines:
# - Always process stops in the order mentioned by the user
# - For category stops (bank, cafe, etc.), use find_optimal_place to get the best location
# - Include alternatives for category stops so users can choose different options
# - Use the mode and optimize parameters provided by the user
# - If geocoding fails, inform the user which address couldn't be found
# - Return ONLY the JSON response, no additional text
# """

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
            "description": "Calculate a route through multiple points",
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
            result = await places_client.geocode(
                arguments["address"],
                arguments.get("city"),
                arguments.get("region_id")
            )
            logger.info(f"geocode_address result: {result}")
            return result

        elif name == "search_nearby_places":
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
                include_pedestrian_instructions=False,
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
    mode_map = {
        "driving": "на машине",
        "walking": "пешком",
        "public_transport": "на общественном транспорте (автобус, метро, трамвай)"
    }
    mode_ru = mode_map.get(mode, "на машине")

    # Build mode-specific instructions
    if mode == "public_transport":
        mode_instructions = """Способ передвижения: на общественном транспорте

ВАЖНО: Используй инструмент calculate_public_transport_route для построения маршрута.
Включи в ответ: transport_chain (цепочку транспорта), transfer_count (пересадки), walking_duration_minutes (время ходьбы)."""
    else:
        mode_instructions = f"""Способ передвижения: {mode_ru}

Проанализируй запрос и сам выбери оптимизацию (time или distance) на основе контекста."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Запрос пользователя: {query}

{mode_instructions}

Используй инструменты для поиска мест и построения маршрутов. Верни результат в формате JSON."""}
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
        logger.info(f"LLM response - content: {message.content[:200] if message.content else 'None'}...")
        logger.info(f"LLM response - tool_calls: {message.tool_calls}")

        # Add assistant message to history
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls if message.tool_calls else None
        })

        # If no tool calls, we have the final response
        if not message.tool_calls:
            response_text = message.content or ""
            logger.info(f"Final response: {response_text[:500]}...")
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
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
        return {
            "error": f"Failed to parse agent response: {str(e)}",
            "raw_response": response_text,
        }
