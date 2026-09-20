"""
Tool implementations for the vacation planning agent.

Tools are defined using LangChain @tool decorator for proper integration.
"""

import json
from typing import Any, Dict
from langchain.tools import tool

from app.services.rag_service import rag_service
from app.services.weather_service import get_weather


# ============================================================================
# WEATHER TOOL
# ============================================================================

@tool
def get_weather_tool(destination: str) -> Dict[str, Any]:
    """
    Get current and forecast weather for a destination.
    
    Args:
        destination: City or country name
        
    Returns:
        Weather data with temperature, conditions, etc.
    """
    try:
        result = get_weather(destination)
        if "error" in result:
            return {"status": "error", "message": result.get("error")}
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# RAG/TRAVEL KNOWLEDGE TOOL
# ============================================================================

@tool
def search_travel_knowledge_tool(
    query: str, 
    destination: str = "", 
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Search the travel knowledge base for relevant information.
    
    Uses RAG system to retrieve travel tips, attractions, and guidance.
    
    Args:
        query: Search query
        destination: Optional destination filter
        top_k: Number of results to return
        
    Returns:
        Retrieved knowledge documents and context.
    """
    try:
        results = rag_service.search(
            query=query,
            destination=destination if destination else None,
            top_k=top_k
        )
        
        if not results:
            return {
                "status": "success", 
                "data": [], 
                "message": "No matching travel knowledge found"
            }
        
        formatted_results = [
            {
                "title": r.get("title", "Travel Information"),
                "content": r.get("content", ""),
                "destination": r.get("destination")
            }
            for r in results
        ]
        
        return {"status": "success", "data": formatted_results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# PLACES/ATTRACTIONS TOOL
# ============================================================================

@tool
def search_places_tool(
    destination: str, 
    activity_type: str = "", 
    radius_km: int = 20
) -> Dict[str, Any]:
    """
    Search for places and attractions in a destination.
    
    This is a simplified implementation. In production, integrate with:
    - Google Places API
    - OpenStreetMap
    - Local tourism APIs
    
    Args:
        destination: City or country
        activity_type: Filter by type (museums, restaurants, parks, etc.)
        radius_km: Search radius
        
    Returns:
        List of places with location data.
    """
    try:
        return {
            "status": "success",
            "data": [
                {
                    "name": f"Popular {activity_type or 'attraction'} in {destination}",
                    "type": activity_type or "landmark",
                    "location": destination,
                    "rating": 4.5,
                    "note": "Google Places API integration needed for production"
                }
            ],
            "message": "Places search - API integration required for full functionality"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# COST ESTIMATION TOOL
# ============================================================================

@tool
def estimate_costs_tool(
    destination: str, 
    days: int, 
    trip_style: str = "moderate"
) -> Dict[str, Any]:
    """
    Estimate travel costs for a destination.
    
    This is a simplified implementation. In production, integrate with:
    - Booking.com / Airbnb APIs for accommodation
    - Skyscanner / Amadeus for flights
    - Restaurant/activity pricing databases
    
    Args:
        destination: City or country
        days: Number of days
        trip_style: Budget level (budget, moderate, luxury)
        
    Returns:
        Cost breakdown by category.
    """
    cost_ranges = {
        "budget": {"accommodation": 40, "food": 20, "activities": 15, "transport": 10},
        "moderate": {"accommodation": 100, "food": 50, "activities": 50, "transport": 30},
        "luxury": {"accommodation": 250, "food": 150, "activities": 100, "transport": 100}
    }
    
    try:
        daily_costs = cost_ranges.get(trip_style.lower(), cost_ranges["moderate"])
        
        breakdown = {
            "accommodation": {
                "per_night": daily_costs["accommodation"],
                "total": daily_costs["accommodation"] * days
            },
            "food": {
                "per_day": daily_costs["food"],
                "total": daily_costs["food"] * days
            },
            "activities": {
                "per_day": daily_costs["activities"],
                "total": daily_costs["activities"] * days
            },
            "transport": {
                "local": daily_costs["transport"] * days,
                "flights": "Check external API for actual flight prices"
            }
        }
        
        total = (breakdown["accommodation"]["total"] + 
                breakdown["food"]["total"] + 
                breakdown["activities"]["total"] + 
                breakdown["transport"]["local"])
        
        return {
            "status": "success",
            "data": {
                "destination": destination,
                "days": days,
                "style": trip_style,
                "breakdown": breakdown,
                "estimated_total_usd": total,
                "note": "Estimates are approximate. Verify with actual booking APIs."
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# TOOL LIST FOR LANGGRAPH
# ============================================================================

AGENT_TOOLS = [
    get_weather_tool,
    search_travel_knowledge_tool,
    search_places_tool,
    estimate_costs_tool
]