"""
OWNER: Person 3. The ADK agent: Gemini + tools + MCP servers.

Architecture:
  root agent "parakh" (LlmAgent, Gemini)
    ├─ McpToolset -> "parakh-checks" (our own MCP server, Person 2)
    ├─ McpToolset -> Gmail + Calendar (workspace-mcp, community server)
    ├─ AgentTool  -> "official_source_agent" (sub-agent with the built-in google_search tool)
    ├─ function tool: memory_lookup / memory_save
    └─ function tool: submit_verdict  (the ONLY way a verdict reaches the UI)

Why submit_verdict instead of output_schema: in ADK, an agent with output_schema cannot
use tools. A submit_verdict tool validates with pydantic and returns errors to Gemini so it
can fix and retry (this is also our "handles failures" story).

Why a sub-agent for search: ADK's built-in google_search tool may not be combinable with
other tools in the same agent. Check the current ADK docs; wrapping it in AgentTool avoids it.
"""
import os
import sys

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from . import memory
from .schemas import Verdict

MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# The ONLY Gmail/Calendar tools the agent may use. No send, draft, delete, filters or
# out-of-office: Parakh can read opportunity emails, label them and add calendar events.
ALLOWED_WORKSPACE_TOOLS = [
    "search_gmail_messages", "get_gmail_message_content", "get_gmail_messages_content_batch",
    "get_gmail_attachment_content", "list_gmail_labels", "manage_gmail_label",
    "modify_gmail_message_labels", "batch_modify_gmail_message_labels",
    "list_calendars", "get_events", "manage_event",
]

# Verdicts collected during one run. service.py reads and clears this.
COLLECTED_VERDICTS: list[Verdict] = []


def submit_verdict(verdict_json: str) -> dict:
    """Submit the final verdict for ONE email as a JSON string matching the Verdict schema.
    Returns {"ok": true} or {"ok": false, "error": "..."} so you can fix and resubmit."""
    try:
        v = Verdict.model_validate_json(verdict_json)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    COLLECTED_VERDICTS.append(v)
    return {"ok": True}


def memory_lookup(indicators: list[str]) -> dict:
    """Check shared scam memory for domains, final URLs or sender addresses.
    Returns {"hit": false} or {"hit": true, "record": {...}}."""
    rec = memory.lookup(indicators)
    return {"hit": bool(rec), "record": rec}


def memory_save(indicators: list[str], risk: str, summary: str) -> dict:
    """Save scam fingerprints (domains, URLs, sender addresses) after a suspicious/scam verdict.
    NEVER pass student names, emails or phone numbers."""
    memory.save(indicators, risk, summary)
    return {"ok": True}


def make_official_source_agent(model: str) -> LlmAgent:
    """Built per model so that when service.py switches to the backup model (after a 429/503),
    the sub-agent switches too. Before, it was stuck on the exhausted model."""
    return LlmAgent(
        model=model,
        name="official_source_agent",
        description="Finds the official page of a scholarship, internship or organisation and "
                    "reports whether it charges a fee, its real deadline and its official domain.",
        instruction="Search for the OFFICIAL website of the program named in the request. "
                    "Reply in JSON: {official_url, official_domain, charges_fee (true/false/unknown), "
                    "official_deadline, contradictions: [..]}. If you cannot find it, say unknown. "
                    "Never guess.",
        tools=[google_search],
    )


def checks_mcp() -> McpToolset:
    return McpToolset(connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(command=sys.executable,
                                            args=["-m", "parakh.mcp_server"]),
        timeout=30))


def workspace_mcp() -> McpToolset:
    """
    TODO(Person 3): community Google Workspace MCP server (Gmail + Calendar).
    Read its README for the exact launch args and env vars (OAuth client id/secret,
    USER_GOOGLE_EMAIL). First baby step: connect and PRINT the list of tool names.
    """
    # The default start-up timeout is 5 seconds. uvx may need much longer the first time
    # (it downloads workspace-mcp), so we allow 120 s. Run `uvx workspace-mcp --help` once
    # beforehand to cache it.
    return McpToolset(connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uvx", args=["workspace-mcp", "--tools", "gmail", "calendar"],
            env={**os.environ}),
        timeout=120),
        tool_filter=ALLOWED_WORKSPACE_TOOLS)


INSTRUCTION = """
You are Parakh, an agent that protects students from fake scholarship, internship and
admission offers. You investigate with tools and evidence. You never guess.

For an INBOX SCAN:
1. Use the Gmail MCP search tool with the query:
   (scholarship OR internship OR admission OR "offer letter" OR fellowship) newer_than:30d
   Only open emails returned by this search. Never read other emails.
2. For EACH opportunity email, plan which checks it needs:
   - always: memory_lookup on the sender domain and link domains (if hit, skip other checks
     and reuse the stored verdict, set memory_hit=true)
   - headers present -> check_headers
   - links present -> check_link_destination, then check_safe_browsing, check_domain_age,
     check_lookalike on the FINAL domain
   - image/QR attachment -> decode_qr, then link checks on decoded URLs
   - always -> check_fee_pressure
   - it names a real program AND the other evidence is not already conclusive
     -> official_source_agent (it is slow and uses extra quota, so skip it when the
     checks already show a clear scam)
3. Decide risk: likely_scam / suspicious / verified / not_opportunity, with confidence.
   Checks with status "unverified" LOWER confidence; never treat them as pass or fail.
4. Act:
   - apply the Gmail label for the risk ("Parakh/Verified", "Parakh/Suspicious",
     "Parakh/Likely scam") via the Gmail MCP
   - verified + a deadline -> create a Google Calendar event via the Calendar MCP
   - suspicious/likely_scam -> memory_save with the scam domains/URLs/sender address only
5. Call submit_verdict once per email. If it returns an error, fix the JSON and resubmit.

EFFICIENCY (the API has a small request quota): call all independent checks together in
the SAME step instead of one at a time, keep explanations short, and stop right after
submit_verdict. Do not repeat a tool call that already returned a result.

Never send or delete emails. Never include the student's personal data in memory.
"""


def build_agent(use_gmail: bool = True, model: str | None = None) -> LlmAgent:
    """model lets service.py switch to a backup model when Gemini is overloaded or out of quota."""
    m = model or MODEL
    tools = [checks_mcp(), AgentTool(agent=make_official_source_agent(m)),
             memory_lookup, memory_save, submit_verdict]
    if use_gmail:
        tools.insert(1, workspace_mcp())
    return LlmAgent(model=m, name="parakh", instruction=INSTRUCTION, tools=tools)


# `adk web` looks for root_agent. Gmail stays OFF unless USE_GMAIL_MCP=1 is set explicitly.
root_agent = build_agent(use_gmail=os.getenv("USE_GMAIL_MCP", "0") == "1")