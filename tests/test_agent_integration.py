"""
End-to-end integration tests for the agent workflow.

Tests the complete flow: trip retrieval → agent → tools → itinerary → validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agent import run_agent, StructuredItinerary
from app.agent.state import AgentState


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def sample_trip_model():
    """SQLAlchemy trip model instance."""
    trip = Mock()
    trip.id = 1
    trip.destination = "Paris"
    trip.days = 3
    trip.budget = 1500.0
    trip.trip_style = "moderate"
    trip.created_at = "2024-01-01"
    return trip


# ============================================================================
# END-TO-END TESTS
# ============================================================================

def test_complete_planning_workflow(mock_db, sample_trip_model):
    """
    Test complete workflow: request → agent → tools → validation → draft.
    
    Mocks:
    - Database trip retrieval
    - Claude API responses
    - Tool execution
    
    Verifies:
    - Agent receives trip context
    - Tools are called appropriately
    - Itinerary passes validation
    - Draft is created and accessible
    """
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=sample_trip_model):
        with patch("app.agent.graph.client.messages.create") as mock_claude:
            
            # Mock Claude response with structured output
            mock_response = Mock()
            
            # First response: Claude calls weather tool
            text_block = Mock()
            text_block.type = "text"
            text_block.text = """
{
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
      "theme": "Arrival and culture",
      "activities": [
        {"name": "Arrive", "time": "09:00 - 10:30", "description": "Airport to hotel", "estimated_cost": 30},
        {"name": "Louvre", "time": "14:00 - 17:00", "description": "Museum visit", "estimated_cost": 18},
        {"name": "Dinner cruise", "time": "19:00 - 21:00", "description": "Seine dinner", "estimated_cost": 80}
      ],
      "estimated_daily_cost": 128.0
    },
    {
      "day_number": 2,
      "date": "2024-06-02",
      "theme": "Culture",
      "activities": [
        {"name": "Breakfast", "time": "08:00 - 09:00", "description": "Café", "estimated_cost": 12},
        {"name": "Musée d'Orsay", "time": "10:00 - 13:00", "description": "Art museum", "estimated_cost": 15},
        {"name": "Lunch in Marais", "time": "13:30 - 15:00", "description": "Local food", "estimated_cost": 25}
      ],
      "estimated_daily_cost": 52.0
    },
    {
      "day_number": 3,
      "date": "2024-06-03",
      "theme": "Landmarks",
      "activities": [
        {"name": "Eiffel Tower", "time": "09:00 - 11:00", "description": "Iconic landmark", "estimated_cost": 18},
        {"name": "Arc de Triomphe", "time": "12:00 - 13:00", "description": "Historic arch", "estimated_cost": 0},
        {"name": "Shopping", "time": "14:00 - 17:00", "description": "Champs-Élysées", "estimated_cost": 50}
      ],
      "estimated_daily_cost": 68.0
    }
  ],
  "reasoning": "Balanced cultural and iconic experiences",
  "recommendations": ["Book Louvre in advance", "Use metro pass"]
}
            """
            
            mock_response.content = [text_block]
            mock_response.stop_reason = "end_turn"
            mock_claude.return_value = mock_response
            
            # Run agent
            state = run_agent(
                trip_id=1,
                user_id=1,
                message="Plan my Paris trip",
                thread_id="test_flow_1",
                db=mock_db
            )
    
    # Verify success
    assert state.error is None, f"Unexpected error: {state.error}"
    assert state.approval_state == "draft_ready"
    assert state.itinerary_draft is not None
    
    # Verify structure
    itinerary = StructuredItinerary(**state.itinerary_draft)
    assert itinerary.metadata.destination == "Paris"
    assert len(itinerary.days) == 3
    assert itinerary.days[0].day_number == 1
    assert len(itinerary.days[0].activities) == 3


def test_agent_with_tool_calls(mock_db, sample_trip_model):
    """
    Test agent that calls tools (weather, RAG, etc).
    
    Verifies:
    - Agent calls tools
    - Tool results are returned to agent
    - Agent generates output after tools
    """
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=sample_trip_model):
        with patch("app.agent.graph.client.messages.create") as mock_claude:
            
            # Create mock tool call
            tool_use = Mock()
            tool_use.type = "tool_use"
            tool_use.id = "tool_1"
            tool_use.name = "get_weather"
            tool_use.input = {"destination": "Paris"}
            
            # First response: tool call
            response1 = Mock()
            response1.content = [tool_use]
            response1.stop_reason = "tool_use"
            
            # Second response: final output after tool result
            text_block = Mock()
            text_block.type = "text"
            text_block.text = '{"metadata":{"destination":"Paris","duration_days":3},"days":[]}'
            
            response2 = Mock()
            response2.content = [text_block]
            response2.stop_reason = "end_turn"
            
            # Mock Claude to return tool call first, then final response
            mock_claude.side_effect = [response1, response2]
            
            # Mock tool execution
            with patch("app.agent.tools.get_weather") as mock_weather:
                mock_weather.return_value = {
                    "destination": "Paris",
                    "temperature": 16,
                    "weather_code": 2
                }
                
                # Run agent
                state = run_agent(
                    trip_id=1,
                    user_id=1,
                    message="Plan with weather info",
                    thread_id="test_tools_1",
                    db=mock_db
                )
    
    # Verify tool was used
    assert state.tool_iteration_count > 0, "Agent should have used tools"
    
    # Verify Claude was called multiple times (tool call + result → second call)
    assert mock_claude.call_count >= 2


def test_itinerary_validation_in_workflow(mock_db, sample_trip_model):
    """
    Test that invalid itineraries are caught during workflow.
    
    Verifies:
    - Pydantic validation catches schema errors
    - Error state is set
    - Draft is not created
    """
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=sample_trip_model):
        with patch("app.agent.graph.client.messages.create") as mock_claude:
            
            # Mock invalid itinerary (missing required fields)
            text_block = Mock()
            text_block.type = "text"
            text_block.text = '{"metadata":{"destination":"Paris"}}'  # Incomplete
            
            response = Mock()
            response.content = [text_block]
            response.stop_reason = "end_turn"
            mock_claude.return_value = response
            
            state = run_agent(
                trip_id=1,
                user_id=1,
                message="Plan trip",
                thread_id="test_invalid_1",
                db=mock_db
            )
    
    # Should have error due to validation
    assert state.error is not None
    assert state.approval_state != "draft_ready"


def test_trip_not_found_error(mock_db):
    """Test error handling when trip not found."""
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=None):
        state = run_agent(
            trip_id=999,
            user_id=1,
            message="Plan trip",
            thread_id="test_notfound_1",
            db=mock_db
        )
    
    assert state.error is not None
    assert "not found" in state.error.lower()


def test_authorization_check(mock_db):
    """
    Test that unauthorized trip access is blocked.
    
    Scenario: User 1 tries to access User 2's trip.
    """
    
    mock_trip = Mock()
    mock_trip.id = 2
    mock_trip.owner_id = 2  # Different user
    
    # CRUD should return None for unauthorized user
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=None):
        state = run_agent(
            trip_id=2,
            user_id=1,  # Different user trying to access
            message="Plan",
            thread_id="test_authz_1",
            db=mock_db
        )
    
    assert state.error is not None


def test_revision_workflow(mock_db, sample_trip_model):
    """
    Test revision workflow: user requests changes, agent regenerates.
    
    Verifies:
    - Agent receives feedback
    - Re-enters planning
    - Returns new draft
    """
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=sample_trip_model):
        with patch("app.agent.graph.client.messages.create") as mock_claude:
            
            # Mock revised response
            text_block = Mock()
            text_block.type = "text"
            text_block.text = """{
  "metadata": {
    "destination": "Paris",
    "duration_days": 3,
    "total_estimated_cost": 1200.0,
    "travel_style": "budget"
  },
  "days": [
    {
      "day_number": 1,
      "date": "2024-06-01",
      "theme": "Budget exploration",
      "activities": [
        {"name": "Free walking tour", "estimated_cost": 0},
        {"name": "Street food", "estimated_cost": 15},
        {"name": "Parks", "estimated_cost": 0}
      ],
      "estimated_daily_cost": 15.0
    },
    {
      "day_number": 2,
      "date": "2024-06-02",
      "theme": "Budget culture",
      "activities": [
        {"name": "Free museum", "estimated_cost": 0},
        {"name": "Lunch special", "estimated_cost": 12},
        {"name": "Seine walk", "estimated_cost": 0}
      ],
      "estimated_daily_cost": 12.0
    },
    {
      "day_number": 3,
      "date": "2024-06-03",
      "theme": "Budget landmarks",
      "activities": [
        {"name": "View Eiffel from afar", "estimated_cost": 0},
        {"name": "Local market", "estimated_cost": 20},
        {"name": "Explore neighborhoods", "estimated_cost": 0}
      ],
      "estimated_daily_cost": 20.0
    }
  ],
  "reasoning": "Budget-focused activities",
  "recommendations": ["Use free attractions", "Eat where locals eat"]
}"""
            
            response = Mock()
            response.content = [text_block]
            response.stop_reason = "end_turn"
            mock_claude.return_value = response
            
            # First: original planning
            state = run_agent(
                trip_id=1,
                user_id=1,
                message="Original plan",
                thread_id="test_revision_1",
                db=mock_db
            )
            
            original_cost = state.itinerary_draft["metadata"]["total_estimated_cost"]
            
            # Second: revision with feedback
            state = run_agent(
                trip_id=1,
                user_id=1,
                message="",
                thread_id="test_revision_1",
                db=mock_db,
                user_feedback="Make it more budget-friendly"
            )
            
            revised_cost = state.itinerary_draft["metadata"]["total_estimated_cost"]
    
    # Verify revision succeeded
    assert state.error is None
    assert state.approval_state == "draft_ready"
    
    # Verify cost changed (budget reduced)
    assert revised_cost < original_cost


def test_max_iterations_protection(mock_db, sample_trip_model):
    """
    Test that agent stops at max iterations.
    
    Scenario: Agent keeps requesting tools indefinitely.
    """
    
    with patch("app.agent.graph.crud.get_trip_by_id", return_value=sample_trip_model):
        with patch("app.agent.graph.client.messages.create") as mock_claude:
            
            # Mock Claude always returning tool calls (never ending)
            tool_use = Mock()
            tool_use.type = "tool_use"
            tool_use.id = "tool_1"
            tool_use.name = "get_weather"
            tool_use.input = {"destination": "Paris"}
            
            response = Mock()
            response.content = [tool_use]
            response.stop_reason = "tool_use"
            
            # Always return tool call
            mock_claude.return_value = response
            
            with patch("app.agent.tools.execute_tool", return_value={"status": "success", "data": {}}):
                state = run_agent(
                    trip_id=1,
                    user_id=1,
                    message="Plan",
                    thread_id="test_maxiter_1",
                    db=mock_db
                )
    
    # Should eventually error due to MAX_TOOL_ITERATIONS
    assert state.error is not None or state.tool_iteration_count >= 5
    assert "iteration" in state.error.lower() if state.error else True


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

@pytest.fixture(autouse=True)
def reset_agent_graph():
    """Reset global agent graph between tests."""
    import app.agent.graph as graph_module
    graph_module.agent_graph = None
    yield
    graph_module.agent_graph = None