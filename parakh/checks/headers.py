"""OWNER: Person 2. Email header forensics."""
import re
from email.parser import HeaderParser
from email.utils import parseaddr

from ..schemas import CheckResult, CheckStatus

FREE_MAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "ymail.com", "mail.ru", "yandex.com", "proton.me",
    "protonmail.com", "aol.com", "icloud.com", "gmx.com",
}

# Words that suggest the sender is pretending to be an organisation.
ORG_WORDS = (
    "university", "hec", "scholarship", "foundation", "ministry", "commission",
    "embassy", "board", "institute", "college", "program", "programme",
    "admission", "internship", "recruitment", "hr", "fund", "trust", "office",
)


def _domain_of(address: str) -> str:
    """'Ali <ali@Gmail.com>' -> 'gmail.com'. Returns '' if there is no address."""
    _, addr = parseaddr(address or "")
    if "@" not in addr:
        return ""
    return addr.rpartition("@")[2].strip().strip(">").lower()


def _related(a: str, b: str) -> bool:
    """True if both domains belong to the same owner (same, or one is a subdomain)."""
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _auth_result(auth_text: str, name: str) -> str:
    """Find 'spf=pass' / 'dkim=fail' / 'dmarc=none' inside the header text."""
    m = re.search(rf"\b{name}\s*=\s*(\w+)", auth_text, re.IGNORECASE)
    return m.group(1).lower() if m else "none"


def _claims_organisation(display_name: str, address: str) -> bool:
    text = f"{display_name} {address.split('@')[0]}".lower()
    words = re.findall(r"[a-z]+", text)
    return any(w in ORG_WORDS for w in words)


def check_headers(raw_headers: str, claimed_sender: str) -> CheckResult:
    """Read SPF/DKIM/DMARC, compare From vs Reply-To, flag free-mail org claims."""
    try:
        if not raw_headers or not raw_headers.strip():
            return CheckResult(check="headers", status=CheckStatus.UNVERIFIED,
                               summary="Headers not provided")

        msg = HeaderParser().parsestr(raw_headers)

        # Who does the email say it is from?
        sender_text = claimed_sender or str(msg.get("From", ""))
        display_name, address = parseaddr(sender_text)
        if "@" not in address:
            display_name, address = parseaddr(str(msg.get("From", "")))
        from_domain = _domain_of(address)
        reply_to_domain = _domain_of(str(msg.get("Reply-To", "")))

        # The three stamps.
        auth_text = " ".join(str(v) for v in (msg.get_all("Authentication-Results") or []))
        spf = _auth_result(auth_text, "spf")
        dkim = _auth_result(auth_text, "dkim")
        dmarc = _auth_result(auth_text, "dmarc")

        evidence = {
            "spf": spf, "dkim": dkim, "dmarc": dmarc,
            "from_domain": from_domain, "reply_to_domain": reply_to_domain,
        }

        # ---- FAIL: strong evidence of lying ----
        problems = []
        if dmarc == "fail":
            problems.append("the sender failed DMARC (the domain does not vouch for this email)")
        if spf == "fail":
            problems.append("the sender failed SPF (sent from a server the domain did not approve)")
        if reply_to_domain and from_domain and not _related(from_domain, reply_to_domain):
            problems.append(f"replies go to {reply_to_domain}, not {from_domain}")
        if problems:
            return CheckResult(check="headers", status=CheckStatus.FAIL,
                               summary="Sender looks forged: " + "; ".join(problems) + ".",
                               evidence=evidence)

        # ---- WARN: suspicious but not proof ----
        if from_domain in FREE_MAIL and _claims_organisation(display_name, address):
            return CheckResult(check="headers", status=CheckStatus.WARN,
                               summary=f"A free {from_domain} account is pretending to be an organisation.",
                               evidence=evidence)
        if spf == "softfail":
            return CheckResult(check="headers", status=CheckStatus.WARN,
                               summary="SPF returned softfail, so the sending server is only weakly approved.",
                               evidence=evidence)

        # ---- No stamps at all: we cannot say PASS ----
        if not auth_text.strip():
            return CheckResult(check="headers", status=CheckStatus.UNVERIFIED,
                               summary="No SPF/DKIM/DMARC results found in the headers.",
                               evidence=evidence)

        # ---- PASS ----
        return CheckResult(check="headers", status=CheckStatus.PASS,
                           summary="Sender checks (SPF/DKIM/DMARC and Reply-To) look consistent.",
                           evidence=evidence)
    except Exception as exc:  # never crash the agent
        return CheckResult(check="headers", status=CheckStatus.UNVERIFIED,
                           summary=f"Could not read the headers ({type(exc).__name__}).")