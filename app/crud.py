from sqlalchemy.orm import Session
from models import model
from schema import schemas
from auth import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(model.User).filter(model.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(model.User).filter(model.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = model.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_trip(db: Session, trip: schemas.TripCreate, owner_id: int):
    db_trip = model.Trip(
        destination=trip.destination,
        days=trip.days,
        budget=trip.budget,
        trip_style=trip.trip_style,
        owner_id = owner_id
    )
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip

def get_user_trips(db: Session, owner_id: int, skip: int = 0, limit: int = 10):
    return db.query(model.Trip).filter(model.Trip.owner_id == owner_id).offset(skip).limit(limit).all()

def get_trip_by_id(db: Session, trip_id: int, owner_id: int):
    return db.query(model.Trip).filter(
        model.Trip.id == trip_id,
        model.Trip.owner_id == owner_id
    ).first()

def update_trip(db: Session, trip_id: int, owner_id: int, trip_update: schemas.TripUpdate):
    db_trip = get_trip_by_id(db, trip_id, owner_id)
    if not db_trip:
        return None

    update_data = trip_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trip, field, value)

    db.commit()
    db.refresh(db_trip)
    return db_trip

def delete_trip(db: Session, trip_id: int, owner_id: int) -> bool:
    db_trip = get_trip_by_id(db, trip_id, owner_id)
    if not db_trip:
        return False

    db.delete(db_trip)
    db.commit()
    return True