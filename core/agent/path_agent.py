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

# Configure LiteLLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")


SYSTEM_PROMPT = """Ты — AI-агент, специализирующийся на гео-навигации и логистике. Твоя задача — анализировать запрос пользователя, извлекать точки маршрута (адреса и категории мест) и составлять оптимальные маршруты.

ТВОИ ЦЕЛИ:
1. Проанализировать текст пользователя. Найти точку отправления (Start).
2. Найти промежуточные точки (Waypoints). Если указана категория (например, "банк", "кафе"), ты должен подобрать конкретные заведения, используя доступные тебе инструменты поиска (или знания о гео-контексте).
3. Найти конечную точку (End). Если пользователь говорит "домой" или "обратно", конечная точка совпадает с начальной. Если конечная точка не указана, предложи логическое завершение или оставь маршрут открытым.
4. Сгенерировать ровно 3 варианта маршрута. Варианты должны отличаться выбором конкретных заведений (например, "Ближайший банк А" vs "Банк Б чуть дальше, но с лучшим рейтингом") или порядком посещения, чтобы предложить пользователю выбор.

ВЫБОР ОПТИМИЗАЦИИ МАРШРУТА:
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
    "optimization_choice": "time или distance — что ты выбрал и почему (кратко)"
  },
  "routes": [
    {
      "route_id": 1,
      "title": "Название варианта (например: 'Самый быстрый' или 'Через Halyk Bank')",
      "total_distance_meters": Число (примерная оценка),
      "total_duration_minutes": Число (примерная оценка),
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
          "name": "Название конкретного найденного места (например, Starbucks)",
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
            "description": "Convert an address string to geographic coordinates",
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
            "description": "Search for places by category or name near a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'bank', 'cafe', 'pharmacy')"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the search center point"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the search center point"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters (default 5000)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 5)"
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
    }
]


async def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool and return the result."""
    logger.info(f"Executing tool: {name} with args: {arguments}")
    places_client = get_places_client()
    routing_client = get_routing_client()

    try:
        if name == "geocode_address":
            result = await places_client.geocode(
                arguments["address"],
                arguments.get("city")
            )
            logger.info(f"geocode_address result: {result}")
            return result

        elif name == "search_nearby_places":
            result = await places_client.search_places(
                arguments["query"],
                (arguments["longitude"], arguments["latitude"]),
                arguments.get("radius", 5000),
                arguments.get("limit", 5)
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

        else:
            result = {"error": f"Unknown tool: {name}"}
            logger.info(f"Tool {name} result: {result}")
            return result

    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return {"error": str(e)}


async def plan_route(
    query: str,
    mode: Literal["driving", "walking"] = "driving",
) -> dict:
    """
    Plan a route based on natural language query.

    Args:
        query: Natural language route request
        mode: Transportation mode

    Returns:
        Route response dictionary
    """
    mode_ru = "пешком" if mode == "walking" else "на машине"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Запрос пользователя: {query}

Способ передвижения: {mode_ru}

Проанализируй запрос и сам выбери оптимизацию (time или distance) на основе контекста. Используй инструменты для поиска мест и построения маршрутов. Верни результат в формате JSON."""}
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
