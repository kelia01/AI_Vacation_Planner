import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


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

