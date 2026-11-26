"""
OWNER: Person 3 (real branch). THE INTEGRATION POINT between the agent and the UI.
Person 1's UI calls ONLY these two functions. Their signatures must never change.

PARAKH_MOCK=1 -> returns fake demo data from mock_data.py (so the UI can be built first).
"""
import os
from typing import Callable, Optional

from .schemas import EmailInput, ScanResult, TraceEvent

OnEvent = Optional[Callable[[TraceEvent], None]]


def is_mock() -> bool:
    return os.getenv("PARAKH_MOCK", "0") == "1"


def scan_inbox(max_emails: int = 10, on_event: OnEvent = None) -> ScanResult:
    """Scan the connected Gmail inbox for opportunity emails and verify each one.
    on_event(TraceEvent) is called live for every step so the UI can show the trace."""
    if is_mock():
        from .mock_data import mock_scan
        return mock_scan(on_event)
    return _run_agent(f"Scan the inbox. Check at most {max_emails} opportunity emails.",
                      on_event, use_gmail=True)


def check_email(email: EmailInput, on_event: OnEvent = None) -> ScanResult:
    """Forward mode: verify ONE pasted/forwarded email without touching any inbox."""
    if is_mock():
        from .mock_data import mock_single
        return mock_single(email, on_event)
    prompt = ("Investigate this ONE email (do not use Gmail search, do not apply labels):\n"
              + email.model_dump_json())
    return _run_agent(prompt, on_event, use_gmail=False)


def _run_agent(prompt: str, on_event: OnEvent, use_gmail: bool) -> ScanResult:
    """
    TODO(Person 3): run the ADK agent and stream events.
      import asyncio
      from google.adk.runners import Runner
      from google.adk.sessions import InMemorySessionService
      from google.genai import types
      from .agent import build_agent, COLLECTED_VERDICTS
    - COLLECTED_VERDICTS.clear()
    - runner.run_async(user_id=..., session_id=..., new_message=types.Content(role="user",
      parts=[types.Part(text=prompt)]))
    - for each event: event.get_function_calls() -> TraceEvent(kind="tool_call" or "mcp_call",
      tool=name, via_mcp=...), event.get_function_responses() -> kind="tool_result".
      Call on_event(trace_event) AND append it to a list.
    - return ScanResult(verdicts=list(COLLECTED_VERDICTS), trace=trace,
                        emails_scanned=len(COLLECTED_VERDICTS), mock=False)
    - Wrap everything in try/except: on error emit TraceEvent(kind="error") and return what
      you have. The UI must never crash.
    """
    raise NotImplementedError("Real agent run not wired yet. Use PARAKH_MOCK=1 for now.")
