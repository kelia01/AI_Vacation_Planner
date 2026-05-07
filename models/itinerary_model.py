from pydantic import BaseModel, Field
from typing import Optional, List

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

class config:
        from_attributes = True


