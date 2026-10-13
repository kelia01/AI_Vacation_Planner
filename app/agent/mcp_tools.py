from langchain.tools import tool
from app.agent.mcp_client import call_mcp_tool
import asyncio

def _run(coro):
    return asyncio.run(coro)

@tool
def get_weather_mcp(destination: str) -> str:
    """Get 7-day weather forecast for a destination."""
    return _run(call_mcp_tool("get_weather", {"destination": destination}))


@tool
def find_restaurants_mcp(destination: str) -> str:
    """Find restaurants near a destination."""
    return _run(call_mcp_tool("find_places", {"destination": destination, "category": "restaurant"}))


@tool
def find_hotels_mcp(destination: str) -> str:
    """Find hotels near a destination."""
    return _run(call_mcp_tool("find_places", {"destination": destination, "category": "hotel"}))


@tool
def find_museums_mcp(destination: str) -> str:
    """Find museums near a destination."""
    return _run(call_mcp_tool("find_places", {"destination": destination, "category": "museum"}))


@tool
def check_calendar_mcp(start_date: str, end_date: str) -> str:
    """Check vacation calendar for conflicts between start_date and end_date (YYYY-MM-DD)."""
    return  _run(call_mcp_tool("check_calendar", {"start_date": start_date, "end_date": end_date}))


@tool
def add_to_calendar_mcp(date: str, activity: str, time: str = "10:00") -> str:
    """Add an activity to the vacation calendar."""
    return _run(call_mcp_tool("add_to_calendar", {"date": date, "activity": activity, "time": time}))

@tool
def search_travel_knowledge_mcp(query: str, destination: str = "") -> str:
    """Search the travel knowledge base for tips, FAQs, and destination info."""
    return _run(call_mcp_tool(
        "search_travel_knowledge", 
        {"query": query, "destination": destination}
    ))

MCP_TOOLS = [
    get_weather_mcp,
    find_restaurants_mcp,
    find_hotels_mcp,
    find_museums_mcp,
    check_calendar_mcp,
    add_to_calendar_mcp,
    search_travel_knowledge_mcp
]
