# Parakh evaluation results
Run: 2026-11-27 09:11 | Mode: REAL agent | Accuracy: **0/7 (0%)**

| Email | What it is | Expected | Got | Confidence | Result | Time |
|---|---|---|---|---|---|---|
| 1_fake_scholarship.eml | Fake scholarship, fee + 3-day deadline, hidden link | likely_scam | ERROR NotImplementedError |  | FAIL | 0.0s |
| 2_qr_poster.eml | Same scam, link hidden in a QR poster | likely_scam | ERROR NotImplementedError |  | FAIL | 0.0s |
| 3_same_scam_reworded.eml | Reworded scam, same link + JazzCash number | likely_scam | ERROR NotImplementedError |  | FAIL | 0.0s |
| 4_genuine_internship.eml | Real internship email from nu.edu.pk | verified | ERROR NotImplementedError |  | FAIL | 0.0s |
| 5_certificate_internship.eml | Real-looking sender, but pay-for-certificate | suspicious | ERROR NotImplementedError |  | FAIL | 0.0s |
| 6_newsletter.eml | Cafe newsletter | not_opportunity | ERROR NotImplementedError |  | FAIL | 0.0s |
| 7_genuine_scholarship.eml | Real HEC scholarship email from nu.edu.pk | verified | ERROR NotImplementedError |  | FAIL | 0.0s |
