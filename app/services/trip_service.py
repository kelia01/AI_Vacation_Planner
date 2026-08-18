from fastapi import HTTPException
from app import crud, schemas

def create_trip(db, trip_data, user_id):
    db_trip = crud.create_trip(db, trip_data, user_id)

    response = schemas.TripResponse.model_validate(db_trip)
    response.message = "Trip created successfully"

    return response

def get_trip_by_id(db, trip_id, user_id):
    trip = crud.get_trip_by_id(db, trip_id, user_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

def update_trip(db, trip_id, user_id, trip_update):
    updated_trip = crud.update_trip(db, trip_id, user_id, trip_update)
    if not updated_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return updated_trip

def delete_trip(db, trip_id, user_id):
    deleted = crud.delete_trip(db, trip_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found")
    return None
