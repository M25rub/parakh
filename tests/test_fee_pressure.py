from parakh.checks.content import check_fee_pressure


def test_scam_fee_and_pressure():
    r = check_fee_pressure("Pay a registration fee of Rs. 5,000 within 24 hours. Limited seats!")
    assert r.status == "fail"


def test_personal_wallet():
    r = check_fee_pressure("Send the amount via JazzCash to 0301-1234567 to confirm.")
    assert r.status == "fail" and r.evidence["personal_wallet"] is True


def test_only_pressure():
    assert check_fee_pressure("Apply urgently, last chance to apply.").status == "warn"


def test_genuine_email():
    r = check_fee_pressure("Applications are open until 15 December. There is no application fee.")
    assert r.status == "pass"


def test_empty():
    assert check_fee_pressure("").status == "unverified"
