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


from unittest.mock import MagicMock, patch  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402


def _fake_rdap(days_old):
    reg = (datetime.now(timezone.utc) - timedelta(days=days_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"events": [
        {"eventAction": "last changed", "eventDate": "2026-01-01T00:00:00Z"},
        {"eventAction": "registration", "eventDate": reg},
    ]}
    return resp


def test_domain_age_new_is_fail():
    with patch("parakh.checks.links.requests.get", return_value=_fake_rdap(10)):
        r = checks.check_domain_age("hec-scholar-2026.com")
    assert r.status.value == "fail" and r.evidence["age_days"] == 10


def test_domain_age_months_is_warn():
    with patch("parakh.checks.links.requests.get", return_value=_fake_rdap(200)):
        assert checks.check_domain_age("x.org").status.value == "warn"


def test_domain_age_old_is_pass():
    with patch("parakh.checks.links.requests.get", return_value=_fake_rdap(4000)):
        assert checks.check_domain_age("google.com").status.value == "pass"


def test_domain_age_not_supported_is_unverified():
    with patch("parakh.checks.links.requests.get", return_value=MagicMock(status_code=404)):
        assert checks.check_domain_age("hec.gov.pk").status.value == "unverified"


def test_domain_age_network_error_is_unverified():
    with patch("parakh.checks.links.requests.get", side_effect=Exception("no internet")):
        assert checks.check_domain_age("x.com").status.value == "unverified"   
        

def test_safe_browsing_no_key_is_unverified(monkeypatch):
    monkeypatch.delenv("SAFE_BROWSING_API_KEY", raising=False)
    assert checks.check_safe_browsing("https://x.com").status.value == "unverified"


def test_safe_browsing_match_is_fail(monkeypatch):
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "fake")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"matches": [{"threatType": "SOCIAL_ENGINEERING"}]}
    with patch("parakh.checks.links.requests.post", return_value=resp):
        r = checks.check_safe_browsing("https://bad.example")
    assert r.status.value == "fail" and "SOCIAL_ENGINEERING" in r.evidence["threats"]


def test_safe_browsing_clean_is_pass(monkeypatch):
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "fake")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {}
    with patch("parakh.checks.links.requests.post", return_value=resp):
        assert checks.check_safe_browsing("https://ok.example").status.value == "pass"


def test_safe_browsing_api_error_is_unverified(monkeypatch):
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "fake")
    with patch("parakh.checks.links.requests.post", return_value=MagicMock(status_code=403)):
        assert checks.check_safe_browsing("https://x.com").status.value == "unverified"
        

def _redirect(to):
    return MagicMock(status_code=302, headers={"Location": to})


def _ok():
    return MagicMock(status_code=200, headers={})


def test_link_private_address_is_blocked():
    r = checks.check_link_destination("http://127.0.0.1/admin")
    assert r.status.value == "unverified" and "blocked_host" in r.evidence


def test_link_shortener_to_other_domain_is_warn():
    responses = [_redirect("https://hec-scholar-2026.com/pay"), _ok()]
    with patch("parakh.checks.links._is_private_host", return_value=False), \
         patch("parakh.checks.links._fetch_headers", side_effect=responses):
        r = checks.check_link_destination("https://bit.ly/abc")
    assert r.status.value == "warn"
    assert r.evidence["final_domain"] == "hec-scholar-2026.com"


def test_link_same_domain_is_pass():
    with patch("parakh.checks.links._is_private_host", return_value=False), \
         patch("parakh.checks.links._fetch_headers", return_value=_ok()):
        assert checks.check_link_destination("https://hec.gov.pk/apply").status.value == "pass"


def test_link_too_many_hops_is_warn():
    with patch("parakh.checks.links._is_private_host", return_value=False), \
         patch("parakh.checks.links._fetch_headers", return_value=_redirect("https://a.com/next")):
        r = checks.check_link_destination("https://a.com/start")
    assert r.status.value == "warn"


def test_link_network_error_is_unverified():
    with patch("parakh.checks.links._is_private_host", return_value=False), \
         patch("parakh.checks.links._fetch_headers", side_effect=Exception("boom")):
        assert checks.check_link_destination("https://x.com").status.value == "unverified"
        

def test_lookalike_official_is_pass():
    assert checks.check_lookalike("hec.gov.pk", "HEC").status.value == "pass"
    assert checks.check_lookalike("portal.hec.gov.pk", "HEC").status.value == "pass"


def test_lookalike_dashed_copy_is_fail():
    r = checks.check_lookalike("hec-gov-pk.com", "HEC")
    assert r.status.value == "fail" and r.evidence["imitates"] == "hec.gov.pk"


def test_lookalike_official_hidden_in_front_is_fail():
    assert checks.check_lookalike("hec.gov.pk.apply-now.com", "HEC").status.value == "fail"


def test_lookalike_punycode_is_fail():
    assert checks.check_lookalike("xn--hec-gv-pk-abc.com", None).status.value == "fail"


def test_lookalike_letter_swap_is_fail():
    assert checks.check_lookalike("rnicrosoft.com", None).status.value == "fail"


def test_lookalike_brand_word_in_other_domain_is_warn():
    assert checks.check_lookalike("hec-scholarship-portal.com", "HEC").status.value == "warn"


def test_lookalike_unrelated_is_pass():
    assert checks.check_lookalike("random-site.com", None).status.value == "pass"