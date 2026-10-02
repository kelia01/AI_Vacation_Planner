from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.agent import run_agent, StructuredItinerary
from app.services import trip_service
from app import crud, schemas
from app.agent.schemas import (  
    PlanningRequest,
    PlanningResponse,
    ReviewRequest,
    ReviewResponse
)

router = APIRouter(prefix="/agent", tags=["agent"])

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
        raise HTTPException(status_code=404, detail="Trip not found")
    
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


@router.post("/review", response_model=ReviewResponse, status_code=status.HTTP_200_OK)
def review_itinerary(
    request: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Review the draft itinerary.
    
    Actions:
    - 'approve': Saves the itinerary to database
    - 'revise': Agent re-enters loop with feedback
    
    Returns:
        If approve: Saved itinerary with ID
        If revise: Revised draft itinerary
    """
    
    # Extract trip_id from thread_id
    try:
        parts = request.thread_id.split("_")
        trip_id = int(parts[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
    
    # Verify trip ownership
    try:
        trip = trip_service.get_trip_by_id(db, trip_id, current_user.id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if request.action == "approve":
        # Save the itinerary
        try:
            structured = StructuredItinerary(**request.itinerary_data)
            legacy_format = structured.to_legacy_format()
            legacy_format["trip_id"] = trip_id
            
            itinerary_create = schemas.ItineraryCreate(**legacy_format)
            db_itinerary = crud.create_itinerary(db, itinerary_create, current_user.id)
            
            if not db_itinerary:
                raise HTTPException(status_code=400, detail="Failed to create itinerary")
            
            return ReviewResponse(
                status="success",
                thread_id=request.thread_id,
                saved_id=db_itinerary.id
            )
            
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid itinerary: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")
    
    elif request.action == "revise":
        # Re-enter agent with feedback
        try:
            agent_state = run_agent(
                trip_id=trip_id,
                user_id=current_user.id,
                message="",
                thread_id=request.thread_id,
                db=db,
                user_feedback=request.feedback
            )
            
            if agent_state.error:
                return ReviewResponse(
                    status="error",
                    thread_id=request.thread_id,
                    error=agent_state.error
                )
            
            return ReviewResponse(
                status="success",
                thread_id=request.thread_id,
                itinerary=agent_state.itinerary_draft
            )
            
        except Exception as e:
            return ReviewResponse(
                status="error",
                thread_id=request.thread_id,
                error=f"Revision failed: {str(e)}"
            )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'revise'")