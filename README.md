# Parakh: Real or Fake? 🔍
An AI agent (Gemini + Google ADK) that scans a student's inbox for scholarship, internship and
admission emails, verifies each one with real evidence (email authentication, Google Safe
Browsing, domain age, QR decoding, official sources, shared scam memory), labels them in Gmail
and adds genuine deadlines to Google Calendar.

Track: **Automating Boring Stuff** · MCP servers: **parakh-checks** (our own) and **Gmail + Calendar** (workspace-mcp)

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env          # add your keys
PARAKH_MOCK=1 streamlit run app.py   # demo data
PARAKH_MOCK=0 streamlit run app.py   # real agent
```
## Tests
`PARAKH_MOCK=1 pytest -q`

## Team docs
- `CONTRACT.md`: who owns what, data shapes, rules (read first!)
- `ROADMAP.md`: build plan and checkpoints
- `prompts/`: context prompts for each teammate's AI assistant

## Privacy
Only opportunity emails matching the search are opened. No sending or deleting. Student
details are redacted before Gemini sees anything. Only scam fingerprints (domains, URLs,
sender addresses) are stored. Demo uses a dedicated demo inbox with sample emails only.
