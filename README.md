# Parakh: Real or Fake? 🔍
An AI agent (Gemini + Google ADK) that scans a student's inbox for scholarship, internship and
admission emails, checks each one with real evidence, labels it in Gmail and adds genuine
deadlines to Google Calendar. Students can also check a single email with **zero inbox access**.

**Track:** Automating Boring Stuff · **GDG AI Agent-a-thon 2026, FAST CFD**

**Live demo:** https://parakh-4opz.onrender.com (free server: the first visit can take ~50 s to wake up)
**Demo video:** _add link_  ·  **Accuracy on our demo emails:** see `python tests/eval_demo.py`

### Try it as a judge
1. Open the live link → **Check one email**.
2. Upload any file from [`demo_emails/`](demo_emails/) (e.g. `1_fake_scholarship.eml` or `2_qr_poster.eml`), or paste any email you received.
3. Watch the live agent trace and the verdict with its evidence.

**Inbox scan** (Gmail labels + Calendar deadlines) runs on our demo Gmail account and is shown in the video: Google only lets approved test accounts connect until the app is verified.

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
- **Agent:** Google ADK `LlmAgent` on Gemini (with an automatic backup model if Gemini is busy or out of quota). It plans which checks each email needs, calls them, and adapts (e.g. skips other checks when shared memory already knows the link).
- **MCP servers:** `parakh-checks` (our own, exposes every check) and Gmail + Calendar (`workspace-mcp`).
- **Web app:** FastAPI + plain HTML/CSS/JS, with a live agent trace streamed to the page.
- **Memory:** Firestore (shared scam fingerprints), with a local file fallback.
- **Hosting:** Docker on Render.

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

## Privacy
- Only opportunity emails (search filter) are opened.
- The agent is only given read, label and calendar tools: sending, drafting and deleting tools are blocked in code (`ALLOWED_WORKSPACE_TOOLS` in `parakh/agent.py`).
- In "Check one email", the student's email address, phone, CNIC and card numbers are removed before the text reaches Gemini. Payment/wallet numbers are kept because they are the evidence.
- Only scam fingerprints are stored, never email content.
- Demo uses a dedicated demo inbox and sample emails only (`demo_emails/`).

## Honest limits
- Gmail is a restricted Google scope: until the app passes Google verification, only added test users can connect an inbox. **Check one email** works for everyone.
- Verdicts are evidence-based guidance, not a guarantee. Always confirm with the official source.
- The free Gemini tier has small rate limits, so a scan checks at most 5 emails at a time.
- Future work: WhatsApp and LinkedIn messages, redaction for inbox-scan mode, per-user Gmail sign-in.

## Team
- Merub Awan: web app, email parsing, fee/pressure + QR checks, evaluation, deployment
- Kiran Shahid: investigation checks, `parakh-checks` MCP server, shared memory
- Sawera Khalid: ADK agent, Gmail + Calendar MCP, integration
