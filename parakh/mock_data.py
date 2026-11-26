"""
OWNER: Person 1. Fake demo data so the UI can be built before the agent is ready.
Only used when PARAKH_MOCK=1. The UI must show a visible "MOCK DATA" badge when
ScanResult.mock is True (the rules forbid presenting mock-ups as working features).
"""
import time

from .schemas import (CheckResult, CheckStatus, Deadline, EmailInput, Risk, ScanResult,
                      TraceEvent, Verdict)

S = CheckStatus


def _verdicts() -> list[Verdict]:
    return [
        Verdict(
            email_id="m1", subject="Congratulations! Fully Funded Scholarship 2026",
            sender="scholarship.office2026@gmail.com", risk=Risk.LIKELY_SCAM, confidence=0.93,
            explanation="The sender failed DMARC, the link leads to a 9-day-old domain, and the "
                        "official program page does not charge any fee.",
            gmail_label_applied="Parakh/Likely scam",
            checks=[
                CheckResult(check="headers", status=S.FAIL,
                            summary="DMARC failed and replies go to a different Gmail address",
                            evidence={"dmarc": "fail"}),
                CheckResult(check="domain_age", status=S.FAIL,
                            summary="Payment site was registered 9 days ago",
                            evidence={"age_days": 9}),
                CheckResult(check="fee_pressure", status=S.FAIL,
                            summary="Asks for a Rs. 15,000 processing fee within 3 days"),
                CheckResult(check="official_source", status=S.FAIL,
                            summary="Official program page says there is no application fee"),
            ]),
        Verdict(
            email_id="m2", subject="Summer Software Internship: Offer",
            sender="careers@realcompany.example", risk=Risk.VERIFIED, confidence=0.86,
            explanation="Authenticated sender, established domain, no fee requested.",
            gmail_label_applied="Parakh/Verified",
            deadline=Deadline(title="Internship acceptance deadline", date="2026-12-15",
                              calendar_event_created=True),
            checks=[
                CheckResult(check="headers", status=S.PASS, summary="SPF, DKIM and DMARC passed"),
                CheckResult(check="domain_age", status=S.PASS, summary="Domain is 11 years old"),
                CheckResult(check="fee_pressure", status=S.PASS, summary="No fee requested"),
            ]),
        Verdict(
            email_id="m3", subject="Virtual Internship + Certificate (Limited Seats)",
            sender="hr@internhub-pk.example", risk=Risk.SUSPICIOUS, confidence=0.71,
            explanation="Asks for a certificate fee and uses urgency, but the sender "
                        "authenticated correctly.",
            gmail_label_applied="Parakh/Suspicious",
            checks=[
                CheckResult(check="headers", status=S.PASS, summary="SPF and DKIM passed"),
                CheckResult(check="fee_pressure", status=S.WARN,
                            summary="Requests a Rs. 1,500 certificate fee"),
                CheckResult(check="safe_browsing", status=S.UNVERIFIED,
                            summary="Safe Browsing could not be reached; confidence lowered"),
            ]),
        Verdict(
            email_id="m4", subject="Re: Scholarship confirmation fee (reminder)",
            sender="admissions.desk2026@gmail.com", risk=Risk.LIKELY_SCAM, confidence=0.95,
            memory_hit=True, gmail_label_applied="Parakh/Likely scam",
            explanation="Same payment link as a scam already reported by another student. "
                        "Recognised instantly from memory.",
            checks=[CheckResult(check="memory", status=S.FAIL,
                                summary="Link domain was reported before (3 reports)")]),
    ]


def _trace() -> list[TraceEvent]:
    return [
        TraceEvent(kind="mcp_call", via_mcp="gmail", tool="search_gmail_messages",
                   message='Searching inbox: scholarship OR internship OR admission → 4 emails'),
        TraceEvent(kind="thinking", message="Email 1 has headers, a link and a fee → "
                                            "plan: memory, headers, link, fee, official source"),
        TraceEvent(kind="tool_call", via_mcp="parakh-checks", tool="check_headers",
                   message="DMARC fail, Reply-To mismatch"),
        TraceEvent(kind="tool_call", via_mcp="parakh-checks", tool="check_domain_age",
                   message="Domain registered 9 days ago"),
        TraceEvent(kind="tool_call", tool="official_source_agent",
                   message="Official page found: no application fee"),
        TraceEvent(kind="decision", message="Email 1 → Likely scam (93%)"),
        TraceEvent(kind="mcp_call", via_mcp="gmail", tool="modify_gmail_message_labels",
                   message='Label "Parakh/Likely scam" applied'),
        TraceEvent(kind="decision", message="Email 2 → Verified (86%)"),
        TraceEvent(kind="mcp_call", via_mcp="calendar", tool="create_event",
                   message="Deadline 15 Dec added to Google Calendar"),
        TraceEvent(kind="tool_call", tool="memory_lookup",
                   message="Email 4: link domain already reported → skipping other checks"),
        TraceEvent(kind="decision", message="Email 4 → Likely scam (from memory)"),
    ]


def mock_scan(on_event=None) -> ScanResult:
    trace = _trace()
    for ev in trace:
        if on_event:
            on_event(ev)
            time.sleep(0.4)
    v = _verdicts()
    return ScanResult(verdicts=v, trace=trace, emails_scanned=len(v), mock=True)


def mock_single(email: EmailInput, on_event=None) -> ScanResult:
    v = _verdicts()[0].model_copy(update={"email_id": email.email_id, "subject": email.subject,
                                          "sender": email.sender, "gmail_label_applied": None})
    trace = _trace()[1:6]
    for ev in trace:
        if on_event:
            on_event(ev)
            time.sleep(0.4)
    return ScanResult(verdicts=[v], trace=trace, emails_scanned=1, mock=True)
