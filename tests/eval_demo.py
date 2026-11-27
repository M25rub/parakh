"""
OWNER: Person 1. Evaluation harness: runs every demo email through the REAL agent and checks
the verdict matches what we expect. Run: PARAKH_MOCK=0 python tests/eval_demo.py
Shows judges we TESTED the agent, not just hoped it works.

TODO(Person 1): save each demo email as demo_emails/<name>.eml, fill EXPECTED, print a table:
email | expected | got | confidence | pass/fail, and the overall accuracy.
"""
from pathlib import Path

from parakh import service
from parakh.parse_email import parse_raw_email

EXPECTED = {
    # "1_fake_scholarship.eml": "likely_scam",
    # "4_genuine_internship.eml": "verified",
}


def main():
    ok = 0
    for name, want in EXPECTED.items():
        email = parse_raw_email(Path("demo_emails", name).read_text(), email_id=name)
        got = service.check_email(email).verdicts[0]
        hit = got.risk.value == want
        ok += hit
        print(f"{name:35} expected={want:12} got={got.risk.value:12} "
              f"conf={got.confidence:.2f} {'PASS' if hit else 'FAIL'}")
    if EXPECTED:
        print(f"Accuracy: {ok}/{len(EXPECTED)}")


if __name__ == "__main__":
    main()
