"""OWNER: Person 2. Email header forensics."""
from ..schemas import CheckResult, CheckStatus


def check_headers(raw_headers: str, claimed_sender: str) -> CheckResult:
    """
    Read SPF / DKIM / DMARC results from the 'Authentication-Results' header,
    compare From vs Reply-To, and flag free-mail senders (gmail.com, outlook.com...)
    that claim to be an organisation.

    TODO(Person 2): implement with Python's built-in `email` module.
    - No headers given -> status UNVERIFIED, summary "Headers not provided".
    - dmarc=fail or From/Reply-To domains differ -> FAIL.
    - Free-mail sender claiming an organisation -> WARN.
    - All pass -> PASS.
    evidence example: {"spf": "pass", "dkim": "none", "dmarc": "fail",
                       "from_domain": "gmail.com", "reply_to_domain": "mail.ru"}
    """
    return CheckResult(check="headers", status=CheckStatus.UNVERIFIED,
                       summary="Header check not implemented yet")
