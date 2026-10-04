import asyncio
import json
import logging
import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities

logging.basicConfig(level=logging.INFO)

server = Server("vacation-planner")

WEATHER_API = "https://api.open-meteo.com/v1/forecast"
GEOCODE_API = "https://geocoding-api.open-meteo.com/v1/search"
OVERPASS_API = "https://overpass-api.de/api/interpreter"

# In-process calendar (per server lifetime)
CALENDAR_DATA: dict = {"bookings": []}


def geocode(location: str) -> tuple[float | None, float | None]:
    try:
        r = requests.get(
            GEOCODE_API,
            params={"name": location, "count": 1},
            timeout=5
        )
        data = r.json()
        if data.get("results"):
            place = data["results"][0]
            return float(place["latitude"]), float(place["longitude"])
    except Exception as e:
        logging.error(f"Geocoding error: {e}")
    return None, None


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_weather",
            description="Get 7-day weather forecast for a destination",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City name"}
                },
                "required": ["destination"]
            }
        ),
        Tool(
            name="find_places",
            description="Find restaurants, hotels, museums, or parks near a destination using OpenStreetMap",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["restaurant", "hotel", "museum", "park"]
                    }
                },
                "required": ["destination", "category"]
            }
        ),
        Tool(
            name="check_calendar",
            description="Check vacation calendar for conflicts on a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["start_date", "end_date"]
            }
        ),
        Tool(
            name="add_to_calendar",
            description="Add an activity to the vacation calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "activity": {"type": "string"},
                    "time": {"type": "string", "description": "HH:MM", "default": "10:00"}
                },
                "required": ["date", "activity"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_weather":
        destination = arguments["destination"]
        lat, lon = geocode(destination)
        if lat is None:
            return [TextContent(type="text", text=f"Could not geocode: {destination}")]
        try:
            r = requests.get(
                WEATHER_API,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                    "timezone": "auto"
                },
                timeout=5
            )
            daily = r.json()["daily"]
            lines = [f"Weather forecast for {destination}:"]
            for i in range(min(7, len(daily["time"]))):
                lines.append(
                    f"  {daily['time'][i]}: {daily['temperature_2m_max'][i]}°C / "
                    f"{daily['temperature_2m_min'][i]}°C, "
                    f"rain {daily['precipitation_sum'][i]}mm"
                )
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [TextContent(type="text", text=f"Weather API error: {e}")]

    elif name == "find_places":
        destination = arguments["destination"]
        category = arguments["category"]
        lat, lon = geocode(destination)
        if lat is None:
            return [TextContent(type="text", text=f"Could not geocode: {destination}")]

        osm_tag_map = {
            "restaurant": 'amenity"="restaurant',
            "hotel": 'tourism"="hotel',
            "museum": 'tourism"="museum',
            "park": 'leisure"="park',
        }
        tag = osm_tag_map.get(category, f'amenity"="{category}')
        query = f"""
[out:json][timeout:10];
node["{tag}](around:5000,{lat},{lon});
out 5;
"""
        try:
            r = requests.post(OVERPASS_API, data={"data": query}, timeout=12)
            elements = r.json().get("elements", [])
            if not elements:
                return [TextContent(type="text", text=f"No {category}s found near {destination}.")]
            lines = [f"Top {category}s near {destination}:"]
            for el in elements[:5]:
                name = el.get("tags", {}).get("name", "Unnamed")
                lines.append(f"  - {name}")
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [TextContent(type="text", text=f"Places search error: {e}")]

    elif name == "check_calendar":
        start = arguments["start_date"]
        end = arguments["end_date"]
        conflicts = [
            b for b in CALENDAR_DATA["bookings"]
            if start <= b["date"] <= end
        ]
        if not conflicts:
            return [TextContent(type="text", text=f"No conflicts from {start} to {end}.")]
        lines = [f"Conflicts from {start} to {end}:"]
        for b in conflicts:
            lines.append(f"  {b['date']} {b['time']}: {b['activity']}")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "add_to_calendar":
        entry = {
            "date": arguments["date"],
            "activity": arguments["activity"],
            "time": arguments.get("time", "10:00")
        }
        CALENDAR_DATA["bookings"].append(entry)
        return [TextContent(
            type="text",
            text=f"Added: {entry['date']} at {entry['time']} — {entry['activity']}"
        )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="vacation-planner",
                server_version="0.1.0",
                capabilities=ServerCapabilities()
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
