"""
LangGraph workflow for the vacation planning agent.

Uses LangChain model abstraction (init_chat_model) for provider-agnostic LLM usage.
Properly implements tool calling and ToolNode pattern.
"""

import os
import json
from typing import Literal
from pathlib import Path

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel

from app.agent.state import AgentState
from app.agent.models import StructuredItinerary
from app.agent.tools import AGENT_TOOLS
from app import crud
import sqlite3


# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_ITERATIONS = 5

# Initialize LLM via LangChain abstraction (provider agnostic)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google_genai")

if LLM_PROVIDER == "google_genai":
    llm = init_chat_model(
        "gemini-3.6-flash",
        model_provider="google_genai"
    )
elif LLM_PROVIDER == "anthropic":
    llm = init_chat_model(
        "claude-haiku-4-5",
        model_provider="anthropic"
    )
else:
    raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")

# Checkpointing (fixed SQLite path)
CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)
CHECKPOINT_FILE = CHECKPOINT_DIR / "agent.db"

conn = sqlite3.connect(str(CHECKPOINT_FILE), check_same_thread=False)
checkpointer = SqliteSaver(conn)


# ============================================================================
# NODES
# ============================================================================

def retrieve_trip_node(state: AgentState, db) -> AgentState:
    """
    Retrieve trip details from database with authorization.
    """
    if not state.trip_id or not state.user_id:
        state.error = "Missing trip_id or user_id"
        return state
    
    try:
        trip = crud.get_trip_by_id(db, state.trip_id, state.user_id)
        if not trip:
            state.error = "Trip not found or unauthorized"
            return state
        
        state.trip = {
            "id": trip.id,
            "destination": trip.destination,
            "days": trip.days,
            "budget": trip.budget,
            "trip_style": trip.trip_style,
            "created_at": str(trip.created_at) if trip.created_at else None
        }
        
    except Exception as e:
        state.error = f"Database error: {str(e)}"
    
    return state


def agent_node(state: AgentState) -> Command:
    """
    Main agent node using LangChain model with bound tools.
    
    Returns a Command to route to ToolNode or proceed to validation.
    """
    
    if state.error:
        return Command(goto="end", update={"approval_state": "error"})
    
    if not state.trip:
        state.error = "Trip not loaded"
        return Command(goto="end", update={"approval_state": "error"})
    
    # Build system prompt
    system_prompt = f"""You are an expert travel planner AI assistant.

You have access to tools to help plan itineraries:
- get_weather_tool: Get weather forecast
- search_travel_knowledge_tool: Query travel knowledge base
- search_places_tool: Find attractions
- estimate_costs_tool: Estimate trip costs

TRIP DETAILS:
- Destination: {state.trip['destination']}
- Duration: {state.trip['days']} days
- Budget: ${state.trip['budget']}
- Travel Style: {state.trip['trip_style']}

Your task:
1. Use tools to gather information (weather, attractions, costs, travel tips)
2. Generate a detailed, structured itinerary
3. Return ONLY valid JSON matching this schema:

{{
  "metadata": {{
    "destination": "string",
    "duration_days": number,
    "total_estimated_cost": number,
    "travel_style": "string",
    "weather_summary": "string"
  }},
  "days": [
    {{
      "day_number": number,
      "date": "YYYY-MM-DD",
      "theme": "string",
      "activities": [
        {{
          "name": "string",
          "time": "HH:MM - HH:MM",
          "description": "string",
          "estimated_cost": number
        }}
      ],
      "estimated_daily_cost": number
    }}
  ],
  "reasoning": "string",
  "recommendations": ["string"]
}}

Rules:
- Use weather to inform activity planning
- Stay within budget
- Respect travel style (budget/moderate/luxury)
- Each day must have at least 1 activity
- Return complete JSON with no markdown formatting
"""
    
    # Use previous messages or start fresh
    if not state.messages:
        state.messages.append(
            HumanMessage(content=state.user_feedback or f"Plan my {state.trip['days']}-day trip to {state.trip['destination']} with a budget of ${state.trip['budget']}. Trip style: {state.trip['trip_style']}")
        )
    
    # Bind tools to model and invoke
    llm_with_tools = llm.bind_tools(AGENT_TOOLS)
    
    response = llm_with_tools.invoke(
        [SystemMessage(content=system_prompt)] + state.messages
    )
    
    # Add assistant response to messages
    state.messages.append(response)
    
    # Check if model called tools
    if response.tool_calls:
        # Route to tool execution
        return Command(goto="tools")
    
    # No tools called - model returned final answer
    # Extract JSON from response
    try:
        # Try to extract JSON from text
        text = response.content
        if isinstance(text, str):
            # Remove markdown formatting if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            itinerary_json = json.loads(text.strip())
            
            # Validate against schema
            itinerary = StructuredItinerary(**itinerary_json)
            state.itinerary_draft = itinerary.model_dump()
            state.approval_state = "draft_ready"
        else:
            state.error = "Model did not return valid JSON"
            return Command(goto="end")
    
    except json.JSONDecodeError as e:
        state.error = f"Failed to parse itinerary JSON: {str(e)}"
        return Command(goto="end")
    except Exception as e:
        state.error = f"Itinerary validation failed: {str(e)}"
        return Command(goto="end")
    
    return Command(goto="validate")


