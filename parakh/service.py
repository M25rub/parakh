"""
OWNER: Person 3 (real branch). THE INTEGRATION POINT between the agent and the UI.
Person 1's UI calls ONLY these two functions. Their signatures must never change.

PARAKH_MOCK=1 -> returns fake demo data from mock_data.py (so the UI can be built first).
"""
import asyncio
import json
import logging
import os
import time
from typing import Callable, Optional

from dotenv import load_dotenv

from .schemas import EmailInput, ScanResult, TraceEvent

load_dotenv()  # so Streamlit and plain scripts also see GOOGLE_API_KEY

# ADK prints giant tracebacks for errors we already handle and report ourselves.
# Set PARAKH_DEBUG=1 to see them again.
if os.getenv("PARAKH_DEBUG", "0") != "1":
    logging.getLogger("google_adk").setLevel(logging.CRITICAL)

OnEvent = Optional[Callable[[TraceEvent], None]]

# Tools served by our own parakh-checks MCP server (same names as in the contract).
CHECK_TOOLS = {"check_headers", "extract_links", "check_link_destination",
               "check_safe_browsing", "check_domain_age", "check_lookalike",
               "decode_qr", "check_fee_pressure", "redact"}


def _via_mcp(tool: str) -> Optional[str]:
    """Which MCP server a tool belongs to (None = a local tool). The UI highlights these.
    TODO: once workspace-mcp is connected (step 4), replace the guesses below with the
    real Gmail / Calendar tool names."""
    t = (tool or "").lower()
    if tool in CHECK_TOOLS:
        return "parakh-checks"
    if "event" in t or "calendar" in t:
        return "calendar"
    if "gmail" in t or "label" in t or "message" in t or "thread" in t:
        return "gmail"
    return None


def _result_text(resp) -> str:
    """MCP wraps results as {'content': [{'text': '<json>'}]}. Show 'status: summary' instead."""
    r = getattr(resp, "response", None)
    try:
        if isinstance(r, dict) and r.get("content"):
            txt = r["content"][0].get("text", "")
            d = json.loads(txt)
            if isinstance(d, dict) and "status" in d:
                return f"{d.get('status')}: {d.get('summary', '')}"[:200]
            return txt[:200]
    except Exception:  # noqa: BLE001
        pass
    return str(r)[:200]


def _friendly(e: Exception) -> str:
    """One readable line instead of a wall of text."""
    s = str(e)
    if "429" in s or "RESOURCE_EXHAUSTED" in s:
        return ("Gemini quota exceeded (429): free-tier limit reached. "
                "Wait a minute, or check aistudio.google.com/rate-limit")
    if "503" in s or "UNAVAILABLE" in s:
        return "Gemini is overloaded (503), usually temporary"
    return (s.strip() or type(e).__name__)[:200]


def is_mock() -> bool:
    return os.getenv("PARAKH_MOCK", "0") == "1"


def scan_inbox(max_emails: int = 10, on_event: OnEvent = None) -> ScanResult:
    """Scan the connected Gmail inbox for opportunity emails and verify each one.
    on_event(TraceEvent) is called live for every step so the UI can show the trace."""
    if is_mock():
        from .mock_data import mock_scan
        return mock_scan(on_event)
    return _run_agent(f"Scan the inbox. Check at most {max_emails} opportunity emails.",
                      on_event, use_gmail=True, timeout=300)


def check_email(email: EmailInput, on_event: OnEvent = None) -> ScanResult:
    """Forward mode: verify ONE pasted/forwarded email without touching any inbox."""
    if is_mock():
        from .mock_data import mock_single
        return mock_single(email, on_event)
    # Privacy: hide the student's own email, phone, CNIC and card numbers before Gemini sees them.
    # Person 2's redact() keeps payment/wallet numbers ("send fee to JazzCash 03xx") as evidence.
    from .checks.privacy import redact
    body = redact(email.body_text or "", student_email=os.getenv("USER_GOOGLE_EMAIL", ""))
    email = email.model_copy(update={"body_text": body})
    prompt = ("Investigate this ONE email (do not use Gmail search, do not apply labels):\n"
              + email.model_dump_json())
    return _run_agent(prompt, on_event, use_gmail=False, timeout=120)


async def _run_agent_async(prompt: str, emit, use_gmail: bool, model=None) -> None:
    """Runs the ADK agent once and reports every step through emit()."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from .agent import COLLECTED_VERDICTS, build_agent

    COLLECTED_VERDICTS.clear()
    session_service = InMemorySessionService()
    runner = Runner(agent=build_agent(use_gmail=use_gmail, model=model),
                    app_name="parakh", session_service=session_service)
    session = await session_service.create_session(app_name="parakh", user_id="student")
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    emit("info", "Parakh agent started" + (f" (model: {model})" if model else ""))
    async for event in runner.run_async(user_id="student", session_id=session.id,
                                        new_message=msg):
        for call in event.get_function_calls() or []:
            via = _via_mcp(call.name)
            emit("mcp_call" if via else "tool_call",
                 f"Calling {call.name} {str(dict(call.args or {}))[:200]}", call.name, via)
        for resp in event.get_function_responses() or []:
            emit("tool_result", f"{resp.name} -> {_result_text(resp)}",
                 resp.name, _via_mcp(resp.name))
        if event.is_final_response() and event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts).strip()
            if text:
                emit("decision", text[:500])


def _run_agent(prompt: str, on_event: OnEvent, use_gmail: bool, timeout: int = 120) -> ScanResult:
    """Always returns a ScanResult, even if the agent fails. The UI must never crash."""
    trace: list[TraceEvent] = []

    def emit(kind, message, tool=None, via=None):
        ev = TraceEvent(kind=kind, message=message, tool=tool, via_mcp=via)
        trace.append(ev)
        if on_event:
            try:
                on_event(ev)
            except Exception:  # noqa: BLE001  a UI callback bug must not kill the run
                pass

    # Attempt 1: normal model. Attempts 2-3: the backup model. Each model has its own quota,
    # so switching models is the fastest way past a 429.
    fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest")
    models = [None, fallback, fallback]
    for attempt, model in enumerate(models, start=1):
        try:
            asyncio.run(asyncio.wait_for(
                _run_agent_async(prompt, emit, use_gmail, model), timeout=timeout))
            break
        except asyncio.TimeoutError:
            emit("error", f"Agent timed out after {timeout} seconds")
            break
        except Exception as e:  # noqa: BLE001
            s = str(e)
            quota = "429" in s or "RESOURCE_EXHAUSTED" in s
            busy = "503" in s or "UNAVAILABLE" in s
            emit("error", f"Attempt {attempt} failed: {_friendly(e)}")
            if not (quota or busy) or attempt == len(models):
                break
            switching = models[attempt] != model
            wait = 2 if switching else (20 if quota else 3 * attempt)
            emit("info", f"Retrying in {wait}s"
                 + (f" with backup model {models[attempt]}" if switching else ""))
            time.sleep(wait)

    verdicts = []
    try:
        from .agent import COLLECTED_VERDICTS
        verdicts = list(COLLECTED_VERDICTS)
    except Exception as e:  # noqa: BLE001
        emit("error", f"Could not read verdicts: {e}")

    return ScanResult(verdicts=verdicts, trace=trace,
                      emails_scanned=len(verdicts), mock=False)