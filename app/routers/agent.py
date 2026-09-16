"""
API routes for the vacation planning agent workflow.

Endpoints for planning, approval, and revision of itineraries.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.agent import run_agent, StructuredItinerary
from app.services import trip_service
from app import crud, schemas


router = APIRouter(prefix="/agent", tags=["agent"])


# ============================================================================
# SCHEMAS
# ============================================================================

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


class ApprovalRequest(BaseModel):
    """Request to approve a draft itinerary."""
    thread_id: str = Field(..., description="Thread ID of planning conversation")


class RevisionRequest(BaseModel):
    """Request revisions to the draft itinerary."""
    thread_id: str = Field(..., description="Thread ID of planning conversation")
    feedback: str = Field(..., description="Revision feedback for the agent")


class RevisionResponse(BaseModel):
    """Response with revised itinerary."""
    status: str = Field(..., description="'success' or 'error'")
    thread_id: str
    itinerary: Optional[dict] = Field(None, description="Revised itinerary")
    error: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/plan", response_model=PlanningResponse, status_code=status.HTTP_200_OK)
def plan_itinerary(
    request: PlanningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start the itinerary planning process using the AI agent.
    
    The agent will:
    1. Retrieve trip details
    2. Use tools (weather, places, costs, travel knowledge) as needed
    3. Generate a structured itinerary
    4. Return draft for user approval
    
    Returns:
        Draft itinerary and thread_id for follow-up (approve/revise)
    """
    
    # Verify trip exists and user owns it
    try:
        trip = trip_service.get_trip_by_id(db, request.trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )
    
    # Generate thread ID for this planning session
    thread_id = f"trip_{request.trip_id}_user_{current_user.id}_{id(request)}"
    
    # Run the agent
    try:
        agent_state = run_agent(
            trip_id=request.trip_id,
            user_id=current_user.id,
            message=request.message or f"Plan a {trip.days}-day trip to {trip.destination}",
            thread_id=thread_id,
            db=db
        )
        
        if agent_state.error:
            return PlanningResponse(
                status="error",
                thread_id=thread_id,
                error=agent_state.error
            )
        
        if agent_state.approval_state != "draft_ready":
            return PlanningResponse(
                status="error",
                thread_id=thread_id,
                error="Agent failed to generate itinerary"
            )
        
        return PlanningResponse(
            status="success",
            thread_id=thread_id,
            itinerary=agent_state.itinerary_draft
        )
        
    except Exception as e:
        return PlanningResponse(
            status="error",
            thread_id=thread_id,
            error=f"Planning failed: {str(e)}"
        )


@router.post("/approve", status_code=status.HTTP_201_CREATED)
def approve_itinerary(
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve the draft itinerary and save it to the database.
    
    Args:
        request: Contains thread_id from planning request
        
    Returns:
        Created itinerary with ID
    """
    
    # Extract trip_id from thread_id
    # Format: trip_{trip_id}_user_{user_id}_...
    try:
        parts = request.thread_id.split("_")
        trip_id = int(parts[1])
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid thread_id format"
        )
    
    # Verify trip ownership
    try:
        trip = trip_service.get_trip_by_id(db, trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )
    
    # In production, retrieve the draft from state store or cache
    # For now, we accept the approval and the client must re-provide the itinerary
    # This is a simplified implementation
    
    # Note: Full implementation would:
    # 1. Retrieve state from LangGraph checkpointer
    # 2. Verify itinerary_draft exists
    # 3. Convert to legacy format
    # 4. Save via CRUD
    
    raise HTTPException(
        status_code=501,
        detail="Approval endpoint requires state retrieval from checkpointer - see implementation notes"
    )


@router.post("/revise", response_model=RevisionResponse, status_code=status.HTTP_200_OK)
def revise_itinerary(
    request: RevisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request revisions to the draft itinerary.
    
    The agent re-enters the planning loop with your feedback and may:
    - Fetch new tool data
    - Regenerate activities
    - Adjust costs
    - Return a revised itinerary
    
    Args:
        request: Contains thread_id and revision feedback
        
    Returns:
        Revised itinerary draft
    """
    
    # Extract trip_id from thread_id
    try:
        parts = request.thread_id.split("_")
        trip_id = int(parts[1])
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid thread_id format"
        )
    
    # Verify trip ownership
    try:
        trip = trip_service.get_trip_by_id(db, trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )
    
    # Run the agent again with feedback in revision mode
    try:
        agent_state = run_agent(
            trip_id=trip_id,
            user_id=current_user.id,
            message="",  # Use feedback below
            thread_id=request.thread_id,
            db=db,
            user_feedback=request.feedback
        )
        
        if agent_state.error:
            return RevisionResponse(
                status="error",
                thread_id=request.thread_id,
                error=agent_state.error
            )
        
        if agent_state.approval_state != "draft_ready":
            return RevisionResponse(
                status="error",
                thread_id=request.thread_id,
                error="Agent failed to generate revised itinerary"
            )
        
        return RevisionResponse(
            status="success",
            thread_id=request.thread_id,
            itinerary=agent_state.itinerary_draft
        )
        
    except Exception as e:
        return RevisionResponse(
            status="error",
            thread_id=request.thread_id,
            error=f"Revision failed: {str(e)}"
        )


@router.post("/save-itinerary", response_model=schemas.ItineraryResponse, status_code=status.HTTP_201_CREATED)
def save_itinerary(
    trip_id: int,
    itinerary_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save an approved itinerary to the database.
    
    This endpoint converts the structured itinerary to the legacy format
    and persists it via CRUD.
    
    Args:
        trip_id: Trip ID
        itinerary_data: Structured itinerary dictionary
        
    Returns:
        Persisted itinerary
    """
    
    # Verify trip ownership
    try:
        trip = trip_service.get_trip_by_id(db, trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )
    
    try:
        # Validate the itinerary structure
        structured = StructuredItinerary(**itinerary_data)
        
        # Convert to legacy format
        legacy_format = structured.to_legacy_format()
        legacy_format["trip_id"] = trip_id
        
        # Create itinerary using CRUD
        itinerary_create = schemas.ItineraryCreate(**legacy_format)
        db_itinerary = crud.create_itinerary(db, itinerary_create, current_user.id)
        
        if not db_itinerary:
            raise HTTPException(
                status_code=400,
                detail="Failed to create itinerary"
            )
        
        return schemas.ItineraryResponse.model_validate(db_itinerary)
        
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid itinerary structure: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save itinerary: {str(e)}"
        )