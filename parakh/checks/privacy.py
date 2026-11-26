"""OWNER: Person 2. Remove the STUDENT's personal data before text reaches Gemini.
NEVER remove the SENDER's address, links, domains, fee amounts or wallet numbers:
those are the evidence."""
import re

PATTERNS = {
    "CNIC": r"\b\d{5}-?\d{7}-?\d\b",
    "PHONE": r"(?:\+92|0092|0)3\d{2}[- ]?\d{7}\b",
    "CARD": r"\b(?:\d[ -]?){13,16}\b",
}


def redact(text: str, student_name: str = "", student_email: str = "") -> str:
    """Replace the student's own name/email and structured IDs with tags."""
    out = text or ""
    if student_email:
        out = re.sub(re.escape(student_email), "[STUDENT_EMAIL]", out, flags=re.I)
    if student_name:
        out = re.sub(re.escape(student_name), "[STUDENT]", out, flags=re.I)
    for label, pat in PATTERNS.items():
        out = re.sub(pat, f"[{label}]", out)
    # TODO(Person 2): keep wallet numbers that appear next to "send/pay/JazzCash/Easypaisa"
    # (they are scam evidence). Phone redaction above currently removes them too.
    return out
