# Demo emails (OWNER: Person 1)
Sample data only. These are made-up scam emails for testing Parakh. No real students, no real offers.
The scam domain `scholarship-hec-pk.xyz` is fictional.

| File | What it is | Expected verdict |
|---|---|---|
| `1_fake_scholarship.eml` | "Selected!" + Rs. 15,000 fee in 3 days, link text says hec.gov.pk but goes elsewhere, DMARC fail | Likely scam |
| `2_qr_poster.eml` | Same scam, link hidden in a QR code poster (`qr_poster.png`) | Likely scam |
| `3_same_scam_reworded.eml` | Reworded, same link + JazzCash number | Likely scam (from shared memory) |
| `4_genuine_internship.eml` | Real internship email from nu.edu.pk (personal details removed) | Verified + Calendar deadline |
| `5_certificate_internship.eml` | Authenticated sender, but "pay certificate fee" + 24 hours | Suspicious |
| `6_newsletter.eml` | Cafe menu | Not an opportunity |
| `7_genuine_scholarship.eml` | Real HEC scholarship email from nu.edu.pk (personal details removed) | Verified |

## Use them
- **Check one email page:** upload any `.eml` file.
- **Scan inbox demo:** send each one from your own accounts to the demo Gmail (attach `qr_poster.png` for #2).
- **Evaluation:** `python tests/eval_demo.py` (with `PARAKH_MOCK=0` for the real agent).
