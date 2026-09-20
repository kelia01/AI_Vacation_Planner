"""
LangGraph agent state definition.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from langchain_core.messages import AnyMessage


@dataclass
class AgentState:
    """
    State for the vacation planning agent.
    
    Fields:
    - messages: LangChain message history (HumanMessage, AIMessage, ToolMessage)
    - trip_id: Database ID of the trip
    - trip: Cached trip details
    - user_id: Authenticated user ID
    - itinerary_draft: Generated itinerary awaiting approval
    - approval_state: 'planning', 'draft_ready', 'approved', or 'revising'
    - user_feedback: User feedback for revisions
    - error: Error message if any
    """
    
    messages: list[AnyMessage] = field(default_factory=list)
    trip_id: int = 0
    trip: Optional[dict] = None
    user_id: int = 0
    
    itinerary_draft: Optional[dict] = None
    approval_state: str = "planning"
    user_feedback: Optional[str] = None
    
    error: Optional[str] = None