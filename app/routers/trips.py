# from fastapi import APIRouter, HTTPException, status
# from sqlalchemy.orm import Session
# from app import dependencies, crud, schemas, model
# from database import db
#
# router = APIRouter(prefix="/trips", tags=["trips"])
#
# @router.post("/", response_model=schemas.TripResponse, status_code=status.HTTP_201_CREATED)
# async def create_trip(
#       trip: TripCreate,
#       db: Session = Depends(get_db),
#       current_user: User = Depends(get_current_user)
# ):

#      return crud.create_trip(db, trip, current_user.id)

#
# @router.get("/", response_model=List[schemas.TripResponse], status_code=status.HTTP_200_OK)
# async def get_trips(
#  skip: int = 0,
#  limit: int = 100,
#  db: Session = Depends(get_db),
#  current_user: User = Depends(get_current_user)
#  ):
#     return crud.get_user_trips(db, current_user.id, skip=skip, limit=limit)
#
# @router.get("/{trip_id}", response_model=schemas.TripResponse)
# async def get_trip(trip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     trip = crud.get_trip_by_id(db, trip_id, current_user.id)
#
#     if not trip:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Trip with id {trip_id} not found"
#         )
#
#     return trip
#
# @router.put("/{trip_id}", response_model=schemas.TripResponse)
# async def update_trip(trip_id: int, trip_update: schemas.TripUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     updated_data = trip_update.dict(exclude_unset=True)
#
#     if not updated_data:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"No fields to update"
#         )
#
#     updated_trip = update_trip_by_id(trip_id, updated_data)
#
#     if not updated_trip:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Trip with id {trip_id} not found"
#         )
#
#     return updated_trip
#
# @router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_trip(trip_id):
#     deleted = delete_trip_by_id(trip_id)
#
#     if not deleted:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Trip with id {trip_id} not found"
#         )
#
#     return None
#
#
#
#
