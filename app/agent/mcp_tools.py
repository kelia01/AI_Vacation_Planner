import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain.tools import tool
from app.agent.mcp_client import call_mcp_tool

_executor = ThreadPoolExecutor(max_workers=4)

_llmobs_enabled = bool(os.getenv("DD_API_KEY"))
if _llmobs_enabled:
    from ddtrace.llmobs import LLMObs


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _run_in_thread(coro):
    future = _executor.submit(_run, coro)
    return future.result()


def _tool_call(tool_name: str, arguments: dict) -> str:
    result = _run_in_thread(call_mcp_tool(tool_name, arguments))
    if _llmobs_enabled:
        LLMObs.annotate(span=None, input_data=str(arguments), output_data=str(result))
    return result


@tool
def get_weather_mcp(destination: str) -> str:
    """Get 7-day weather forecast for a destination."""
    if _llmobs_enabled:
        with LLMObs.tool(name="get_weather_mcp"):
            return _tool_call("get_weather", {"destination": destination})
    return _run_in_thread(call_mcp_tool("get_weather", {"destination": destination}))


@tool
def find_restaurants_mcp(destination: str) -> str:
    """Find restaurants near a destination."""
    if _llmobs_enabled:
        with LLMObs.tool(name="find_restaurants_mcp"):
            return _tool_call("find_places", {"destination": destination, "category": "restaurant"})
    return _run_in_thread(call_mcp_tool("find_places", {"destination": destination, "category": "restaurant"}))


@tool
def find_hotels_mcp(destination: str) -> str:
    """Find hotels near a destination."""
    if _llmobs_enabled:
        with LLMObs.tool(name="find_hotels_mcp"):
            return _tool_call("find_places", {"destination": destination, "category": "hotel"})
    return _run_in_thread(call_mcp_tool("find_places", {"destination": destination, "category": "hotel"}))


@tool
def find_museums_mcp(destination: str) -> str:
    """Find museums near a destination."""
    if _llmobs_enabled:
        with LLMObs.tool(name="find_museums_mcp"):
            return _tool_call("find_places", {"destination": destination, "category": "museum"})
    return _run_in_thread(call_mcp_tool("find_places", {"destination": destination, "category": "museum"}))


@tool
def check_calendar_mcp(start_date: str, end_date: str) -> str:
    """Check vacation calendar for conflicts between start_date and end_date (YYYY-MM-DD)."""
    if _llmobs_enabled:
        with LLMObs.tool(name="check_calendar_mcp"):
            return _tool_call("check_calendar", {"start_date": start_date, "end_date": end_date})
    return _run_in_thread(call_mcp_tool("check_calendar", {"start_date": start_date, "end_date": end_date}))


@tool
def add_to_calendar_mcp(date: str, activity: str, time: str = "10:00") -> str:
    """Add an activity to the vacation calendar."""
    if _llmobs_enabled:
        with LLMObs.tool(name="add_to_calendar_mcp"):
            return _tool_call("add_to_calendar", {"date": date, "activity": activity, "time": time})
    return _run_in_thread(call_mcp_tool("add_to_calendar", {"date": date, "activity": activity, "time": time}))


@tool
def search_travel_knowledge_mcp(query: str, destination: str = "") -> str:
    """Search the travel knowledge base for tips, FAQs, and destination info."""
    if _llmobs_enabled:
        with LLMObs.tool(name="search_travel_knowledge_mcp"):
            return _tool_call("search_travel_knowledge", {"query": query, "destination": destination})
    return _run_in_thread(call_mcp_tool("search_travel_knowledge", {"query": query, "destination": destination}))


MCP_TOOLS = [
    get_weather_mcp,
    find_restaurants_mcp,
    find_hotels_mcp,
    find_museums_mcp,
    check_calendar_mcp,
    add_to_calendar_mcp,
    search_travel_knowledge_mcp,
]
