"""
Observability via LangChain BaseCallbackHandler.
Hooks into every LLM call and tool invocation automatically.
"""

import json
import logging
import time
from typing import Any, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from app.services.datadog_service import record_llm_call

_logger = logging.getLogger("agent.observability")
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


class AgentObservabilityHandler(BaseCallbackHandler):
    """Spy on every LLM call and tool invocation inside the LangGraph agent."""

    def __init__(self, trip_id: int, user_id: int, thread_id: str):
        self.trip_id = trip_id
        self.user_id = user_id
        self.thread_id = thread_id
        self._llm_start: float = 0
        self._model_name: str = "unknown"
        self._tool_starts: dict[str, float] = {}  # run_id -> start time

    # ── LLM hooks ────────────────────────────────────────────────────────────

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        self._llm_start = time.perf_counter()
        self._model_name = (
            serialized.get("name")
            or (serialized.get("id") or ["unknown"])[-1]
        )

    def on_llm_end(self, response: LLMResult, **kwargs):
        latency_ms = round((time.perf_counter() - self._llm_start) * 1000, 2)
        usage = {}
        if response.llm_output:
            usage = response.llm_output.get("usage", {})
        _logger.info(json.dumps({
            "event": "llm_call",
            "trip_id": self.trip_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "model": self._model_name,
            "latency_ms": latency_ms,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }))
        record_llm_call(
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            model=self._model_name,
            trip_id=self.trip_id,
        )

    def on_llm_error(self, error: BaseException, **kwargs):
        _logger.error(json.dumps({
            "event": "llm_error",
            "trip_id": self.trip_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "error": str(error),
        }))

    # ── Tool hooks ────────────────────────────────────────────────────────────

    def on_tool_start(self, serialized: dict, input_str: str, run_id: Any = None, **kwargs):
        self._tool_starts[str(run_id)] = time.perf_counter()
        _logger.info(json.dumps({
            "event": "tool_start",
            "tool": serialized.get("name"),
            "trip_id": self.trip_id,
            "thread_id": self.thread_id,
        }))

    def on_tool_end(self, output: str, run_id: Any = None, **kwargs):
        start = self._tool_starts.pop(str(run_id), None)
        latency_ms = round((time.perf_counter() - start) * 1000, 2) if start else None
        _logger.info(json.dumps({
            "event": "tool_end",
            "trip_id": self.trip_id,
            "thread_id": self.thread_id,
            "latency_ms": latency_ms,
        }))

    def on_tool_error(self, error: BaseException, run_id: Any = None, **kwargs):
        self._tool_starts.pop(str(run_id), None)
        _logger.error(json.dumps({
            "event": "tool_error",
            "trip_id": self.trip_id,
            "thread_id": self.thread_id,
            "error": str(error),
        }))
