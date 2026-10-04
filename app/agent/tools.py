from langchain.tools import tool
from app.services.weather_service import get_weather
from app.services.rag_service import rag_service


@tool
def weather_tool(destination: str) -> dict:
    """Get current weather for a destination."""
    result = get_weather(destination)
    if "error" in result:
        return {"status": "error", "message": result["error"]}
    return {"status": "success", "data": result}


@tool
def search_travel_knowledge_tool(query: str, destination: str = "") -> dict:
    """Search the travel knowledge base for tips, FAQs, and destination info."""
    results = rag_service.search(query, destination=destination or None)
    return {"status": "success", "data": results}


def execute_tool(name: str, params: dict) -> dict:
    """Dispatch helper used by tests."""
    if name == "get_weather":
        if "destination" not in params:
            return {"status": "error", "message": "Missing destination"}
        return weather_tool.invoke(params)
    if name == "search_travel_knowledge":
        return search_travel_knowledge_tool.invoke(params)
    return {"status": "error", "message": f"Unknown tool: {name}"}


AGENT_TOOLS = [weather_tool, search_travel_knowledge_tool]
