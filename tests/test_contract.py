"""Run: PARAKH_MOCK=1 pytest -q   (must pass before every merge)"""
import os

os.environ.setdefault("PARAKH_MOCK", "1")

from parakh import checks, service  # noqa: E402
from parakh.schemas import CheckResult, EmailInput, ScanResult  # noqa: E402


def test_checks_return_checkresult():
    results = [
        checks.check_headers("", "a@b.com"),
        checks.check_link_destination("https://example.com"),
        checks.check_safe_browsing("https://example.com"),
        checks.check_domain_age("example.com"),
        checks.check_lookalike("example.com", None),
        checks.decode_qr(""),
        checks.check_fee_pressure("Pay Rs. 1500 processing fee within 3 days"),
    ]
    for r in results:
        assert isinstance(r, CheckResult)
        assert r.summary


def test_extract_links():
    assert checks.extract_links("go to https://a.com/x, then http://b.org.") == [
        "https://a.com/x", "http://b.org"]


def test_redact_keeps_sender_evidence():
    out = checks.redact("Dear Ayesha Khan, CNIC 35202-1234567-1. Visit https://scam.example",
                        student_name="Ayesha Khan")
    assert "Ayesha" not in out and "[CNIC]" in out and "https://scam.example" in out


def test_service_contract():
    r = service.scan_inbox(on_event=None)
    assert isinstance(r, ScanResult) and r.verdicts
    r2 = service.check_email(EmailInput(email_id="t", sender="x@y.com", subject="s"))
    assert isinstance(r2, ScanResult) and len(r2.verdicts) == 1
