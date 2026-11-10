from unittest.mock import patch, AsyncMock
from tests.conftest import (
    register_and_login, auth_headers, create_trip
)

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
