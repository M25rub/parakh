# Parakh: Integration Contract (read before writing any code)

This file is why our three parts will not break when combined. Follow it exactly.

## 1. File ownership (only edit YOUR files)
| Person | Owns | Never edit |
|---|---|---|
| **Person 1: UI, deploy, demo + text/QR checks** | `server.py`, `web/`, `parakh/mock_data.py`, `parakh/checks/content.py` (fee_pressure), `parakh/checks/qr.py` (decode_qr), `parakh/parse_email.py`, `tests/eval_demo.py`, `Dockerfile`, `demo_emails/`, `README.md`, the demo video | `parakh/agent.py`, `parakh/service.py`, other check files |
| **Person 2: Evidence checks + parakh-checks MCP server + memory** | `parakh/checks/headers.py`, `parakh/checks/links.py`, `parakh/checks/privacy.py`, `parakh/mcp_server.py`, `parakh/memory.py` | `server.py`, `web/`, `parakh/agent.py`, `parakh/service.py` |
| **Person 3: Agent, Gmail/Calendar MCP, integration** | `parakh/agent.py`, `parakh/service.py` (real branch) | `server.py`, `web/`, `parakh/checks/*`, `parakh/memory.py` |
| **Shared (change only after all 3 agree)** | `parakh/schemas.py`, `requirements.txt`, `CONTRACT.md`, `tests/test_contract.py` | |

## 2. The data shapes (`parakh/schemas.py`)
- Every check returns **`CheckResult`** `{check, status, summary, evidence}`.
  `status` is one of `pass | warn | fail | unverified | skipped`.
  If a check cannot run (no API key, timeout, missing data) return `unverified`. **Never guess, never crash.**
- The agent's final answer per email is a **`Verdict`**.
- Live steps for the UI are **`TraceEvent`**s.
- The UI receives a **`ScanResult`** `{verdicts, trace, emails_scanned, mock}`.

Schema rule: you may ADD a field with a default value. Never rename or delete a field.

## 3. The two integration functions (`parakh/service.py`)
```python
scan_inbox(max_emails: int = 10, on_event=None) -> ScanResult
check_email(email: EmailInput, on_event=None) -> ScanResult
```
- The UI calls ONLY these. `on_event(TraceEvent)` is called live for each step.
- `PARAKH_MOCK=1` makes both return fake data, so Person 1 can build the UI on day one.

## 4. Check function signatures (Persons 1 & 2 implement, Person 3 calls via MCP)
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
`parakh/mcp_server.py` exposes the same functions as MCP tools with the SAME names.

## 5. Gmail labels (exact strings)
`Parakh/Verified`, `Parakh/Suspicious`, `Parakh/Likely scam`

## 6. Git rules
1. Each person works on their own branch: `p1-ui`, `p2-checks`, `p3-agent`.
2. Before pushing: `PARAKH_MOCK=1 pytest -q` must pass.
3. Merge into `main` only at the checkpoints in ROADMAP.md, one person at a time.
4. Never commit `.env`, API keys, `client_secret*.json` or OAuth tokens.
5. If you need a schema change, message the group first.
