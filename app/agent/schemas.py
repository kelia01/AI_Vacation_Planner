
from pydantic import BaseModel, Field
from typing import Optional

class PlanningRequest(BaseModel):
    """Request to plan an itinerary."""
    trip_id: int = Field(..., description="Trip to plan")
    message: Optional[str] = Field(None, description="Additional planning instructions")


class PlanningResponse(BaseModel):
    """Response with draft itinerary."""
    status: str = Field(..., description="'success' or 'error'")
    thread_id: str = Field(..., description="Conversation thread ID")
    itinerary: Optional[dict] = Field(None, description="Draft itinerary")
    error: Optional[str] = Field(None, description="Error message if any")

class ReviewRequest(BaseModel):
    """User's review of the draft itinerary."""
    thread_id: str = Field(..., description="Thread ID from planning")
    action: str = Field(..., description="'approve' or 'revise'")
    feedback: Optional[str] = Field(None, description="Feedback if revising")
    itinerary_data: Optional[dict] = Field(None, description="Itinerary to save if approving")


class ReviewResponse(BaseModel):
    """Response to review (either saved itinerary or revised draft)."""
    status: str
    thread_id: str
    itinerary: Optional[dict] = None
    saved_id: Optional[int] = None
    error: Optional[str] = None