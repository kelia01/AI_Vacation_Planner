"""
LangGraph agent state definition.

Maintains conversation state, tool execution history, and itinerary drafts.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class AgentState:
    """
    State object for the vacation planning agent.
    
    Fields:
    - messages: Conversation history (LangChain format)
    - trip_id: Database ID of the trip
    - trip: Cached trip details
    - user_id: Authenticated user ID
    - tool_iteration_count: Tracks tool execution loops
    - tool_results: Results from most recent tool execution
    - itinerary_draft: Generated itinerary awaiting approval
    - approval_state: 'pending', 'approved', or 'revising'
    - user_feedback: Feedback from user revision request
    """
    
    messages: list = field(default_factory=list)
    trip_id: int = 0
    trip: Optional[dict] = None
    user_id: int = 0
    
    tool_iteration_count: int = 0
    tool_results: dict = field(default_factory=dict)
    
    itinerary_draft: Optional[dict] = None
    approval_state: str = "planning"  # planning, draft_ready, approved, revising
    user_feedback: Optional[str] = None
    
    error: Optional[str] = None