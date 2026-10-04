"""
Structured Pydantic models for agent-generated itineraries.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class ActivityItem(BaseModel):
    """A single activity in a day's itinerary."""
    
    name: str = Field(..., description="Activity name")
    time: Optional[str] = Field(None, description="Suggested time (e.g., '9:00 AM - 11:00 AM')")
    description: Optional[str] = Field(None, description="Brief description")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost in USD")
    

class ItineraryDayItem(BaseModel):
    """A single day in the itinerary."""
    
    day_number: int = Field(..., ge=1, description="Day number")
    date: Optional[str] = Field(None, description="Date (YYYY-MM-DD)")
    theme: Optional[str] = Field(None, description="Day theme (e.g., 'Cultural Exploration')")
    activities: List[ActivityItem] = Field(default_factory=list, description="Activities for the day")
    estimated_daily_cost: Optional[float] = Field(None, description="Estimated daily cost in USD")
    
    @field_validator("activities")
    @classmethod
    def validate_activities(cls, activities):
        if len(activities) == 0:
            raise ValueError("Each day must contain at least one activity.")
        return activities


class ItineraryMetadata(BaseModel):
    """Metadata about the generated itinerary."""
    
    destination: str = Field(..., description="Trip destination")
    duration_days: int = Field(..., ge=1, description="Number of days")
    total_estimated_cost: Optional[float] = Field(None, description="Total estimated cost in USD")
    travel_style: Optional[str] = Field(None, description="Travel style (e.g., 'luxury', 'budget')")
    weather_summary: Optional[str] = Field(None, description="Weather forecast summary")
    

class StructuredItinerary(BaseModel):
    """Complete structured itinerary output from the agent."""
    
    metadata: ItineraryMetadata
    days: List[ItineraryDayItem] = Field(..., description="List of days")
    reasoning: Optional[str] = Field(None, description="Why the agent chose these activities")
    recommendations: Optional[List[str]] = Field(None, description="Additional tips and recommendations")
    
    @field_validator("days")
    @classmethod
    def validate_days_sequence(cls, days):
        """Ensure days are sequential from 1 to N."""
        if not days:
            raise ValueError("Itinerary must contain at least one day.")
        
        numbers = [d.day_number for d in days]
        expected = list(range(1, len(days) + 1))
        
        if numbers != sorted(numbers):
            raise ValueError("Days must be in sequential order.")
        if expected != numbers:
            raise ValueError(f"Days must be numbered 1 to {len(days)}, got {numbers}")
        
        return days
    
    def to_legacy_format(self) -> dict:
        """
        Convert to Phase 4 itinerary format for database persistence.
        
        Returns dict compatible with existing ItineraryCreate schema.
        """
        return {
            "trip_id": 0,  # Set by caller
            "days": [
                {
                    "day": day.day_number,
                    "activities": [f"{a.name}" + (f" ({a.time})" if a.time else "") for a in day.activities]
                }
                for day in self.days
            ]
        }