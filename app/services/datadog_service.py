"""
Datadog observability integration.
- ddtrace patches FastAPI + SQLAlchemy + requests automatically on init_datadog()
- record_metric() sends custom metrics via DogStatsD
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger("agent.datadog")

_datadog_enabled = False


def init_datadog() -> None:
    """Call once at application startup. No-ops gracefully if keys are missing."""
    global _datadog_enabled

    api_key = os.getenv("DD_API_KEY")
    if not api_key:
        _logger.info("DD_API_KEY not set — Datadog integration disabled")
        return

    try:
        import ddtrace
        from ddtrace import patch_all, tracer

        ddtrace.config.env = os.getenv("DD_ENV", "production")
        ddtrace.config.service = os.getenv("DD_SERVICE", "ai-vacation-planner")
        ddtrace.config.version = os.getenv("DD_VERSION", "7.0.0")

        patch_all()

        _datadog_enabled = True
        _logger.info(
            "Datadog APM enabled — service=%s env=%s",
            ddtrace.config.service,
            ddtrace.config.env,
        )
    except ImportError:
        _logger.warning("ddtrace not installed — run: uv add ddtrace")
    except Exception as e:
        _logger.warning("Datadog init failed: %s", e)


def record_metric(metric: str, value: float, tags: list[str] | None = None) -> None:
    """Send a gauge metric to Datadog via DogStatsD. Silent no-op if disabled."""
    if not _datadog_enabled:
        return
    try:
        from datadog import statsd
        statsd.gauge(metric, value, tags=tags or [])
    except Exception:
        pass


def record_llm_call(
    latency_ms: float,
    input_tokens: int | None,
    output_tokens: int | None,
    model: str,
    trip_id: int,
) -> None:
    """Convenience wrapper — records LLM latency and token usage as Datadog metrics."""
    tags = [f"model:{model}", f"trip_id:{trip_id}"]
    record_metric("vacation_planner.llm.latency_ms", latency_ms, tags)
    if input_tokens is not None:
        record_metric("vacation_planner.llm.input_tokens", input_tokens, tags)
    if output_tokens is not None:
        record_metric("vacation_planner.llm.output_tokens", output_tokens, tags)


def record_agent_request(status: str, trip_id: int) -> None:
    """Increment agent request counter with status tag."""
    record_metric(
        "vacation_planner.agent.requests",
        1,
        tags=[f"status:{status}", f"trip_id:{trip_id}"],
    )


def record_evaluation(passed: bool, score: float, trip_id: int) -> None:
    """Record itinerary evaluation outcome."""
    record_metric(
        "vacation_planner.evaluation.score",
        score,
        tags=[f"passed:{passed}", f"trip_id:{trip_id}"],
    )
