"""OWNER: Person 2. Remove the STUDENT's personal data before text reaches Gemini.
NEVER remove the SENDER's address, links, domains, fee amounts or wallet numbers:
those are the evidence."""
import re

PATTERNS = {
    "CNIC": r"\b\d{5}-?\d{7}-?\d\b",
    "PHONE": r"(?:\+92|0092|0)3\d{2}[- ]?\d{7}\b",
    "CARD": r"\b(?:\d[ -]?){13,16}\b",
}

# Words that tell us a phone number is a PAYMENT wallet (scam evidence), not a person's phone.
WALLET_WORDS = re.compile(
    r"pay|send|transfer|deposit|jazz\s?cash|easy\s?paisa|sadapay|nayapay|wallet|account|jama",
    re.IGNORECASE,
)
LOOK_BEFORE = 40  # characters to look at BEFORE the number
LOOK_AFTER = 20   # characters to look at AFTER the number


def _redact_phone(match: re.Match) -> str:
    """Called once for every phone number found. Decide: keep it or hide it."""
    text = match.string
    before = text[max(0, match.start() - LOOK_BEFORE):match.start()]
    after = text[match.end():match.end() + LOOK_AFTER]
    if WALLET_WORDS.search(before) or WALLET_WORDS.search(after):
        return match.group(0)  # scammer's wallet: keep as evidence
    return "[PHONE]"           # a normal phone number: hide it


def redact(text: str, student_name: str = "", student_email: str = "") -> str:
    """Replace the student's own name/email and structured IDs with tags."""
    out = text or ""
    if student_email:
        out = re.sub(re.escape(student_email), "[STUDENT_EMAIL]", out, flags=re.I)
    if student_name:
        out = re.sub(re.escape(student_name), "[STUDENT]", out, flags=re.I)
    out = re.sub(PATTERNS["CNIC"], "[CNIC]", out)
    out = re.sub(PATTERNS["PHONE"], _redact_phone, out)
    out = re.sub(PATTERNS["CARD"], "[CARD]", out)
    return out