"""
LangGraph workflow for the vacation planning agent.
"""

import json
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

from app.agent.state import AgentState
from app.agent.itinerary_models import StructuredItinerary
from app.agent.mcp_tools import MCP_TOOLS
from app.services import trip_service
from app.services.rag_service import rag_service


MAX_ITERATIONS = 5

llm = init_chat_model("claude-haiku-4-5", model_provider="anthropic")

CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)
CHECKPOINT_FILE = CHECKPOINT_DIR / "agent.db"

async def _get_checkpointer():
    return AsyncSqliteSaver(await aiosqlite.connect(str(CHECKPOINT_FILE)))

# ============================================================================
# NODES
# ============================================================================

def retrieve_trip_node(state: AgentState, db) -> AgentState:
    if not state.get("trip_id") or not state.get("user_id"):
        return {**state, "error": "Missing trip_id or user_id"}
    try:
        trip = trip_service.get_trip_by_id(db, state["trip_id"], state["user_id"])
        if not trip:
            return {**state, "error": "Trip not found or unauthorized"}
        return {
            **state,
            "trip": {
                "id": trip.id,
                "destination": trip.destination,
                "days": trip.days,
                "budget": trip.budget,
                "trip_style": trip.trip_style,
                "created_at": str(trip.created_at) if trip.created_at else None,
            }
        }
    except Exception as e:
        return {**state, "error": f"Database error: {str(e)}"}


def agent_node(state: AgentState) -> Command:
    if state.get("error"):
        return Command(goto=END, update={"approval_state": "error"})

    if not state.get("trip"):
        return Command(goto=END, update={"error": "Trip not loaded", "approval_state": "error"})

    trip = state["trip"]
    
    rag_context = rag_service.get_context(
        query=f"travel tips for {trip['destination']}",
        destination=trip["destination"]
    )
    
    system_prompt = f"""You are an expert vacation planning assistant. Use the available tools to:
1. Check weather for the destination
2. Find restaurants, hotels, and museums
3. Manage the vacation calendar

TRIP DETAILS:
- Destination: {trip['destination']}
- Duration: {trip['days']} days
- Budget: ${trip['budget']}
- Travel Style: {trip['trip_style']}

TRAVEL KNOWLEDGE BASE:
{rag_context if rag_context else "No additional knowledge available."}

Return ONLY valid JSON matching this schema (no markdown, no extra text):

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
- Stay within budget
- Each day must have at least 1 activity
- Return complete JSON only
"""

    messages = state.get("messages", [])
    # Count prior tool call rounds to enforce iteration limit
    tool_call_count = sum(
        1 for msg in messages
        if hasattr(msg, "tool_calls") and msg.tool_calls
    )
    if tool_call_count >= MAX_ITERATIONS:
        return Command(goto=END, update={"error": f"Maximum tool iterations ({MAX_ITERATIONS}) reached"})

    llm_with_tools = llm.bind_tools(MCP_TOOLS)
    response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + messages)

    if response.tool_calls:
        return Command(goto="tools", update={"messages": [response]})

    # No tool calls — parse itinerary JSON
    text = response.content
    if isinstance(text, list):
        # Some providers return a list of content blocks
        text = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in text)

    text = text.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.endswith("```"):
        text = text[:-3]

    try:
        itinerary_json = json.loads(text.strip())
        itinerary = StructuredItinerary(**itinerary_json)
        return Command(
            goto="validate",
            update={
                "messages": [response],
                "itinerary_draft": itinerary.model_dump(),
                "approval_state": "draft_ready",
            }
        )
    except json.JSONDecodeError as e:
        return Command(goto=END, update={"messages": [response], "error": f"JSON parse error: {e}"})
    except Exception as e:
        return Command(goto=END, update={"messages": [response], "error": f"Itinerary validation failed: {e}"})


def validate_itinerary_node(state: AgentState) -> Command:
    if state.get("error") or not state.get("itinerary_draft"):
        return Command(goto=END)

    try:
        itinerary = StructuredItinerary(**state["itinerary_draft"])
        trip_days = state["trip"]["days"]
        if len(itinerary.days) != trip_days:
            return Command(
                goto=END,
                update={"error": f"Itinerary has {len(itinerary.days)} days, trip requires {trip_days}"}
            )
        total = itinerary.metadata.total_estimated_cost or 0
        if total > state["trip"]["budget"] * 1.1:
            print(f"Warning: cost ${total:.2f} exceeds budget ${state['trip']['budget']}")
        return Command(goto=END, update={"approval_state": "draft_ready"})
    except Exception as e:
        return Command(goto=END, update={"error": f"Validation failed: {e}"})


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_agent_graph(checkpointer):
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(MCP_TOOLS))
    graph.add_node("validate", validate_itinerary_node)

    graph.set_entry_point("agent")
    graph.add_edge("tools", "agent")
    graph.add_edge("validate", END)

    return graph.compile(checkpointer=checkpointer)


# ============================================================================
# AGENT INVOCATION
# ============================================================================

async def run_agent(
    trip_id: int,
    user_id: int,
    message: str,
    thread_id: str,
    db,
    user_feedback: str = None,
) -> AgentState:
    initial_state: AgentState = {
        "messages": [],
        "trip_id": trip_id,
        "trip": None,
        "user_id": user_id,
        "itinerary_draft": None,
        "approval_state": "planning",
        "user_feedback": user_feedback or message,
        "error": None,
    }
    
    user_msg = user_feedback or message or (
        f"Plan my {state_with_trip['trip']['days']}-day trip to "
        f"{state_with_trip['trip']['destination']} "
        f"with a budget of ${state_with_trip['trip']['budget']}. "
        f"Style: {state_with_trip['trip']['trip_style']}"
    )

    initial_state["messages"] = [HumanMessage(content=user_msg)]
    
    state_with_trip = retrieve_trip_node(initial_state, db)
    if state_with_trip.get("error"):
        return state_with_trip
    
    checkpointer = await _get_checkpointer()
    graph = build_agent_graph(checkpointer)
    
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke(state_with_trip, config=config)
