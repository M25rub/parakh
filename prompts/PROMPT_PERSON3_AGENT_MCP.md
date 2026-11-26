# CONTEXT FOR YOUR AI ASSISTANT: read all of this before helping me

You are helping me build my part of a 3-person team project for the **GDG AI Agent-a-thon**
(FAST National University, Chiniot-Faisalabad campus). We have **24 hours**. Help me in
**small, testable baby steps**: give me one step, wait for me to confirm it works, then the next.
Explain briefly so I understand my own code (judges will ask us to explain it).

## The project: Parakh ("Real or Fake?")
An AI agent that protects students from fake scholarship, internship and admission offers.
Fake offers arrive as polite emails asking for "processing/registration fees" with tight
deadlines, lookalike senders, hidden links and payment QR codes. Spam filters miss them.

**User flow:** the student opens our web app, clicks **"Scan my inbox"**. The agent:
1. Searches Gmail (through a Gmail MCP server) ONLY for opportunity emails.
2. For each email, PLANS which checks it needs and runs them as tools: email headers
   (SPF/DKIM/DMARC, From vs Reply-To), link destination, Google Safe Browsing, domain age,
   lookalike domains, QR decoding, fee/pressure detection, official-source check, shared memory.
3. DECIDES a risk level (verified / suspicious / likely_scam) with evidence and confidence.
4. ACTS: applies a Gmail label, adds genuine deadlines to Google Calendar (Calendar MCP),
   saves scam fingerprints to shared memory.
5. Shows a live "agent trace" and result cards in the UI.
Second mode "Check one email": the student pastes an email; no inbox access.

## Competition rules we MUST satisfy
- Track: **Automating Boring Stuff**. Must use **Gemini / Google ADK** meaningfully.
- Must use **at least one MCP server** as a working part (we use two: our own `parakh-checks`
  server, and `workspace-mcp` for Gmail + Calendar). We must show which agent decisions
  lead to MCP calls.
- Must be a real agent (planning, dynamic tool choice, multi-step, adapts to failures), NOT a
  fixed pipeline or plain chatbot.
- Must be **deployed** (public URL on Google Cloud Run), with a GitHub repo + README + 3–5 min video.
- No API keys in the repo. Sample/demo data only. Never present mock-ups as working.

## Tech stack (do not change)
Python 3.11 · Google ADK (`google-adk`) · Gemini (`gemini-flash-latest`) · MCP (`mcp`, FastMCP)
· `workspace-mcp` (community Gmail/Calendar MCP server) · Streamlit UI · pydantic v2 ·
Firestore or local JSON for memory · Docker + Cloud Run.

## Privacy rules (built in, judges will ask)
- Only open emails matching the opportunity search. Never send or delete emails.
- Redact the STUDENT's data (name, email, CNIC, phone) before text reaches Gemini, but KEEP the
  sender's address, links, domains, fee amounts and wallet numbers (that's the evidence).
- Memory stores only scam fingerprints (domains, final URLs, sender addresses).

## THE CONTRACT (this is what keeps our 3 parts from breaking when combined)
We share a starter repo. The file `parakh/schemas.py` defines the shared data shapes.
**Do not rename or delete any field or function signature below. You may only add fields with
default values, and only after telling the team.** Only edit the files I own.

```python
class CheckStatus(str, Enum): PASS="pass"; WARN="warn"; FAIL="fail"; UNVERIFIED="unverified"; SKIPPED="skipped"
class CheckResult(BaseModel):   # returned by EVERY check
    check: str      # "headers"|"link_destination"|"safe_browsing"|"domain_age"|"lookalike"|"qr"|"fee_pressure"|"official_source"|"memory"
    status: CheckStatus
    summary: str    # one plain-English sentence for the UI
    evidence: dict = {}
class Risk(str, Enum): VERIFIED="verified"; SUSPICIOUS="suspicious"; LIKELY_SCAM="likely_scam"; NOT_OPPORTUNITY="not_opportunity"
GMAIL_LABELS = {VERIFIED: "Parakh/Verified", SUSPICIOUS: "Parakh/Suspicious", LIKELY_SCAM: "Parakh/Likely scam"}
class EmailInput(BaseModel): email_id; sender; reply_to=None; subject=""; body_text=""; raw_headers=""; links=[]; qr_images_b64=[]; received_at=None
class Deadline(BaseModel): title: str; date: str  # YYYY-MM-DD ; calendar_event_created: bool=False
class Verdict(BaseModel): email_id; subject; sender; risk: Risk; confidence: float (0-1); checks: list[CheckResult]=[]; explanation: str; deadline: Deadline|None=None; gmail_label_applied: str|None=None; memory_hit: bool=False
class TraceEvent(BaseModel): kind: "thinking"|"tool_call"|"tool_result"|"mcp_call"|"decision"|"error"|"info"; message: str; tool: str|None; via_mcp: "gmail"|"calendar"|"parakh-checks"|None; timestamp
class ScanResult(BaseModel): verdicts: list[Verdict]; trace: list[TraceEvent]; emails_scanned: int; mock: bool=False
```
Integration functions in `parakh/service.py` (the UI calls ONLY these):
```python
scan_inbox(max_emails: int = 10, on_event=None) -> ScanResult
check_email(email: EmailInput, on_event=None) -> ScanResult
# PARAKH_MOCK=1 env var -> both return fake data from parakh/mock_data.py
```
Check functions in `parakh/checks/` (Persons 1 & 2), exposed with the SAME names as MCP tools in
`parakh/mcp_server.py` (each MCP tool returns `CheckResult.model_dump(mode="json")`):
```python
check_headers(raw_headers: str, claimed_sender: str) -> CheckResult
extract_links(text: str) -> list[str]
check_link_destination(url: str) -> CheckResult
check_safe_browsing(url: str) -> CheckResult
check_domain_age(domain: str) -> CheckResult
check_lookalike(domain: str, claimed_org: str | None) -> CheckResult
decode_qr(image_b64: str) -> CheckResult
check_fee_pressure(text: str) -> CheckResult
redact(text: str, student_name: str = "", student_email: str = "") -> str
```
Golden rule: if a check or step cannot run (no key, timeout, missing data), return status
"unverified" with a clear summary. Never guess, never raise an exception to the caller.

