from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/trips", tags=["trips"])

@router.post("/", response_model=schemas.TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    trip: schemas.TripCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_trip = crud.create_trip(db, trip, current_user.id)
    response = schemas.TripResponse.model_validate(db_trip)
    response.message = "Trip created successfully"
    return response

@router.get("/", response_model=list[schemas.TripResponse])
def get_all_trips(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_user_trips(db, current_user.id, skip=skip, limit=limit)

@router.get("/{trip_id}", response_model=schemas.TripResponse)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    trip = crud.get_trip_by_id(db, trip_id, current_user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.put("/{trip_id}", response_model=schemas.TripResponse)
def update_trip(
    trip_id: int,
    trip_update: schemas.TripUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_trip = crud.update_trip(db, trip_id, current_user.id, trip_update)
    if not updated_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return updated_trip

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = crud.delete_trip(db, trip_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found")
    return None