# Parakh: Real or Fake? 🔍
An AI agent (Gemini + Google ADK) that scans a student's inbox for scholarship, internship and
admission emails, checks each one with real evidence, labels it in Gmail and adds genuine
deadlines to Google Calendar. Students can also check a single email with **zero inbox access**.

**Track:** Automating Boring Stuff · **GDG AI Agent-a-thon 2026, FAST CFD**

## What it checks
| Check | How |
|---|---|
| Sender | SPF / DKIM / DMARC from the email headers, Reply-To mismatch |
| Links | Real destination (redirects), Google Safe Browsing, domain age (RDAP), look-alike domains |
| Hidden links | `href` targets inside HTML, links inside **QR code images** (OpenCV) |
| Fees & pressure | "processing fee", "within 24 hours", JazzCash/Easypaisa to a personal number (English + Roman Urdu) |
| Official source | Searches the real organisation's website for the opportunity |
| Shared memory | Scam fingerprints (domains, links, senders) caught once are recognised for every student |

## How it works
- **Agent:** Google ADK `LlmAgent` on Gemini. It plans which checks each email needs, calls them, and adapts (e.g. skips other checks when shared memory already knows the link).
- **MCP servers:** `parakh-checks` (our own, exposes every check) and Gmail + Calendar (`workspace-mcp`).
- **Web app:** FastAPI + plain HTML/CSS/JS, with a live agent trace streamed to the page.

## Run locally
```bash
python -m venv .venv && .venv\Scripts\activate      # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                               # add your own keys, never commit .env
uvicorn server:app --reload                          # open http://127.0.0.1:8000
```
`PARAKH_MOCK=1` in `.env` shows labelled sample data; `PARAKH_MOCK=0` runs the real agent.

## Tests and evaluation
```bash
python -m pytest -q            # unit tests (checks, QR decoder, email parser, data contract)
python tests/eval_demo.py      # runs the demo emails through the agent, prints accuracy
```

## Team docs
- `CONTRACT.md`: who owns what, data shapes, rules
- `ROADMAP.md`: build plan and checkpoints

## Privacy
- Only opportunity emails (search filter) are opened. Gmail access is read + label only: no sending, no deleting.
- The student's name, email, phone and CNIC numbers are redacted before any text reaches Gemini.
- Only scam fingerprints are stored, never email content.
- Demo uses a dedicated demo inbox and sample emails only (`demo_emails/`).

## Honest limits
- Gmail is a restricted Google scope: until the app passes Google verification, only added test users can connect an inbox. **Check one email** works for everyone.
- Verdicts are evidence-based guidance, not a guarantee. Always confirm with the official source.

## Team
- Person 1 (Ella): web app, email parsing, fee/pressure + QR checks, evaluation, deployment
- Person 2: investigation checks, `parakh-checks` MCP server, shared memory
- Person 3: ADK agent, Gmail + Calendar MCP, integration