def process_tool_calls(state: AgentState) -> Command:
    """
    Process tool calls from the model.
    
    LangGraph's ToolNode handles the actual execution.
    This node routes after tool execution.
    """
    
    # Check iteration limit
    # Count tool_use blocks in messages
    tool_call_count = sum(
        1 for msg in state.messages 
        if hasattr(msg, 'tool_calls') and msg.tool_calls
    )
    
    if tool_call_count >= MAX_ITERATIONS:
        state.error = f"Maximum tool iterations ({MAX_ITERATIONS}) reached"
        return Command(goto="end")
    
    # Continue to agent to process tool results
    return Command(goto="agent")


def validate_itinerary_node(state: AgentState) -> Command:
    """
    Validate the generated itinerary.
    """
    
    if state.error or not state.itinerary_draft:
        return Command(goto="end")
    
    try:
        # Already validated in agent_node, but double-check
        itinerary = StructuredItinerary(**state.itinerary_draft)
        
        # Business rule checks
        if len(itinerary.days) != state.trip['days']:
            state.error = f"Itinerary has {len(itinerary.days)} days, trip is {state.trip['days']} days"
            return Command(goto="end")
        
        total_cost = itinerary.metadata.total_estimated_cost or 0
        if total_cost > state.trip['budget'] * 1.1:  # Allow 10% over
            print(f"Warning: Estimated cost ${total_cost:.2f} exceeds budget ${state.trip['budget']}")
        
        state.approval_state = "draft_ready"
        return Command(goto="end")
    
    except Exception as e:
        state.error = f"Validation failed: {str(e)}"
        return Command(goto="end")


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_agent_graph():
    """
    Construct the LangGraph workflow.
    """
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(AGENT_TOOLS))  # Built-in LangGraph tool execution
    graph.add_node("validate", validate_itinerary_node)
    
    # Set entry point
    graph.set_entry_point("agent")
    
    # Add edges
    graph.add_edge("tools", "agent")  # After tools, back to agent
    graph.add_edge("validate", END)
    
    # Compile with checkpointer
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    return compiled_graph


agent_graph = build_agent_graph()


# ============================================================================
# AGENT INVOCATION
# ============================================================================

def run_agent(
    trip_id: int,
    user_id: int,
    message: str,
    thread_id: str,
    db,
    user_feedback: str = None
) -> AgentState:
    """
    Run the vacation planner agent for a given trip.
    
    Args:
        trip_id: Database trip ID
        user_id: Authenticated user ID
        message: User's request message
        thread_id: Conversation thread ID
        db: Database session
        user_feedback: Optional revision feedback
        
    Returns:
        Final agent state with itinerary draft or error
    """
    
    # Initialize state
    state = AgentState(
        trip_id=trip_id,
        user_id=user_id,
        user_feedback=user_feedback or message
    )
    
    # Retrieve trip (authorization + load)
    state = retrieve_trip_node(state, db)
    
    if state.error:
        return state
    
    # Run the graph
    config = {"configurable": {"thread_id": thread_id}}
    
    final_state = agent_graph.invoke(state, config=config)
    
    return final_state