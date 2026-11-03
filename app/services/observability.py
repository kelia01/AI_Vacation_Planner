"""
Structured observability for agent calls.
Logs latency, token usage, model, errors, and request context as JSON.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

_logger = logging.getLogger("agent.observability")

if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    
@dataclass
class AgentCallRecord:
    trip_id: int
    user_id: int
    thread_id: str
    model: str = "claude-haiku-4-5"
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None 
    tool_calls_made: int = 0
    success: bool = True
    error: Optional[str] = None
    approval_state: Optional[str] = None
    extra: dict = field(default_factory=dict)
    
def log_record(record: AgentCallRecord) -> None:
    _logger.info(json.dumps({"event": "agent_call", **asdict(record)}))
    
class AgentTimer:
    def __init__(self):
        self.latency_ms: Optional[float] = None
        
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *_):
        self.latency_ms = (time.perf_counter() - self.start) * 1000
        
        
def extract_token_usage(state: dict) -> tuple[Optional[int], Optional[int]]:
    """
    Pull token counts from the last AIMessage in state["messages"].
    LangChain stores usage in message.usage_metadata as
    {"input_tokens": N, "output_tokens": N}.
    Returns (input_tokens, output_tokens) or (None, None) if unavailable.
    """
    messages = state.get("messages", [])
    for msg in reversed(messages):
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            return usage.get("input_tokens"), usage.get("output_tokens")
        return None, None
    
def count_tool_calls(state: dict) -> int:
        return sum(
            1 for msg in state.get("messages", [])
            if getattr(msg, "tool_calls", None)
        )