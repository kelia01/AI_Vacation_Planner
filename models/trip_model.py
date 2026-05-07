from pydantic import BaseModel, Field
from typing import Optional

class TripCreate(BaseModel):
    destination: str = Field(..., max_length=100, description="destination name")
    days: int
    budget: int
    trip_style: str

class TripUpdate(BaseModel):
    destination: str | None = Field(None, max_length=100)
    days: int | None = Field(None, ge=1, le=365)
    budget: int | None = Field(None, ge=0)
    trip_style: str | None = None

class TripResponse(BaseModel):
    id: int
    destination: str
    days: int
    budget: int
    trip_style: str
    message: str

class config:
    from_attributes = True