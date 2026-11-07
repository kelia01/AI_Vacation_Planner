"""
LangGraph workflow for the vacation planning agent.
"""

import json
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
import re

from app.agent.state import AgentState
from app.agent.itinerary_models import StructuredItinerary
from app.agent.mcp_tools import MCP_TOOLS
from app.services import trip_service, evaluator
from app.services.rag_service import rag_service
from app.services.observability import AgentObservabilityHandler

from app.services.evaluator import evaluate_itinerary
import logging

_logger = logging.getLogger("agent.graph")

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
    
    user_message = state.get("user_feedback", "") or ""
    
    system_prompt = f"""You are an expert vacation planning assistant. Use the available tools to:
1. Check weather for the destination
2. Find restaurants, hotels, and museums
3. Manage the vacation calendar


TRIP DETAILS:
- Destination: {trip['destination']}
- Duration: {trip['days']} days
- Budget: ${trip['budget']}
- Travel Style: {trip['trip_style']}
{f"- User request: {user_message}" if user_message else ""}

TRAVEL KNOWLEDGE BASE:
{rag_context if rag_context else "No additional knowledge available."}

- CRITICAL: Total cost across ALL days must not exceed ${trip['budget']}. Never suggest activities whose individual cost exceeds the daily budget of ${round(trip['budget'] / trip['days'], 0)}.

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

After using tools to gather data, you MUST return the complete JSON itinerary.
Do not stop after tool calls - always produce the final JSON output.
"""

    messages = state.get("messages", [])
    # Count prior tool call rounds to enforce iteration limit
    tool_call_count = sum(
        1 for msg in messages
        if hasattr(msg, "tool_calls") and msg.tool_calls
    )
    if tool_call_count >= MAX_ITERATIONS:
        return Command(goto=END, update={"error": f"Maximum tool iterations ({MAX_ITERATIONS}) reached"})

    has_tool_results = any(isinstance(m, ToolMessage) for m in messages)

    if has_tool_results:
        response = llm.invoke([SystemMessage(content=system_prompt)] + messages)
    else:
        response = llm.bind_tools(MCP_TOOLS).invoke([SystemMessage(content=system_prompt)] + messages)

    if response.tool_calls:
        return Command(goto="tools", update={"messages": [response]})

    # No tool calls — parse itinerary JSON
    text = response.content
    
    _logger.warning(
        "DIAG agent_node: has_tool_results=%s content_type=%s raw_content=%r",
        has_tool_results,
        type(response.content).__name__,
        response.content if not isinstance(response.content, str) else response.content[:500],
    )
    
    if isinstance(text, list):
        text = " ".join(
            b["text"] for b in text
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text")
        )

    text = text.strip()
    
    _logger.warning("DIAG agent_node: text_after_processing=%r", text[:300] if text else repr(text))

    if not text:
        return Command(goto=END, update={"messages": [response], "error": "LLM returned empty response after tool calls"})


    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()
    else:
        # No markdown fence — strip leading/trailing fences if present
        for prefix in ("```json", "```"):
            if text.startswith(prefix):
                text = text[len(prefix):]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()


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


MAX_VALIDATION_RETRIES = 2


def validate_itinerary_node(state: AgentState) -> Command:
    if state.get("error") or not state.get("itinerary_draft"):
        return Command(goto=END)

    try:
        itinerary = StructuredItinerary(**state["itinerary_draft"])
        result = evaluate_itinerary(itinerary.model_dump(), state["trip"])

        if not result.passed:
            retries = state.get("validation_retries") or 0
            if retries >= MAX_VALIDATION_RETRIES:
                _logger.warning(
                    "Validation failed after %d retries — returning best draft. Failures: %s",
                    retries, result.failure_summary,
                )
                return Command(goto=END, update={
                    "approval_state": "draft_ready",
                    "user_feedback": f"Note: itinerary has minor issues — {result.failure_summary}",
                })
            return Command(goto="agent", update={
                "approval_state": "evaluation_failed",
                "user_feedback": result.failure_summary,
                "validation_retries": retries + 1,
            })

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
        "validation_retries": 0,
    }
    initial_state["messages"] = [HumanMessage(content=user_feedback or message or "Plan my trip")]
    
    state_with_trip = retrieve_trip_node(initial_state, db)
    if state_with_trip.get("error"):
        _logger.error("Trip retrieval failed: %s", state_with_trip["error"])
        return state_with_trip
    
    if not (user_feedback or message):
        trip = state_with_trip["trip"]
        default_msg = (
            f"Plan my {trip['days']}-day trip to {trip['destination']} "
            f"with a budget of ${trip['budget']}. Style: {trip['trip_style']}"
        )
        state_with_trip["messages"] = [HumanMessage(content=default_msg)]
    
    checkpointer = await _get_checkpointer()
    graph = build_agent_graph(checkpointer)
    
    handler = AgentObservabilityHandler(trip_id=trip_id, user_id=user_id, thread_id=thread_id)
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [handler],       
    }

    final_state = await graph.ainvoke(state_with_trip, config=config)
    return final_state