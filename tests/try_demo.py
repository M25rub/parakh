"""Manual demo: run Person 2's checks on a fake scam and a fake genuine email.
Run:  python tests\\try_demo.py
"""
import os
import tempfile

# Keep the demo from touching your real memory file.
os.environ["MEMORY_FILE"] = os.path.join(tempfile.gettempdir(), "parakh_demo_memory.json")

from parakh import checks, memory  # noqa: E402
from parakh.checks.links import get_domain  # noqa: E402

SCAM_HEADERS = """From: HEC Scholarships <hec.office@gmail.com>
Reply-To: claims@mail.ru
Authentication-Results: mx.google.com; spf=pass; dkim=none; dmarc=fail"""

SCAM_BODY = """Dear Ayesha Khan,
You are selected for the HEC scholarship. Pay Rs. 15,000 processing fee within 3 days
to JazzCash 0300-1234567. Register at https://hec-gov-pk.com/apply
Your CNIC 35202-1234567-1 and phone 0321-5551234 are on file."""

GOOD_HEADERS = """From: careers@google.com
Authentication-Results: mx.google.com; spf=pass; dkim=pass; dmarc=pass"""

GOOD_BODY = "Internship applications close 2026-12-20. No fee. Apply at https://careers.google.com"


def show(title, results):
    print(f"\n=== {title} ===")
    for r in results:
        print(f"  [{r.status.value.upper():10}] {r.check:17} {r.summary}")


def run(title, headers, sender, body, org):
    safe_text = checks.redact(body, student_name="Ayesha Khan")
    print(f"\n--- {title}: text that Gemini would see ---\n{safe_text}")
    links = checks.extract_links(body)
    results = [checks.check_headers(headers, sender)]
    for url in links:
        domain = get_domain(url)
        results += [
            checks.check_lookalike(domain, org),
            checks.check_domain_age(domain),
            checks.check_link_destination(url),
            checks.check_safe_browsing(url),
        ]
    show(title, results)
    return links


links = run("SCAM EMAIL", SCAM_HEADERS, "HEC Scholarships <hec.office@gmail.com>", SCAM_BODY, "HEC")
run("GENUINE EMAIL", GOOD_HEADERS, "careers@google.com", GOOD_BODY, "Google")

print("\n=== MEMORY ===")
indicators = [get_domain(u) for u in links]
memory.save(indicators, "likely_scam", "Fake HEC fee request")
print("After saving, lookup finds:", memory.lookup(indicators))