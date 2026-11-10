"""
DeepEval evaluation tests using the golden dataset.
Runs real LLM-based GEval checks via claude-haiku-4-5.
Requires ANTHROPIC_API_KEY in environment.

Run with:
    uv run deepeval test run tests/test_deepeval.py
or:
    uv run pytest tests/test_deepeval.py -v
"""

import json
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.models import AnthropicModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

from app.services.evaluator import evaluate_itinerary

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"

with open(GOLDEN_DATASET_PATH) as f:
    GOLDEN_DATASET = json.load(f)

model = AnthropicModel(model="claude-haiku-4-5")


def _build_days_summary(itinerary: dict) -> str:
    return "\n".join(
        f"Day {d['day_number']} ({d.get('theme', '')}): "
        + ", ".join(a["name"] for a in d.get("activities", []))
        for d in itinerary.get("days", [])
    )


def _relevance_metric(destination: str, trip_style: str) -> GEval:
    return GEval(
        name="Itinerary Relevance",
        criteria=(
            f"The itinerary activities are genuinely relevant to {destination} "
            f"and appropriate for a {trip_style} travel style. "
            "Activities should be specific to the destination, not generic."
        ),
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.5,
        model=model,
    )


def _completeness_metric(expected_days: int) -> GEval:
    return GEval(
        name="Itinerary Completeness",
        criteria=(
            f"The itinerary covers exactly {expected_days} days, "
            "each day has a clear theme and at least one meaningful activity with a name and description."
        ),
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.5,
        model=model,
    )


# ---------------------------------------------------------------------------
# Parametrised tests — one per golden dataset entry
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", [c for c in GOLDEN_DATASET if c["expected_pass"]], ids=[c["id"] for c in GOLDEN_DATASET if c["expected_pass"]])
def test_passing_itineraries(case):
    """All deterministic + LLM checks must pass for known-good itineraries."""
    itinerary = case["itinerary"]
    trip = case["trip"]

    # 1. Deterministic checks via our evaluator
    eval_result = evaluate_itinerary(itinerary, trip)
    det_checks = [c for c in eval_result.checks if c.name != "llm_relevance"]
    failed_det = [c for c in det_checks if not c.passed]
    assert not failed_det, f"Deterministic checks failed: {[c.reason for c in failed_det]}"

    # 2. DeepEval GEval — relevance
    days_summary = _build_days_summary(itinerary)
    test_case = LLMTestCase(
        input=f"{trip['destination']} {trip['trip_style']} trip, {trip['days']} days, budget ${trip['budget']}",
        actual_output=days_summary,
    )
    assert_test(test_case, [_relevance_metric(trip["destination"], trip["trip_style"])])


@pytest.mark.parametrize("case", [c for c in GOLDEN_DATASET if not c["expected_pass"]], ids=[c["id"] for c in GOLDEN_DATASET if not c["expected_pass"]])
def test_failing_itineraries_caught(case):
    """Known-bad itineraries must be caught by the evaluator."""
    eval_result = evaluate_itinerary(case["itinerary"], case["trip"])
    assert not eval_result.passed, (
        f"Expected itinerary '{case['id']}' to fail but it passed. "
        f"Checks: {[(c.name, c.passed, c.reason) for c in eval_result.checks]}"
    )
    expected_check = case.get("expected_failure_check")
    if expected_check and expected_check != "llm_relevance":
        failed_names = {c.name for c in eval_result.checks if not c.passed}
        assert expected_check in failed_names, (
            f"Expected check '{expected_check}' to fail, but failed checks were: {failed_names}"
        )


def test_irrelevant_activities_caught_by_geval():
    """The Kyoto irrelevant-activities case must fail the GEval relevance metric."""
    case = next(c for c in GOLDEN_DATASET if c["id"] == "irrelevant_activities_fail")
    itinerary = case["itinerary"]
    trip = case["trip"]

    days_summary = _build_days_summary(itinerary)
    metric = _relevance_metric(trip["destination"], trip["trip_style"])
    test_case = LLMTestCase(
        input=f"{trip['destination']} {trip['trip_style']} trip",
        actual_output=days_summary,
    )
    metric.measure(test_case)
    assert metric.score < metric.threshold, (
        f"Expected GEval to flag irrelevant activities but score was {metric.score:.2f}"
    )


def test_completeness_metric_passes_for_full_itinerary():
    """Completeness GEval passes for a well-formed multi-day itinerary."""
    case = next(c for c in GOLDEN_DATASET if c["id"] == "tokyo_cultural_pass")
    days_summary = _build_days_summary(case["itinerary"])
    test_case = LLMTestCase(
        input=f"Tokyo cultural trip, 3 days",
        actual_output=days_summary,
    )
    assert_test(test_case, [_completeness_metric(expected_days=3)])


def test_completeness_metric_fails_for_incomplete_itinerary():
    """Completeness GEval fails when days are missing."""
    case = next(c for c in GOLDEN_DATASET if c["id"] == "missing_days_fail")
    days_summary = _build_days_summary(case["itinerary"])
    test_case = LLMTestCase(
        input=f"Amsterdam cultural trip, 4 days",
        actual_output=days_summary,
    )
    metric = _completeness_metric(expected_days=4)
    metric.measure(test_case)
    assert metric.score < metric.threshold, (
        f"Expected completeness to fail for 2/4 days but score was {metric.score:.2f}"
    )
