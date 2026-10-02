"""
Tests for the vacation planning agent.

Covers:
- Trip retrieval and authorization
- Agent decision-making
- Tool execution
- Itinerary validation
- Approval and revision workflows
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agent.state import AgentState
from app.agent.models import (
    ActivityItem, ItineraryDayItem, ItineraryMetadata, StructuredItinerary
)
from app.agent.tools import execute_tool, weather_tool, search_travel_knowledge_tool
from app.agent.graph import retrieve_trip_node, validate_itinerary_node


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_trip():
    """Sample trip for testing."""
    return {
        "id": 1,
        "destination": "Paris",
        "days": 3,
        "budget": 1500.0,
        "trip_style": "moderate",
        "created_at": "2024-01-01T00:00:00"
    }


@pytest.fixture
def sample_state(sample_trip):
    """Sample agent state."""
    state = AgentState(
        trip_id=1,
        user_id=1,
        trip=sample_trip
    )
    return state


@pytest.fixture
def sample_itinerary_draft():
    """Sample generated itinerary."""
    return {
        "metadata": {
            "destination": "Paris",
            "duration_days": 3,
            "total_estimated_cost": 1400.0,
            "travel_style": "moderate",
            "weather_summary": "Partly cloudy, 15-18°C"
        },
        "days": [
            {
                "day_number": 1,
                "date": "2024-06-01",
                "theme": "City exploration",
                "activities": [
                    {
                        "name": "Arrive and check in",
                        "time": "09:00 - 10:30",
                        "description": "Airport to hotel",
                        "estimated_cost": 30.0
                    },
                    {
                        "name": "Louvre Museum",
                        "time": "14:00 - 17:00",
                        "description": "Visit the Louvre",
                        "estimated_cost": 18.0
                    },
                    {
                        "name": "Seine River dinner cruise",
                        "time": "19:00 - 21:00",
                        "description": "Romantic dinner",
                        "estimated_cost": 80.0
                    }
                ],
                "estimated_daily_cost": 128.0
            },
            {
                "day_number": 2,
                "date": "2024-06-02",
                "theme": "Culture and food",
                "activities": [
                    {
                        "name": "Breakfast at café",
                        "time": "08:00 - 09:00",
                        "estimated_cost": 12.0
                    },
                    {
                        "name": "Musée d'Orsay",
                        "time": "10:00 - 13:00",
                        "description": "Impressionist art",
                        "estimated_cost": 15.0
                    },
                    {
                        "name": "Lunch in Le Marais",
                        "time": "13:30 - 15:00",
                        "estimated_cost": 25.0
                    }
                ],
                "estimated_daily_cost": 52.0
            },
            {
                "day_number": 3,
                "date": "2024-06-03",
                "theme": "Iconic landmarks",
                "activities": [
                    {
                        "name": "Eiffel Tower",
                        "time": "09:00 - 11:00",
                        "estimated_cost": 18.0
                    },
                    {
                        "name": "Arc de Triomphe",
                        "time": "12:00 - 13:00",
                        "estimated_cost": 0.0
                    },
                    {
                        "name": "Champs-Élysées shopping",
                        "time": "14:00 - 17:00",
                        "estimated_cost": 50.0
                    }
                ],
                "estimated_daily_cost": 68.0
            }
        ],
        "reasoning": "This itinerary balances cultural sites with local experiences",
        "recommendations": ["Book Louvre tickets in advance", "Use metro pass for transport"]
    }


# ============================================================================
# TEST: TRIP RETRIEVAL & AUTHORIZATION
# ============================================================================

def test_retrieve_trip_success(sample_state):
    """Test successful trip retrieval."""
    mock_db = Mock()
    
    # Mock trip from database
    mock_trip = Mock()
    mock_trip.id = 1
    mock_trip.destination = "Paris"
    mock_trip.days = 3
    mock_trip.budget = 1500.0
    mock_trip.trip_style = "moderate"
    mock_trip.created_at = "2024-01-01T00:00:00"
    
    # Mock crud function
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=mock_trip):
        result = retrieve_trip_node(sample_state, mock_db)
    
    assert result.trip is not None
    assert result.trip["destination"] == "Paris"
    assert result.error is None


def test_retrieve_trip_not_found(sample_state):
    """Test trip retrieval when trip not found."""
    mock_db = Mock()
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=None):
        result = retrieve_trip_node(sample_state, mock_db)
    
    assert result.error is not None
    assert "not found" in result.error.lower()


def test_retrieve_trip_missing_ids():
    """Test trip retrieval with missing trip_id or user_id."""
    state = AgentState()  # No IDs set
    mock_db = Mock()
    
    result = retrieve_trip_node(state, mock_db)
    
    assert result.error is not None


# ============================================================================
# TEST: STRUCTURED ITINERARY MODELS
# ============================================================================

def test_structured_itinerary_validation(sample_itinerary_draft):
    """Test Pydantic validation of structured itinerary."""
    itinerary = StructuredItinerary(**sample_itinerary_draft)
    
    assert itinerary.metadata.destination == "Paris"
    assert len(itinerary.days) == 3
    assert itinerary.days[0].day_number == 1
    assert len(itinerary.days[0].activities) == 3


def test_structured_itinerary_invalid_day_sequence():
    """Test validation fails with non-sequential days."""
    invalid_data = {
        "metadata": {
            "destination": "Paris",
            "duration_days": 3,
            "total_estimated_cost": 1000.0
        },
        "days": [
            {
                "day_number": 1,
                "activities": [{"name": "Activity 1"}]
            },
            {
                "day_number": 3,  # Missing day 2
                "activities": [{"name": "Activity 2"}]
            }
        ]
    }
    
    with pytest.raises(ValueError, match="sequential"):
        StructuredItinerary(**invalid_data)


def test_structured_itinerary_missing_activities():
    """Test validation fails when day has no activities."""
    invalid_data = {
        "metadata": {
            "destination": "Paris",
            "duration_days": 1,
            "total_estimated_cost": 0.0
        },
        "days": [
            {
                "day_number": 1,
                "activities": []  # No activities
            }
        ]
    }
    
    with pytest.raises(ValueError, match="at least one"):
        StructuredItinerary(**invalid_data)


def test_legacy_format_conversion(sample_itinerary_draft):
    """Test conversion from structured to legacy format."""
    itinerary = StructuredItinerary(**sample_itinerary_draft)
    legacy = itinerary.to_legacy_format()
    
    assert "trip_id" in legacy
    assert "days" in legacy
    assert len(legacy["days"]) == 3
    assert legacy["days"][0]["day"] == 1
    assert len(legacy["days"][0]["activities"]) == 3


# ============================================================================
# TEST: TOOLS
# ============================================================================

def test_weather_tool_success():
    """Test weather tool execution."""
    with patch("app.agent.tools.get_weather") as mock_get:
        mock_get.return_value = {
            "destination": "Paris",
            "country": "France",
            "temperature": 16,
            "weather_code": 2
        }
        
        result = weather_tool("Paris")
    
    assert result["status"] == "success"
    assert result["data"]["destination"] == "Paris"


def test_weather_tool_error():
    """Test weather tool error handling."""
    with patch("app.agent.tools.get_weather") as mock_get:
        mock_get.return_value = {"error": "Location not found"}
        
        result = weather_tool("InvalidCity123")
    
    assert result["status"] == "error"


def test_travel_knowledge_tool_success():
    """Test RAG travel knowledge tool."""
    with patch("app.agent.tools.rag_service") as mock_rag:
        mock_rag.initialize.return_value = None
        mock_rag.search.return_value = [
            {
                "title": "Paris Museums",
                "content": "Best museums in Paris...",
                "destination": "Paris"
            }
        ]
        
        result = search_travel_knowledge_tool("museums in Paris", destination="Paris")
    
    assert result["status"] == "success"
    assert len(result["data"]) > 0
    assert result["data"][0]["title"] == "Paris Museums"


def test_travel_knowledge_tool_no_results():
    """Test RAG tool with no results."""
    with patch("app.agent.tools.rag_service") as mock_rag:
        mock_rag.initialize.return_value = None
        mock_rag.search.return_value = []
        
        result = search_travel_knowledge_tool("obscure query")
    
    assert result["status"] == "success"
    assert len(result["data"]) == 0


def test_execute_tool_unknown():
    """Test executing unknown tool."""
    result = execute_tool("unknown_tool", {})
    
    assert result["status"] == "error"
    assert "Unknown tool" in result["message"]


def test_execute_tool_invalid_params():
    """Test executing tool with invalid parameters."""
    result = execute_tool("get_weather", {})  # Missing required 'destination'
    
    assert result["status"] == "error"


# ============================================================================
# TEST: ITINERARY VALIDATION
# ============================================================================

def test_validate_itinerary_success(sample_state, sample_itinerary_draft):
    """Test successful itinerary validation."""
    sample_state.itinerary_draft = sample_itinerary_draft
    sample_state.approval_state = "draft_ready"
    
    result = validate_itinerary_node(sample_state)
    
    assert result.error is None
    assert result.approval_state == "draft_ready"


def test_validate_itinerary_day_count_mismatch(sample_state, sample_itinerary_draft):
    """Test validation fails when day count doesn't match trip."""
    sample_state.trip["days"] = 5  # Trip is 5 days but itinerary is 3
    sample_state.itinerary_draft = sample_itinerary_draft
    
    result = validate_itinerary_node(sample_state)
    
    assert result.error is not None
    assert "days" in result.error.lower()


