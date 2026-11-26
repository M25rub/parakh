# Parakh: Build Roadmap (24 hours, 3 people)

## What "deployable" means
Your app must run **on the internet with a public link** that judges can open in their browser,
not just on your laptop. We package the app in a container (`Dockerfile`) and run it on
**Google Cloud Run**, which gives a URL like `https://parakh-xxxx.a.run.app`.
Backup if credits/billing fail: **Streamlit Community Cloud** (free, deploys from GitHub).

## Phase 0: Setup together (Hour 0–1, everyone)
1. Person 1 creates a GitHub repo `parakh`, uploads this starter, adds Persons 2 and 3 as collaborators.
2. Everyone: `git clone`, then:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env             # fill in your keys
   PARAKH_MOCK=1 pytest -q          # must show 4 passed
   PARAKH_MOCK=1 streamlit run app.py   # the mock app opens in the browser
   ```
3. Get keys: Gemini API key (aistudio.google.com), Safe Browsing API key (Cloud Console →
   APIs & Services → enable "Safe Browsing API" → Credentials → API key).
4. Create the demo Gmail account (e.g. parakh.demo@gmail.com). Share the password only in private.
5. Each person creates their branch: `git checkout -b p1-ui` / `p2-checks` / `p3-agent`.

## Phase 1: Build in parallel (Hour 1–8)
| Person 1: UI + deploy + demo + 2 checks | Person 2: Evidence checks + MCP server + memory | Person 3: Agent + Gmail/Calendar MCP |
|---|---|---|
| Polish the Streamlit UI against mock data (theme, cards, trace panel, deadlines) | `extract_links`, `redact`, `check_headers` | Run `adk web`, Gemini key working, agent calls a stub tool via parakh-checks MCP |
| `check_fee_pressure` (keywords/regex) | `check_domain_age` (RDAP) + `check_safe_browsing` | `submit_verdict` working + `_run_agent` in service.py |
| `decode_qr` (OpenCV) + make the QR demo poster | `check_link_destination` + `check_lookalike` | Connect workspace-mcp; print its tool names; search the demo inbox |
| First Cloud Run deploy of the MOCK app + send the 5 demo emails | Test `python -m parakh.mcp_server`; memory local JSON | official_source_agent (google_search via AgentTool) |

### ✅ Checkpoint 1 (Hour 4): 15-minute call
Persons 1 & 2 merge real `fee_pressure`, `headers`, `extract_links`. Person 3 confirms the agent
can call them through the MCP server. Person 1 shows the mock UI live on the deployed URL.

### ✅ Checkpoint 2 (Hour 8): first real end-to-end run
Person 3 implements `_run_agent` in `service.py`. Run with `PARAKH_MOCK=0`:
one demo email → agent → checks → Verdict → shows in UI. Fix whatever breaks together.

## Phase 2: Complete the loop (Hour 8–14)
- Person 3: Gmail labels + Calendar event via MCP, memory hit skips checks, failure handling.
- Person 2: harden every check (timeouts 5s, `unverified` on any error), unit tests,
  Firestore memory backend, help Person 3 debug tool calls.
- Person 1: connect the UI trace to real `TraceEvent`s, test all 5 demo emails, deploy real version.

### ✅ Checkpoint 3 (Hour 14): full demo run on the DEPLOYED link. Then sleep in shifts (Hour 14–17).

## Phase 3: Finish (Hour 17–23). No new features after Hour 20.
- Person 1: final deploy, README (setup + run + demo login instructions), record the 3–5 min video.
- Person 2: code clean-up, comments, unit tests green.
- Person 3: prompt tuning, failure handling (missing headers → ask/unverified), architecture diagram.
- Everyone: rehearse the demo 5 times. Record a backup video in case the live demo fails.

## Final submission checklist
- [ ] GitHub repo link (code + README with setup/run steps, no keys inside)
- [ ] Deployed link (works in an incognito window) + demo access instructions
- [ ] 3–5 min demo video: one real task from "Scan" to labels + calendar event
- [ ] Incomplete features clearly marked as "future" (WhatsApp, LinkedIn, etc.)

## Deploy to Cloud Run (Person 1)
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud run deploy parakh --source . --region asia-south1 --allow-unauthenticated \
  --set-env-vars PARAKH_MOCK=0,GEMINI_MODEL=gemini-flash-latest \
  --set-secrets GOOGLE_API_KEY=gemini-key:latest,SAFE_BROWSING_API_KEY=sb-key:latest
```
Keep min instances at 0 (default) so it costs nothing when idle. Set a budget alert.
⚠️ Our event credit showed an expiry of Nov 27, 12:40 AM. Confirm with organisers; if billing
stops, use Streamlit Community Cloud as backup.
