from parakh import service
from parakh.schemas import EmailInput

email = EmailInput(email_id="t1", sender="hec-scholarship@gmail.com", subject="Urgent scholarship",
                   body_text="Pay Rs. 1500 processing fee on JazzCash 03001234567 within 24 hours.")
r = service.check_email(email, on_event=lambda e: print(e.kind, "|", e.message))
print("VERDICTS:", r.verdicts)