from unittest.mock import patch, AsyncMock
from tests.conftest import (
    register_and_login, auth_headers, create_trip, MOCK_AGENT_STATE_SUCCESS
)
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


