"""OWNER: Person 1. Fee and pressure signals in the email text."""
from ..schemas import CheckResult, CheckStatus


def check_fee_pressure(text: str) -> CheckResult:
    """
    TODO(Person 1): regex/keyword detection (English + Roman Urdu):
    fees: "registration fee", "processing fee", "certificate fee", "security deposit", "Rs.", "PKR"
    pressure: "within 24 hours", "3 days", "limited seats", "urgent", "last chance"
    payment to personal wallets: "JazzCash", "Easypaisa" + an 03xx number
    Fee + pressure -> FAIL. Only one -> WARN. None -> PASS.
    evidence: {"fees_found": [...], "pressure_found": [...], "personal_wallet": true}
    """
    return CheckResult(check="fee_pressure", status=CheckStatus.UNVERIFIED,
                       summary="Fee/pressure check not implemented yet")
