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