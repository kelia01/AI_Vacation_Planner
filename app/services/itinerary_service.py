import json
from fastapi import HTTPException
from app import crud, schemas


def get_itinerary(db, trip_id: int, user_id: int):
    itinerary = crud.get_itinerary_by_trip_id(db, trip_id, user_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return itinerary


def create_itinerary(db, itinerary_data: schemas.ItineraryCreate, user_id: int):
    result = crud.create_itinerary(db, itinerary_data, user_id)
    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Itinerary already exists for this trip. Use update instead."
        )
    return result


def update_itinerary(db, itinerary_data: schemas.ItineraryCreate, user_id: int):
    result = crud.update_itinerary(db, itinerary_data, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return result


def build_response(db_itinerary) -> schemas.ItineraryResponse:
    """Convert ORM itinerary to ItineraryResponse schema."""
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
        created_at=db_itinerary.created_at,
    )
