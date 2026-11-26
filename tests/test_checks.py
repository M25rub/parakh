import os

os.environ.setdefault("PARAKH_MOCK", "1")

from parakh import checks  # noqa: E402


def test_redact_keeps_wallet_number():
    out = checks.redact("Send Rs. 5,000 to JazzCash 0300-1234567 today.")
    assert "0300-1234567" in out


def test_redact_hides_student_phone():
    out = checks.redact("Call me on 0321-5551234.")
    assert "0321-5551234" not in out and "[PHONE]" in out


def test_redact_hides_cnic_name_email_keeps_link():
    out = checks.redact(
        "Dear Ayesha Khan (ayesha@gmail.com), CNIC 35202-1234567-1. Visit https://scam.example",
        student_name="Ayesha Khan",
        student_email="ayesha@gmail.com",
    )
    assert "Ayesha" not in out
    assert "ayesha@gmail.com" not in out
    assert "[CNIC]" in out
    assert "https://scam.example" in out


def test_redact_handles_empty():
    assert checks.redact("") == ""
    assert checks.redact(None) == ""


def _h(*lines):
    return "\n".join(lines)


def test_headers_missing_is_unverified():
    r = checks.check_headers("", "a@b.com")
    assert r.status.value == "unverified"


def test_headers_dmarc_fail_and_reply_to_differs():
    raw = _h(
        "From: HEC Scholarships <info@hec-scholar.com>",
        "Reply-To: help@mail.ru",
        "Authentication-Results: mx.google.com; spf=pass; dkim=none; dmarc=fail",
    )
    r = checks.check_headers(raw, "HEC Scholarships <info@hec-scholar.com>")
    assert r.status.value == "fail"
    assert r.evidence["dmarc"] == "fail"
    assert r.evidence["reply_to_domain"] == "mail.ru"


def test_headers_freemail_claiming_org_is_warn():
    raw = _h(
        "From: HEC Scholarships <hec.office@gmail.com>",
        "Authentication-Results: mx.google.com; spf=pass; dkim=pass; dmarc=pass",
    )
    r = checks.check_headers(raw, "HEC Scholarships <hec.office@gmail.com>")
    assert r.status.value == "warn"


def test_headers_all_good_is_pass():
    raw = _h(
        "From: info@hec.gov.pk",
        "Reply-To: noreply@mail.hec.gov.pk",
        "Authentication-Results: mx.google.com; spf=pass; dkim=pass; dmarc=pass",
    )
    r = checks.check_headers(raw, "info@hec.gov.pk")
    assert r.status.value == "pass"    