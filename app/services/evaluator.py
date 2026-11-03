"""
Itinerary evaluator: deterministic checks first, LLM relevance check only if all pass.
"""

from dataclasses import dataclass, field
from typing import Optional
from langchain.chat_models import init_chat_model

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

_llm = init_chat_model("claude-haiku-4-5", model_provider="anthropic")


@dataclass
class CheckResult:
    name: str
    passed: bool
    reason: str


@dataclass
class EvaluationResult:
    passed: bool
    score: float
    checks: list[CheckResult] = field(default_factory=list)
    failure_summary: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "checks": [{"name": c.name, "passed": c.passed, "reason": c.reason} for c in self.checks],
            "failure_summary": self.failure_summary,
        }

def _deterministic_checks(itinerary: dict, trip: dict) -> list[CheckResult]:
    checks = []
    meta = itinerary.get("metadata") or {}
    
    # destination match check
    itinerary_dest = (meta.get("destination") or "").strip().lower()
    trip_dest = (trip.get("destination") or "").strip().lower()
    dest_passed = bool(itinerary_dest) and (itinerary_dest in trip_dest or trip_dest in itinerary_dest)
    
    checks.append(CheckResult(
        name="destination_match",
        passed=dest_passed,
        reason="Destination matches" if dest_passed else f"'{itinerary_dest}' does not match trip destination '{trip_dest}'."
    ))
    
    # day completeness check
    days = itinerary.get("days") or []
    expected_days = trip.get("days", 0)
    empty_days = [d.get("day_number") for d in days if not d.get("activities")]
    days_passed = len(days) == expected_days and not empty_days
    
    checks.append(CheckResult(
        name="day_completeness",
        reason=f"All {len(days)} days present with activites" if days_passed 
        else f"Expected {expected_days} days, got {len(days)}." if len(days) != expected_days
        else f"Days {empty_days} have no activities"
    ))
    
    # budget adherence check
    budget = trip.get("budget") or 0
    total_cost = meta.get("total_estimated_cost") or 0
    budget_passed = budget == 0 or total_cost <= budget * 1.1
    
    checks.append(CheckResult(
        name="budget_adherence",
        passed=budget_passed,
        reason=f"Cost ${total_cost: .0f} within budget ${budget: .0f}" if budget_passed
        else f"Cost ${total_cost: .0f} exceeds  ${budget: .0f} by more than 10%" ,
    ))
    
    # format validity check
    format_errors = []
    if not meta.get("destination"):
        format_errors.append("metadata.destination is missing")
        
    if not isinstance(meta.get("duration_days"), (int, float)):
        format_errors.append("metadata.duration_days is missing or not a number")
        
    for i, day in enumerate(days):
        if not isinstance(day.get("day_number"), int):
            format_errors.append(f"days[{i}].day_number is missing")
            
            for j, act in enumerate(day.get("activities") or []):
                if not act.get("name"):
                    format_errors.append(f"days[{i}].activities[{j}].name missing")
                    
    checks.append(CheckResult(
        name="format_validity",
        passed= not format_errors,
        reason="Format valid." if not format_errors else";".join(format_errors),
    ))
    return checks

def _llm_relevance_checks(itinerary: dict, trip: dict) -> CheckResult:
    