## Team and file ownership
- **Person 1 (Ella): UI + deployment + demo + 2 checks.** Owns `app.py`, `parakh/mock_data.py`, `parakh/checks/content.py` (check_fee_pressure), `parakh/checks/qr.py` (decode_qr), `Dockerfile`, `.streamlit/`, `demo_emails/`, `README.md`.
- **Person 2: evidence checks + parakh-checks MCP server + memory.** Owns `parakh/checks/headers.py`, `parakh/checks/links.py`, `parakh/checks/privacy.py`, `parakh/mcp_server.py`, `parakh/memory.py`.
- **Person 3: ADK agent + Gmail/Calendar MCP + integration.** Owns `parakh/agent.py`, `parakh/service.py`.
- Shared (only change after all agree): `parakh/schemas.py`, `requirements.txt`, `tests/test_contract.py`.

## Git rules
Work on your own branch (`p1-ui` / `p2-checks` / `p3-agent`). Run `PARAKH_MOCK=1 pytest -q`
before every push. Merge to `main` only at team checkpoints (hours 4, 8, 14). Never commit `.env`,
keys or OAuth token files.

---
# MY ROLE: Person 3: ADK agent, Gmail/Calendar MCP, service integration
## My goal
Make the agent truly agentic: it searches the inbox via Gmail MCP, plans checks per email,
calls the parakh-checks MCP tools, decides a verdict, labels the email, creates calendar events
via Calendar MCP, uses the shared memory (built by Person 2), and returns results through `service.py` without ever
crashing the UI. `parakh/agent.py` already contains the architecture and the instruction prompt.

## My baby steps
1. Put the Gemini key in `.env`. Run `adk web` from the repo root with `USE_GMAIL_MCP=0` and chat
   with the agent. Confirm it calls a stub check tool from the parakh-checks MCP server.
2. Confirm `submit_verdict` works: ask the agent to check a pasted email; it must call
   submit_verdict with valid JSON (it gets the error back and retries if invalid).
3. Implement `_run_agent` in `service.py` (Runner + InMemorySessionService + run_async),
   turning ADK events into `TraceEvent`s (function calls → tool_call/mcp_call, responses →
   tool_result) and calling `on_event`. Test `check_email` end to end with PARAKH_MOCK=0.
4. Set up workspace-mcp for Gmail + Calendar with the DEMO account: create OAuth credentials,
   follow its README, and first just PRINT the list of tool names the agent receives.
5. Update the instruction prompt with the real Gmail tool names (search, read, add label,
   create label if missing) and the Calendar create-event tool.
6. Make inbox scan work on the 5 demo emails: labels applied, calendar event created.
7. Memory tools in the agent: memory_lookup first; on a hit skip other checks
   (memory_hit=true); memory_save after suspicious/likely_scam (fingerprints only).
   (Person 2 builds memory.py; you only call it.)
8. official_source_agent (google_search wrapped in AgentTool): verify it works; check the
   current ADK docs about combining built-in tools with other tools.
9. Failure handling: missing headers → "unverified" + lower confidence; any tool error →
   continue with the other checks; always submit a verdict.
10. Prepare a 1-slide architecture diagram and be ready to explain why this is an agent.
## Rules for me
Never change `scan_inbox` / `check_email` signatures. Always return a `ScanResult`, even on
errors (add a TraceEvent of kind "error"). Never send or delete emails. Never store student data.
