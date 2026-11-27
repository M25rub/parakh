"""
OWNER: Person 1. Evaluation harness: runs every demo email through the agent and checks the
verdict matches what a careful human would say. Shows judges we TESTED the agent.

Run with the real agent (Windows cmd):
    set PARAKH_MOCK=0
    python tests/eval_demo.py
Results are printed and also saved to tests/eval_results.md
"""
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from parakh import service  # noqa: E402
from parakh.parse_email import parse_raw_email  # noqa: E402

DEMO = ROOT / "demo_emails"
REPORT = ROOT / "tests" / "eval_results.md"

# file name -> (expected verdict, what the email is)
EXPECTED = {
    "1_fake_scholarship.eml":       ("likely_scam",     "Fake scholarship, fee + 3-day deadline, hidden link"),
    "2_qr_poster.eml":              ("likely_scam",     "Same scam, link hidden in a QR poster"),
    "3_same_scam_reworded.eml":     ("likely_scam",     "Reworded scam, same link + JazzCash number"),
    "4_genuine_internship.eml":     ("verified",        "Real internship email from nu.edu.pk"),
    "5_certificate_internship.eml": ("suspicious",      "Real-looking sender, but pay-for-certificate"),
    "6_newsletter.eml":             ("not_opportunity", "Cafe newsletter"),
    "7_genuine_scholarship.eml":    ("verified",        "Real HEC scholarship email from nu.edu.pk"),
}
# A stricter answer is still safe for the student, so it also counts as a pass
ALSO_OK = {"suspicious": {"likely_scam"}}


def main():
    mode = "MOCK (sample answers, not the real agent)" if service.is_mock() else "REAL agent"
    print(f"\nParakh evaluation | mode: {mode}\n")
    print(f"{'email':32} {'expected':16} {'got':16} {'conf':>5}  {'result':6}  time")
    print("-" * 88)

    rows, failures = [], []
    passed = total = 0
    for name, (want, about) in EXPECTED.items():
        path = DEMO / name
        if not path.exists():
            print(f"{name:32} {want:16} {'(file missing)':16} {'':>5}  SKIP")
            continue
        total += 1
        email = parse_raw_email(path.read_text(encoding="utf-8", errors="replace"), email_id=name)
        start = time.time()
        try:
            v = service.check_email(email).verdicts[0]
            got, conf, why = v.risk.value, f"{v.confidence:.2f}", v.explanation
        except Exception as e:  # noqa: BLE001  one broken email must not stop the whole run
            got, conf, why = f"ERROR {type(e).__name__}", "", str(e)
        secs = time.time() - start
        ok = got == want or got in ALSO_OK.get(want, set())
        passed += ok
        if not ok:
            failures.append((name, want, got, why))
        rows.append((name, about, want, got, conf, "PASS" if ok else "FAIL", f"{secs:.1f}s"))
        print(f"{name:32} {want:16} {got:16} {conf:>5}  {'PASS' if ok else 'FAIL':6}  {secs:.1f}s")
        if not service.is_mock():
            time.sleep(5)  # stay under the free-tier rate limit

    print("-" * 88)
    if not total:
        print("No demo emails found in demo_emails/")
        return
    score = f"{passed}/{total} ({100 * passed // total}%)"
    print(f"Accuracy: {score}")
    for name, want, got, why in failures:
        print(f"  FAIL {name}: expected {want}, got {got}. Agent said: {why[:150]}")

    lines = [
        "# Parakh evaluation results",
        f"Run: {datetime.now():%Y-%m-%d %H:%M} | Mode: {mode} | Accuracy: **{score}**",
        "",
        "| Email | What it is | Expected | Got | Confidence | Result | Time |",
        "|---|---|---|---|---|---|---|",
    ] + [f"| {' | '.join(r)} |" for r in rows]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved table to {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()