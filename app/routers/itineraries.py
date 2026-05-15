from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
import json
from app import schemas, crud, tasks
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("/", response_model=schemas.ItineraryResponse, status_code=status.HTTP_201_CREATED)
def create_itinerary(
        itinerary: schemas.ItineraryCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        db_itinerary = crud.create_itinerary(db, itinerary, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not db_itinerary:
            raise HTTPException(status_code=404, detail="Trip not found or itinerary already exists")

    days = [
        schemas.ItineraryDayResponse(
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
        schemas.ItineraryDayResponse(
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


@router.post("/generate/{trip_id}")
def generate_itinerary_async(
        trip_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    trip = crud.get_trip_by_id(db, trip_id, current_user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    background_tasks.add_task(
        tasks.generate_itinerary_background,
        trip_id=trip_id,
        destination=trip.destination,
        days=trip.days
    )

    return {
        "message": "Itinerary generation started",
        "trip_id": trip_id,
        "status": "processing",
        "check_endpoint": f"/itineraries/status/{trip_id}"
    }


@router.get("/status/{trip_id}")
def get_generation_status(trip_id: int):
    task_id = f"trip_{trip_id}"
    result = tasks.task_results.get(task_id)

    if not result:
        return {
            "trip_id": trip_id,
            "status": "not_found",
            "message": "No generation task found for this trip"
        }

    return {
        "trip_id": trip_id,
        "status": result.get("status"),
        "result": result.get("result"),
        "error": result.get("error")
    }
