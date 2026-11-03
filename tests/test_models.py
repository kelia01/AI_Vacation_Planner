import pytest
from unittest.mock import patch, AsyncMock
from tests.conftest import (
    SAMPLE_ITINERARY_DATA
)

class TestStructuredItinerary:
    def test_valid_itinerary(self):
        from app.agent.itinerary_models import StructuredItinerary
        it = StructuredItinerary(**SAMPLE_ITINERARY_DATA)
        assert it.metadata.destination == "Paris"
        assert len(it.days) == 2

    def test_day_must_have_activity(self):
        from app.agent.itinerary_models import StructuredItinerary
        import pydantic
        bad = {**SAMPLE_ITINERARY_DATA, "days": [
            {**SAMPLE_ITINERARY_DATA["days"][0], "activities": []},
        ]}
        with pytest.raises(pydantic.ValidationError):
            StructuredItinerary(**bad)

    def test_days_must_be_sequential(self):
        from app.agent.itinerary_models import StructuredItinerary
        import pydantic
        bad = {**SAMPLE_ITINERARY_DATA, "days": [
            {**SAMPLE_ITINERARY_DATA["days"][1]},  # day_number=2 first
            {**SAMPLE_ITINERARY_DATA["days"][0]},  # day_number=1 second
        ]}
        with pytest.raises(pydantic.ValidationError):
            StructuredItinerary(**bad)

    def test_to_legacy_format(self):
        from app.agent.itinerary_models import StructuredItinerary
        it = StructuredItinerary(**SAMPLE_ITINERARY_DATA)
        legacy = it.to_legacy_format()
        assert "days" in legacy
        assert legacy["days"][0]["day"] == 1
        assert isinstance(legacy["days"][0]["activities"], list)
        assert isinstance(legacy["days"][0]["activities"][0], str)

    def test_activity_item_fields(self):
        from app.agent.itinerary_models import ActivityItem
        a = ActivityItem(name="Eiffel Tower", time="10:00", description="Visit", estimated_cost=25.0)
        assert a.name == "Eiffel Tower"
        assert a.estimated_cost == 25.0
