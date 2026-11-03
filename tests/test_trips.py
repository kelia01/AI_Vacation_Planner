from unittest.mock import patch, AsyncMock
from tests.conftest import (
    register_and_login, auth_headers, create_trip, MOCK_AGENT_STATE_SUCCESS
)

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

