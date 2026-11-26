"""
OWNER: Person 1. Streamlit web app. Calls ONLY parakh.service.scan_inbox / check_email.
Run:  PARAKH_MOCK=1 streamlit run app.py
TODO(Person 1): custom theme (.streamlit/config.toml), nicer cards, logo, Google sign-in note.
"""
import streamlit as st

from parakh import service
from parakh.checks import extract_links
from parakh.schemas import EmailInput, Risk, TraceEvent

st.set_page_config(page_title="Parakh: Real or Fake?", page_icon="🔍", layout="wide")

BADGE = {Risk.LIKELY_SCAM: ("🔴", "Likely scam"), Risk.SUSPICIOUS: ("🟡", "Suspicious"),
         Risk.VERIFIED: ("🟢", "Verified"), Risk.NOT_OPPORTUNITY: ("⚪", "Not an opportunity")}
ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌", "unverified": "❔", "skipped": "⏭️"}

st.title("🔍 Parakh: Real or Fake?")
st.caption("Verifies scholarship and internship emails with real evidence.")
if service.is_mock():
    st.warning("MOCK DATA: demo mode. Results below are sample data, not a live scan.")

mode = st.radio("Mode", ["⚡ Scan my inbox", "🔒 Check one email (no inbox access)"],
                horizontal=True)


def render(result):
    st.subheader(f"Results: {result.emails_scanned} email(s)")
    for v in result.verdicts:
        icon, label = BADGE[v.risk]
        with st.container(border=True):
            st.markdown(f"### {icon} {label} · {int(v.confidence * 100)}%")
            st.markdown(f"**{v.subject}**  \nFrom: `{v.sender}`")
            if v.memory_hit:
                st.info("⚡ Recognised from shared scam memory")
            st.write(v.explanation)
            if v.deadline:
                st.success(f"📅 {v.deadline.title}: {v.deadline.date}"
                           + (" (added to Google Calendar)" if v.deadline.calendar_event_created
                              else ""))
            with st.expander("Evidence"):
                for c in v.checks:
                    st.markdown(f"{ICON[c.status.value]} **{c.check}**: {c.summary}")


def run_with_trace(fn, *args):
    box = st.status("Parakh is investigating…", expanded=True)

    def on_event(ev: TraceEvent):
        tag = f"[{ev.via_mcp} MCP] " if ev.via_mcp else ""
        box.write(f"{tag}{ev.tool or ev.kind}: {ev.message}")

    try:
        result = fn(*args, on_event=on_event)
        box.update(label="Investigation complete", state="complete")
        render(result)
    except Exception as e:  # never crash the demo
        box.update(label="Something went wrong", state="error")
        st.error(f"Error: {e}")


if mode.startswith("⚡"):
    if st.button("Scan my inbox", type="primary"):
        run_with_trace(service.scan_inbox, 10)
else:
    sender = st.text_input("Sender email")
    subject = st.text_input("Subject")
    body = st.text_area("Email text", height=180)
    headers = st.text_area("Original headers (Gmail → ⋮ → Show original) — optional")
    if st.button("Check this email", type="primary"):
        email = EmailInput(email_id="pasted-1", sender=sender, subject=subject,
                           body_text=body, raw_headers=headers, links=extract_links(body))
        run_with_trace(service.check_email, email)
