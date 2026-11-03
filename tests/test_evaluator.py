import pytest
from app.services.evaluator import evaluate_itinerary, EvaluationResult

TRIP = {"destination": "Paris", "days": 2, "budget": 1000, "trip_style": "cultural"}

GOOD_ITINERARY = {
    "metadata": {"destination": "Paris", "duration_days": 2, "total_estimated_cost": 900},
    "days": [
        {"day_number": 1, "activities": [{"name": "Eiffel Tower"}, {"name": "Louvre"}]},
        {"day_number": 2, "activities": [{"name": "Versailles"}]},
    ],
}


def test_evaluate_returns_result():
    result = evaluate_itinerary(GOOD_ITINERARY, TRIP)
    assert isinstance(result, EvaluationResult)


def test_deterministic_checks_pass_for_valid_itinerary():
    result = evaluate_itinerary(GOOD_ITINERARY, TRIP)
    det_checks = [c for c in result.checks if c.name != "llm_relevance"]
    assert all(c.passed for c in det_checks)


def test_wrong_destination_fails():
    bad = {**GOOD_ITINERARY, "metadata": {**GOOD_ITINERARY["metadata"], "destination": "Tokyo"}}
    result = evaluate_itinerary(bad, TRIP)
    assert not result.passed
    dest_check = next(c for c in result.checks if c.name == "destination_match")
    assert not dest_check.passed


def test_wrong_day_count_fails():
    bad = {**GOOD_ITINERARY, "days": GOOD_ITINERARY["days"][:1]}
    result = evaluate_itinerary(bad, TRIP)
    assert not result.passed
    day_check = next(c for c in result.checks if c.name == "day_completeness")
    assert not day_check.passed


def test_budget_exceeded_fails():
    bad = {**GOOD_ITINERARY, "metadata": {**GOOD_ITINERARY["metadata"], "total_estimated_cost": 1200}}
    result = evaluate_itinerary(bad, TRIP)
    assert not result.passed
    budget_check = next(c for c in result.checks if c.name == "budget_adherence")
    assert not budget_check.passed


def test_score_between_0_and_1():
    result = evaluate_itinerary(GOOD_ITINERARY, TRIP)
    assert 0.0 <= result.score <= 1.0