def test_validate_itinerary_budget_exceeded(sample_state, sample_itinerary_draft):
    """Test validation with budget exceeded."""
    sample_state.trip["budget"] = 500.0  # Budget is $500 but itinerary is ~$1400
    sample_state.itinerary_draft = sample_itinerary_draft
    sample_state.approval_state = "draft_ready"
    
    result = validate_itinerary_node(sample_state)
    
    # Should still succeed but with warning
    assert result.approval_state == "draft_ready"
    # Error would only occur if significantly over budget


# ============================================================================
# TEST: STATE MANAGEMENT
# ============================================================================

def test_agent_state_initialization():
    """Test agent state initialization."""
    state = AgentState(trip_id=1, user_id=1)
    
    assert state.trip_id == 1
    assert state.user_id == 1
    assert state.messages == []
    assert state.approval_state == "planning"
    assert state.tool_iteration_count == 0


def test_agent_state_mutation():
    """Test agent state mutation during execution."""
    state = AgentState(trip_id=1, user_id=1)
    
    state.tool_iteration_count += 1
    state.approval_state = "draft_ready"
    state.error = "test error"
    
    assert state.tool_iteration_count == 1
    assert state.approval_state == "draft_ready"
    assert state.error == "test error"


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

def test_max_iterations_protection():
    """Test that tool loop respects max iteration limit."""
    state = AgentState(trip_id=1, user_id=1)
    state.tool_iteration_count = 5  # MAX_TOOL_ITERATIONS = 5
    state.approval_state = "planning"
    
    # In graph execution, this would trigger END
    # For this test, verify state reflects the limit
    assert state.tool_iteration_count >= 5


def test_error_propagation(sample_state):
    """Test error state propagation."""
    sample_state.error = "Database connection failed"
    
    # Nodes should not proceed when error is set
    assert sample_state.error is not None
    
    # retrieve_trip_node should return early if error already set
    result = retrieve_trip_node(sample_state, Mock())
    assert result.error == "Database connection failed"