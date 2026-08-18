from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import List
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
    message: str = "Trip created successfully"
    created_at: datetime
    updated_at: datetime | None = None
    owner_id: int

    class Config:
        from_attributes = True

class ItineraryDay(BaseModel):
    day: int = Field(..., ge=1)
    activities: List[str]

    @field_validator("activities")
    @classmethod
    def validate_activities(cls, activities):

        if len(activities) == 0:
            raise ValueError(
                "Each day must contain at least one activity."
            )

        return activities

class ItineraryCreate(BaseModel):
    trip_id: int
    days: List[ItineraryDay]

    @field_validator("days")
    @classmethod
    def reject_duplicate_days(cls, days):

        numbers = [d.day for d in days]

        if len(numbers) != len(set(numbers)):
            raise ValueError(
                "Duplicate day numbers are not allowed."
            )

        return days

    @model_validator(mode="after")
    def validate_day_sequence(self):

        expected = list(range(1, len(self.days) + 1))
        actual = sorted(day.day for day in self.days)

        if expected != actual:
            raise ValueError(
                "Day numbers must be consecutive."
            )

        return self
class ItineraryResponse(BaseModel):
    id: int
    trip_id: int
    days: List[ItineraryDay]
    created_at: datetime

    class Config:
        from_attributes = True

