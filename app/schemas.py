from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None

class TripCreate(BaseModel):
    destination: str = Field(..., max_length=100, description="destination name")
    days: int = Field(..., ge=1, le=365)
    budget: float = Field(..., ge=0)
    trip_style: str

class TripUpdate(BaseModel):
    destination: str | None = Field(None, max_length=100)
    days: int | None = Field(None, ge=1, le=365)
    budget: float | None = Field(None, ge=0)
    trip_style: str | None = None

class TripResponse(BaseModel):
    id: int
    destination: str
    days: int
    budget: float
    trip_style: str
    message: str
    created_at: datetime
    update_at: datetime | None = None
    owner_id: int

    class Config:
        from_attributes = True

class ItineraryDay(BaseModel):
    day: int
    activities: List[str]

class ItineraryCreate(BaseModel):
    trip_id: int
    days: List[ItineraryDay]

class ItineraryUpdate(BaseModel):
    days: ItineraryDay | None = None

class ItineraryResponse(BaseModel):
    trip_id: int
    itinerary: List[ItineraryDay]
    message: str

    class Config:
        from_attributes = True

