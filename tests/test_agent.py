
import base64
from unittest.mock import patch, AsyncMock, MagicMock
from tests.conftest import (
    register_and_login, auth_headers, create_trip, SAMPLE_ITINERARY_DATA, MOCK_AGENT_STATE_SUCCESS
)

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
        assert resp.json()["error"] is not None

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
