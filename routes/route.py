from fastapi import APIRouter, HTTPException, status
from typing import List

from models.trip_model import TripCreate, TripUpdate, TripResponse
from database.trip_db import (save_trip)

router = APIRouter(prefix="/trips", tags=["trips"])

@router.post("/", response_model=TripResponse, status=status.HTTP_201_CREATED)
async def create_trip(trip: TripCreate):
    trip_data = {
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "trip_style": trip.trip_style
    }

    created_trip = save_trip(trip_data)

    return created_trip

@router.get("/", response_model=List[TripResponse], status=status.HTTP_200):
async def get_trips():
    return get_all_trips()

@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: int):
    trip = get_trip_by_id(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with id {trip_id} not found"
        )

    return trip

@router.put("/{trip_id}", response=TripResponse)
async def update_trip(trip_id: int, trip_update: TripUpdate):
    updated_data = trip_update.dict(exclude_unset=True)

    if not updated_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fields to update"
        )

    updated_trip = update_trip_by_id(trip_id, updated_data)

    if not updated_trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with id {trip_id} not found
        )

    return updated_trip

@router.delete("/{trip_id}", status=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id):
    deleted = delete_trip_by_id(trip_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with id {trip_id} not found
        )

    return None




