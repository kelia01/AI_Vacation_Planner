from typing import Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    trip_id: int
    trip: Optional[dict]
    user_id: int
    itinerary_draft: Optional[dict]
    approval_state: str
    user_feedback: Optional[str]
    error: Optional[str]
