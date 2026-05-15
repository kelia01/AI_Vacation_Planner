from sqlalchemy.orm import Session, joinedload
from app import schemas, models
from app.auth import get_password_hash
import json

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_trip(db: Session, trip: schemas.TripCreate, owner_id: int):
    db_trip = models.Trip(
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
    return db.query(models.Trip).filter(models.Trip.owner_id == owner_id).offset(skip).limit(limit).all()

def get_trip_by_id(db: Session, trip_id: int, owner_id: int):
    return db.query(models.Trip).filter(
        models.Trip.id == trip_id,
        models.Trip.owner_id == owner_id
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

def create_itinerary(db: Session, itinerary: schemas.ItineraryCreate, owner_id: int):
    trip = get_trip_by_id(db, itinerary.trip_id, owner_id)
    if not trip:
        return None

    invalid_days = [d.day for d in itinerary.days if d.day < 1 or d.day > trip.days]
    if invalid_days:
        raise ValueError(f"Days {invalid_days} are out of range for a {trip.days}-day trip")

    existing = db.query(models.Itinerary).filter(
        models.Itinerary.trip_id == itinerary.trip_id
    ).first()

    if existing:
        return None

    db_itinerary = models.Itinerary(trip_id=itinerary.trip_id)
    db.add(db_itinerary)
    db.commit()
    db.refresh(db_itinerary)

    for day_data in itinerary.days:
        db_day = models.ItineraryDay(
            itinerary_id=db_itinerary.id,
            day_number=day_data.day,
            activities=json.dumps(day_data.activities)
        )
        db.add(db_day)

    db.commit()
    return db_itinerary

def get_itinerary_by_trip_id(db: Session, trip_id: int, owner_id: int):
    trip = get_trip_by_id(db, trip_id, owner_id)
    if not trip:
        return None

    return (db.query(models.Itinerary)
            .options(joinedload(models.Itinerary.days))
            .filter(models.Itinerary.trip_id == trip_id)
            .first())

