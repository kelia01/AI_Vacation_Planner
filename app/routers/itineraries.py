from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app import schemas
from app.services import itinerary_service

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.get("/{trip_id}", response_model=schemas.ItineraryResponse)
def get_itinerary(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_itinerary = itinerary_service.get_itinerary(db, trip_id, current_user.id)
    return itinerary_service.build_response(db_itinerary)
