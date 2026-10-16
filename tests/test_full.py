"""
Full test suite for AI Vacation Planner.
Covers: Auth, Trips, Itineraries, StructuredItinerary models,
Multimodal service, Agent endpoints, MCP client, AgentState.
"""

import json
import base64
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, Trip, Itinerary, ItineraryDay

# ---------------------------------------------------------------------------
# In-memory test DB
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_temp.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_login(client, email="test@example.com", username="testuser", password="secret123"):
    client.post("/auth/register", json={"email": email, "username": username, "password": password})
    # Login uses OAuth2PasswordRequestForm: 'username' field holds the email
    resp = client.post("/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_trip(client, token, destination="Paris", days=3, budget=1000.0, trip_style="cultural"):
    resp = client.post(
        "/trips/",
        json={"destination": destination, "days": days, "budget": budget, "trip_style": trip_style},
        headers=auth_headers(token),
    )
    return resp


SAMPLE_ITINERARY_DATA = {
    "metadata": {
        "destination": "Paris",
        "duration_days": 2,
        "total_estimated_cost": 500.0,
        "travel_style": "cultural",
        "weather_summary": "Sunny",
    },
    "days": [
        {
            "day_number": 1,
            "date": "2024-06-01",
            "theme": "Arrival",
            "activities": [{"name": "Eiffel Tower", "time": "10:00", "description": "Visit", "estimated_cost": 25.0}],
            "estimated_daily_cost": 200.0,
        },
        {
            "day_number": 2,
            "date": "2024-06-02",
            "theme": "Culture",
            "activities": [{"name": "Louvre", "time": "09:00", "description": "Museum", "estimated_cost": 17.0}],
            "estimated_daily_cost": 150.0,
        },
    ],
    "reasoning": "Great cultural trip",
    "recommendations": ["Bring comfortable shoes"],
}


# ===========================================================================
# AUTH
# ===========================================================================

class TestAuth:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={"email": "a@b.com", "username": "alice", "password": "pass123"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "a@b.com"

    def test_register_duplicate_email(self, client):
        data = {"email": "dup@b.com", "username": "user1", "password": "pass123"}
        client.post("/auth/register", json=data)
        data2 = {**data, "username": "user2"}
        resp = client.post("/auth/register", json=data2)
        assert resp.status_code == 400

    def test_register_duplicate_username(self, client):
        client.post("/auth/register", json={"email": "x@b.com", "username": "same", "password": "pass123"})
        resp = client.post("/auth/register", json={"email": "y@b.com", "username": "same", "password": "pass123"})
        assert resp.status_code == 400

    def test_login_success(self, client):
        client.post("/auth/register", json={"email": "u@b.com", "username": "uname", "password": "pass123"})
        resp = client.post("/auth/login", data={"username": "u@b.com", "password": "pass123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={"email": "w@b.com", "username": "wuser", "password": "pass123"})
        resp = client.post("/auth/login", data={"username": "w@b.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", data={"username": "nobody@b.com", "password": "pass123"})
        assert resp.status_code == 401

    def test_get_me(self, client):
        token = register_and_login(client)
        resp = client.get("/users/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    def test_get_me_no_token(self, client):
        resp = client.get("/users/me")
        assert resp.status_code == 401


# ===========================================================================
# TRIPS
# ===========================================================================

class TestTrips:
    def test_create_trip(self, client):
        token = register_and_login(client)
        resp = create_trip(client, token)
        assert resp.status_code == 201
        assert resp.json()["destination"] == "Paris"

    def test_list_trips(self, client):
        token = register_and_login(client)
        create_trip(client, token, destination="Rome")
        create_trip(client, token, destination="Tokyo")
        resp = client.get("/trips/", headers=auth_headers(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_trip_by_id(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token).json()["id"]
        resp = client.get(f"/trips/{trip_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == trip_id

    def test_get_trip_not_found(self, client):
        token = register_and_login(client)
        resp = client.get("/trips/9999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_trip_isolation_between_users(self, client):
        token1 = register_and_login(client, "u1@b.com", "user1")
        token2 = register_and_login(client, "u2@b.com", "user2")
        trip_id = create_trip(client, token1).json()["id"]
        resp = client.get(f"/trips/{trip_id}", headers=auth_headers(token2))
        assert resp.status_code == 404

    def test_update_trip(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token).json()["id"]
        resp = client.put(f"/trips/{trip_id}", json={"destination": "Berlin"}, headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["destination"] == "Berlin"

    def test_delete_trip(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token).json()["id"]
        resp = client.delete(f"/trips/{trip_id}", headers=auth_headers(token))
        assert resp.status_code == 204
        assert client.get(f"/trips/{trip_id}", headers=auth_headers(token)).status_code == 404

    def test_create_trip_invalid_days(self, client):
        token = register_and_login(client)
        resp = create_trip(client, token, days=0)
        assert resp.status_code == 422

    def test_create_trip_negative_budget(self, client):
        token = register_and_login(client)
        resp = create_trip(client, token, budget=-100)
        assert resp.status_code == 422


# ===========================================================================
# ITINERARIES
# ===========================================================================

class TestItineraries:
    def test_get_itinerary_not_found(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token).json()["id"]
        resp = client.get(f"/itineraries/{trip_id}", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_get_itinerary_wrong_user(self, client):
        token1 = register_and_login(client, "u1@b.com", "user1")
        token2 = register_and_login(client, "u2@b.com", "user2")
        trip_id = create_trip(client, token1).json()["id"]
        resp = client.get(f"/itineraries/{trip_id}", headers=auth_headers(token2))
        assert resp.status_code == 404

    def test_get_itinerary_no_auth(self, client):
        resp = client.get("/itineraries/1")
        assert resp.status_code == 401


# ===========================================================================
# STRUCTURED ITINERARY MODELS
# ===========================================================================

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


# ===========================================================================
# MULTIMODAL SERVICE
# ===========================================================================

class TestMultimodalService:
    def test_detect_jpeg(self):
        from app.services.multimodal_service import _detect_media_type
        jpeg_bytes = b"\xff\xd8\xff" + b"\x00" * 10
        assert _detect_media_type(jpeg_bytes) == "image/jpeg"

    def test_detect_png(self):
        from app.services.multimodal_service import _detect_media_type
        png_bytes = b"\x89PNG" + b"\x00" * 10
        assert _detect_media_type(png_bytes) == "image/png"

    def test_detect_unknown_defaults_to_jpeg(self):
        from app.services.multimodal_service import _detect_media_type
        assert _detect_media_type(b"\x00\x00\x00\x00") == "image/jpeg"

    def test_tts_returns_none_without_key(self):
        from app.services.multimodal_service import text_to_speech
        with patch.dict("os.environ", {}, clear=True):
            result = text_to_speech("hello")
        assert result is None

    def test_tts_returns_none_on_api_error(self):
        from app.services.multimodal_service import text_to_speech
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "fake-key"}):
            with patch("app.services.multimodal_service.ElevenLabs") as mock_el:
                mock_el.return_value.text_to_speech.convert.side_effect = Exception("API error")
                result = text_to_speech("hello")
        assert result is None

    def test_analyze_image_calls_claude(self):
        from app.services.multimodal_service import analyze_image
        mock_response = MagicMock()
        mock_response.content = "Eiffel Tower in Paris"
        with patch("app.services.multimodal_service.llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = analyze_image(b"\xff\xd8\xff\x00", content_type="image/jpeg")
        assert result == "Eiffel Tower in Paris"


# ===========================================================================
# AGENT ENDPOINTS
# ===========================================================================

MOCK_AGENT_STATE_SUCCESS = {
    "itinerary_draft": SAMPLE_ITINERARY_DATA,
    "approval_state": "draft_ready",
    "error": None,
    "trip": {"destination": "Paris", "days": 2, "budget": 1000.0, "trip_style": "cultural"},
    "messages": [],
    "trip_id": 1,
    "user_id": 1,
    "user_feedback": None,
}


class TestAgentPlan:
    def test_plan_text_only(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        with patch("app.routers.agent.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {**MOCK_AGENT_STATE_SUCCESS, "trip_id": trip_id}
            with patch("app.routers.agent.text_to_speech", return_value=None):
                resp = client.post(
                    "/agent/plan",
                    data={"trip_id": str(trip_id), "text": "Focus on museums"},
                    headers=auth_headers(token),
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["itinerary"] is not None
        assert body["audio_base64"] is None

    def test_plan_trip_not_found(self, client):
        token = register_and_login(client)
        resp = client.post(
            "/agent/plan",
            data={"trip_id": "9999"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_plan_no_auth(self, client):
        resp = client.post("/agent/plan", data={"trip_id": "1"})
        assert resp.status_code == 401

    def test_plan_agent_error_propagated(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        error_state = {**MOCK_AGENT_STATE_SUCCESS, "error": "LLM failed", "itinerary_draft": None}
        with patch("app.routers.agent.run_agent", new_callable=AsyncMock, return_value=error_state):
            resp = client.post(
                "/agent/plan",
                data={"trip_id": str(trip_id)},
                headers=auth_headers(token),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
        assert "LLM failed" in resp.json()["error"]

    def test_plan_with_audio_merged(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        with patch("app.routers.agent.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {**MOCK_AGENT_STATE_SUCCESS, "trip_id": trip_id}
            with patch("app.routers.agent.transcribe_audio", return_value="I want beaches"):
                with patch("app.routers.agent.text_to_speech", return_value=None):
                    resp = client.post(
                        "/agent/plan",
                        data={"trip_id": str(trip_id), "text": "Budget trip"},
                        files={"audio": ("voice.wav", b"fake-audio", "audio/wav")},
                        headers=auth_headers(token),
                    )
        assert resp.status_code == 200
        msg = mock_run.call_args.kwargs.get("message", "")
        assert "Budget trip" in msg and "beaches" in msg

    def test_plan_with_image(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        with patch("app.routers.agent.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {**MOCK_AGENT_STATE_SUCCESS, "trip_id": trip_id}
            with patch("app.routers.agent.analyze_image", return_value="Eiffel Tower, Paris"):
                with patch("app.routers.agent.text_to_speech", return_value=None):
                    resp = client.post(
                        "/agent/plan",
                        data={"trip_id": str(trip_id)},
                        files={"image": ("photo.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
                        headers=auth_headers(token),
                    )
        assert resp.status_code == 200

    def test_plan_tts_returns_base64(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        fake_audio = b"MP3BYTES"
        with patch("app.routers.agent.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {**MOCK_AGENT_STATE_SUCCESS, "trip_id": trip_id}
            with patch("app.routers.agent.text_to_speech", return_value=fake_audio):
                resp = client.post(
                    "/agent/plan",
                    data={"trip_id": str(trip_id)},
                    headers=auth_headers(token),
                )
        assert resp.status_code == 200
        assert resp.json()["audio_base64"] == base64.b64encode(fake_audio).decode()


class TestAgentReview:
    def _thread_id(self, trip_id, user_id=1):
        return f"trip_{trip_id}_user_{user_id}_abcd1234"

    def test_approve_saves_itinerary(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        thread_id = self._thread_id(trip_id)
        resp = client.post(
            "/agent/review",
            json={"thread_id": thread_id, "action": "approve", "itinerary_data": SAMPLE_ITINERARY_DATA},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["saved_id"] is not None

    def test_approve_then_get_itinerary(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        thread_id = self._thread_id(trip_id)
        client.post(
            "/agent/review",
            json={"thread_id": thread_id, "action": "approve", "itinerary_data": SAMPLE_ITINERARY_DATA},
            headers=auth_headers(token),
        )
        resp = client.get(f"/itineraries/{trip_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert len(resp.json()["days"]) == 2

    def test_revise_calls_agent(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        thread_id = self._thread_id(trip_id)
        revised_state = {**MOCK_AGENT_STATE_SUCCESS, "trip_id": trip_id}
        with patch("app.routers.agent.run_agent", new_callable=AsyncMock, return_value=revised_state):
            resp = client.post(
                "/agent/review",
                json={"thread_id": thread_id, "action": "revise", "feedback": "Add more food options"},
                headers=auth_headers(token),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_invalid_action(self, client):
        token = register_and_login(client)
        trip_id = create_trip(client, token, days=2).json()["id"]
        resp = client.post(
            "/agent/review",
            json={"thread_id": self._thread_id(trip_id), "action": "delete"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_invalid_thread_id_format(self, client):
        token = register_and_login(client)
        resp = client.post(
            "/agent/review",
            json={"thread_id": "bad-format", "action": "approve", "itinerary_data": SAMPLE_ITINERARY_DATA},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_review_no_auth(self, client):
        resp = client.post("/agent/review", json={"thread_id": "trip_1_user_1_abc", "action": "approve"})
        assert resp.status_code == 401


# ===========================================================================
# MCP CLIENT
# ===========================================================================

class TestMCPClient:
    def test_returns_text_result(self):
        from app.agent.mcp_client import call_mcp_tool
        mock_content = MagicMock()
        mock_content.text = "Sunny, 22°C"
        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = False

        async def run():
            with patch("app.agent.mcp_client.stdio_client") as mock_stdio:
                mock_session = AsyncMock()
                mock_session.call_tool.return_value = mock_result
                mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
                with patch("app.agent.mcp_client.ClientSession") as mock_cs:
                    mock_cs.return_value.__aenter__.return_value = mock_session
                    return await call_mcp_tool("get_weather", {"destination": "Paris"})

        result = asyncio.run(run())
        assert result == "Sunny, 22°C"

    def test_propagates_is_error(self):
        from app.agent.mcp_client import call_mcp_tool
        mock_content = MagicMock()
        mock_content.text = "Geocoding failed"
        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = True

        async def run():
            with patch("app.agent.mcp_client.stdio_client") as mock_stdio:
                mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
                with patch("app.agent.mcp_client.ClientSession") as mock_cs:
                    mock_session = AsyncMock()
                    mock_session.call_tool.return_value = mock_result
                    mock_cs.return_value.__aenter__.return_value = mock_session
                    return await call_mcp_tool("get_weather", {"destination": "???"})

        result = asyncio.run(run())
        assert "Tool error" in result

    def test_empty_content_returns_message(self):
        from app.agent.mcp_client import call_mcp_tool
        mock_result = MagicMock()
        mock_result.content = []
        mock_result.isError = False

        async def run():
            with patch("app.agent.mcp_client.stdio_client") as mock_stdio:
                mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
                with patch("app.agent.mcp_client.ClientSession") as mock_cs:
                    mock_session = AsyncMock()
                    mock_session.call_tool.return_value = mock_result
                    mock_cs.return_value.__aenter__.return_value = mock_session
                    return await call_mcp_tool("get_weather", {"destination": "Paris"})

        result = asyncio.run(run())
        assert "no content" in result.lower()


# ===========================================================================
# AGENT STATE
# ===========================================================================

class TestAgentState:
    def test_is_typeddict(self):
        from app.agent.state import AgentState
        import typing
        assert issubclass(AgentState, dict)

    def test_retrieve_trip_node_missing_trip_id(self):
        from app.agent.graph import retrieve_trip_node
        state = {
            "messages": [], "trip_id": None, "trip": None,
            "user_id": 1, "itinerary_draft": None,
            "approval_state": "planning", "user_feedback": None, "error": None,
        }
        result = retrieve_trip_node(state, db=MagicMock())
        assert result["error"] is not None

    def test_retrieve_trip_node_trip_not_found(self):
        from app.agent.graph import retrieve_trip_node
        state = {
            "messages": [], "trip_id": 999, "trip": None,
            "user_id": 1, "itinerary_draft": None,
            "approval_state": "planning", "user_feedback": None, "error": None,
        }
        mock_db = MagicMock()
        with patch("app.agent.graph.trip_service.get_trip_by_id", return_value=None):
            result = retrieve_trip_node(state, db=mock_db)
        assert "not found" in result["error"].lower()
