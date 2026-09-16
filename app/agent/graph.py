"""
LangGraph workflow for the vacation planning agent.

Orchestrates tool usage, itinerary generation, and approval workflow.
"""

import os
import json
import sqlite3
from typing import Any
from dotenv import load_dotenv
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from anthropic import Anthropic

from app.agent.state import AgentState
from app.agent.tools import TOOLS, execute_tool
from app.agent.models import StructuredItinerary
from app import crud
from app.services.rag_service import rag_service


load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_TOOL_ITERATIONS = 5
MODEL = "claude-haiku-4-5"
CHECKPOINT_DIR = str(Path(__file__).parent.parent.parent / "checkpoints")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Create checkpoint directory if needed
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


# ============================================================================
# NODE: TRIP RETRIEVAL
# ============================================================================

def retrieve_trip_node(state: AgentState, db) -> AgentState:
    """
    Retrieve trip details from database.
    
    Verifies authorization and loads trip context.
    """
    if not state.trip_id or not state.user_id:
        state.error = "Missing trip_id or user_id"
        return state
    
    try:
        trip = crud.get_trip_by_id(db, state.trip_id, state.user_id)
        if not trip:
            state.error = "Trip not found or unauthorized"
            return state
        
        # Cache trip details in state
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


# ============================================================================
# NODE: AGENT DECISION & TOOL CALLING
# ============================================================================

def agent_node(state: AgentState) -> AgentState:
    """
    Main agent node using Claude to decide which tools are needed
    and generate the itinerary.
    
    This node handles tool calling in a loop until the agent
    produces final structured output or hits the iteration limit.
    """
    
    if state.error:
        return state
    
    if not state.trip:
        state.error = "Trip not loaded"
        return state
    
    # Initialize messages if empty
    if not state.messages:
        state.messages = []
    
    # Build system prompt
    system_prompt = f"""You are an expert travel planner AI assistant.

You have access to tools to help plan itineraries:
{json.dumps([{"name": name, "description": tool["description"]} for name, tool in TOOLS.items()], indent=2)}

TRIP DETAILS:
- Destination: {state.trip['destination']}
- Duration: {state.trip['days']} days
- Budget: ${state.trip['budget']}
- Travel Style: {state.trip['trip_style']}

Your task:
1. Gather necessary information using tools (weather, travel knowledge, places, costs)
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
- Use weather data to inform activity planning
- Stay within the budget constraint
- Respect travel style (budget/moderate/luxury)
- Each day must have at least 3 activities
- Return complete JSON with no markdown formatting
"""
    
    # Use existing messages or start with user request
    if not state.messages:
        state.messages.append({
            "role": "user",
            "content": state.user_feedback or f"Please plan my {state.trip['days']}-day trip to {state.trip['destination']} with a budget of ${state.trip['budget']}. Trip style: {state.trip['trip_style']}"
        })
    
    # Call Claude with tools
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        tools=[
            {
                "name": tool_name,
                "description": tool_def["description"],
                "input_schema": tool_def["parameters"]
            }
            for tool_name, tool_def in TOOLS.items()
        ],
        messages=state.messages
    )
    
    # Process response
    state.messages.append({
        "role": "assistant",
        "content": response.content
    })
    
    # Check for tool use
    tool_use_blocks = [block for block in response.content if hasattr(block, 'type') and block.type == "tool_use"]
    
    if tool_use_blocks and state.tool_iteration_count < MAX_TOOL_ITERATIONS:
        # Execute tools and continue loop
        state.tool_iteration_count += 1
        
        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input
            
            result = execute_tool(tool_name, tool_input)
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": json.dumps(result)
            })
        
        # Add tool results to messages
        state.messages.append({
            "role": "user",
            "content": tool_results
        })
        
        # Continue agent loop (recursive call via graph)
        return state
    
    elif state.tool_iteration_count >= MAX_TOOL_ITERATIONS:
        state.error = f"Maximum tool iterations ({MAX_TOOL_ITERATIONS}) reached"
        return state
    
    # No more tools - extract final response
    text_blocks = [block for block in response.content if hasattr(block, 'type') and block.type == "text"]
    
    if text_blocks:
        final_text = "".join(block.text for block in text_blocks)
        
        # Try to extract JSON
        try:
            # Clean markdown if present
            cleaned = final_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            itinerary_json = json.loads(cleaned.strip())
            
            # Validate against schema
            itinerary = StructuredItinerary(**itinerary_json)
            state.itinerary_draft = itinerary.model_dump()
            state.approval_state = "draft_ready"
            
        except json.JSONDecodeError as e:
            state.error = f"Failed to parse itinerary JSON: {str(e)}"
        except Exception as e:
            state.error = f"Itinerary validation failed: {str(e)}"
    else:
        state.error = "Agent did not return valid output"
    
    return state


# ============================================================================
# CONDITIONAL ROUTING
# ============================================================================

def should_continue_agent(state: AgentState) -> str:
    """
    Determine whether to continue the agent loop or finish.
    """
    if state.error:
        return "error"
    
    if state.approval_state == "draft_ready":
        return "validate"
    
    if state.approval_state == "revising":
        return "agent"
    
    # Keep calling agent if still in planning
    if state.approval_state == "planning" and state.tool_iteration_count < MAX_TOOL_ITERATIONS:
        return "agent"
    
    return "end"


def validate_itinerary_node(state: AgentState) -> AgentState:
    """
    Validate the generated itinerary against schema and business rules.
    """
    if state.error or not state.itinerary_draft:
        return state
    
    try:
        # Already validated in agent_node, but double-check
        itinerary = StructuredItinerary(**state.itinerary_draft)
        
        # Business rule checks
        if len(itinerary.days) != state.trip['days']:
            state.error = f"Itinerary has {len(itinerary.days)} days, trip is {state.trip['days']} days"
            return state
        
        total_cost = itinerary.metadata.total_estimated_cost or 0
        if total_cost > state.trip['budget'] * 1.1:  # Allow 10% over
            state.warning = f"Estimated cost ${total_cost:.2f} exceeds budget ${state.trip['budget']}"
        
        state.approval_state = "draft_ready"
        
    except Exception as e:
        state.error = f"Validation failed: {str(e)}"
    
    return state


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_agent_graph():
    """
    Construct the LangGraph workflow.
    
    Returns:
        Compiled graph that can be invoked with state.
    """
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("retrieve_trip", lambda s: s)  # Placeholder - handled in invoke
    graph.add_node("agent", agent_node)
    graph.add_node("validate", validate_itinerary_node)
    
    # Set entry point
    graph.set_entry_point("agent")
    
    # Add edges
    graph.add_conditional_edges(
        "agent",
        should_continue_agent,
        {
            "agent": "agent",
            "validate": "validate",
            "error": END,
            "end": END
        }
    )
    
    graph.add_edge("validate", END)

    conn = sqlite3.connect(
        CHECKPOINT_DIR,
        check_same_thread=False
    )
    
    # Compile with checkpointer for state persistence
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    return compiled_graph


# Global graph instance
agent_graph = None

def get_agent_graph():
    """Get or create the compiled agent graph."""
    global agent_graph
    if agent_graph is None:
        agent_graph = build_agent_graph()
    return agent_graph


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
    Run the vacation planner agent for a given trip and request.
    
    Args:
        trip_id: Database trip ID
        user_id: Authenticated user ID
        message: User's request message
        thread_id: Conversation thread ID for checkpointing
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
    
    # Run the agent graph
    graph = get_agent_graph()
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Invoke graph - it will handle the tool loop internally
    final_state = graph.invoke(state, config=config)
    
    return final_state
    