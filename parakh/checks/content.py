"""OWNER: Person 1. Fee and pressure signals in the email text."""
import re

from ..schemas import CheckResult, CheckStatus

# Asking the student to pay (English + Roman Urdu)
FEE_PATTERNS = [
    r"registration fee", r"processing fee", r"application fee", r"certificate fee",
    r"security deposit", r"refundable (?:fee|deposit|amount)", r"confirmation fee",
    r"admin(?:istration)? fee", r"pay (?:a |the )?(?:small )?(?:fee|amount|charges?)",
    r"(?:rs\.?|pkr|\$|usd)\s?\d[\d,]*", r"\d[\d,]*\s?(?:rs|rupees|pkr)\b",
    r"fees? (?:jama|ada) (?:karein|karain|karo)", r"payment (?:karein|karain|karo)",
]

# Rushing the student
PRESSURE_PATTERNS = [
    r"within \d+\s?(?:hours?|hrs?|days?)", r"\b\d+\s?(?:hours?|hrs?)\b", r"limited seats",
    r"only \d+ seats", r"urgent(?:ly)?", r"last chance", r"act now", r"immediately",
    r"today only", r"expires? (?:today|tonight|soon)", r"don'?t miss",
    r"jaldi", r"foran", r"aakhri (?:mauqa|moqa)",
]

# Paying to a personal mobile wallet / phone number
WALLET_PATTERN = r"jazz\s?cash|easy\s?paisa|sadapay|nayapay"
PHONE_PATTERN = r"(?:\+92|0092|0)3\d{2}[\s-]?\d{7}"


NEGATION = re.compile(r"\b(?:no|not|without|free of|zero|never)\b[^.]{0,15}$", re.IGNORECASE)


def _find(patterns: list[str], text: str) -> list[str]:
    found = []
    for p in patterns:
        for m in re.finditer(p, text, flags=re.IGNORECASE):
            if NEGATION.search(text[max(0, m.start() - 25):m.start()]):
                continue  # "no application fee" is a good sign, not a red flag
            hit = m.group(0).strip()
            if hit.lower() not in (f.lower() for f in found):
                found.append(hit)
    return found


def check_fee_pressure(text: str) -> CheckResult:
    """Fee + pressure -> FAIL. Fee to a personal wallet -> FAIL. Only one signal -> WARN. None -> PASS."""
    text = text or ""
    if not text.strip():
        return CheckResult(check="fee_pressure", status=CheckStatus.UNVERIFIED,
                           summary="No email text to check")

    fees = _find(FEE_PATTERNS, text)
    pressure = _find(PRESSURE_PATTERNS, text)
    wallet = bool(re.search(WALLET_PATTERN, text, re.IGNORECASE)) and bool(re.search(PHONE_PATTERN, text))

    evidence = {"fees_found": fees, "pressure_found": pressure, "personal_wallet": wallet}

    if wallet:
        status, summary = CheckStatus.FAIL, "Asks for payment to a personal mobile wallet number"
    elif fees and pressure:
        status, summary = CheckStatus.FAIL, "Asks for money and rushes you to pay"
    elif fees:
        status, summary = CheckStatus.WARN, "Mentions a fee or payment"
    elif pressure:
        status, summary = CheckStatus.WARN, "Uses pressure or urgency language"
    else:
        status, summary = CheckStatus.PASS, "No fee requests or pressure tactics found"

    return CheckResult(check="fee_pressure", status=status, summary=summary, evidence=evidence)
