from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from app import schemas, crud
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.ai_itinerary_service import generate_ai_itinerary
from app.services.rag_answer_service import answer_travel_question

router = APIRouter(prefix="/itineraries", tags=["itineraries"])

@router.post("/ask")
def ask_travel_question(
    question_data: schemas.AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ask a travel question with RAG-augmented response.
    """
    destination = None
    
    if question_data.trip_id:
        trip = crud.get_trip_by_id(db, question_data.trip_id, current_user.id)
        if trip:
            destination = trip.destination
    
    try:
        result = answer_travel_question(question_data.question, destination)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error answering question: {str(e)}"
        )
@router.post("/generate/{trip_id}", response_model=schemas.ItineraryResponse)
def generate_itinerary(
        trip_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        db_itinerary = generate_ai_itinerary(
            db,
            trip_id,
            current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    if not db_itinerary:
        raise HTTPException(
            status_code=400,
            detail="Unable to create itinerary"
        )

    days = [
        schemas.ItineraryDay(
            day=day.day_number,
            activities=json.loads(day.activities)
        )
        for day in sorted(
            db_itinerary.days,
            key=lambda x: x.day_number
        )
    ]

    return schemas.ItineraryResponse(
        id=db_itinerary.id,
        trip_id=db_itinerary.trip_id,
        days=days,
        created_at=db_itinerary.created_at
    )

@router.get("/{trip_id}", response_model=schemas.ItineraryResponse)
def get_itinerary(
        trip_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_itinerary = crud.get_itinerary_by_trip_id(db, trip_id, current_user.id)
    if not db_itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    days = [
        schemas.ItineraryDay(
            day=day.day_number,
            activities=json.loads(day.activities)
        )
        for day in sorted(db_itinerary.days, key=lambda x: x.day_number)
    ]

    return schemas.ItineraryResponse(
        id=db_itinerary.id,
        trip_id=db_itinerary.trip_id,
        days=days,
        created_at=db_itinerary.created_at
    )