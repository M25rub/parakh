"""
OWNER: Person 1. Turns a raw email (.eml file, or Gmail "Show original" text) into EmailInput.
Used by "Check one email" mode, and available to the agent for any raw email.

TODO(Person 1):
- Parse with Python's `email` module (policy=email.policy.default).
- sender / reply_to / subject from headers; raw_headers = all header lines as text.
- body_text: prefer text/plain; else convert text/html to text (strip tags, keep link URLs).
- links: extract_links(body) PLUS href="" values from the HTML part (scammers hide links there).
- qr_images_b64: every image attachment / inline image (image/png, image/jpeg) as base64.
- Never crash: on a broken email return what you could parse.
"""
import base64
from email import policy
from email.parser import Parser

from .checks import extract_links
from .schemas import EmailInput


def parse_raw_email(raw: str, email_id: str = "pasted-1") -> EmailInput:
    msg = Parser(policy=policy.default).parsestr(raw or "")
    body = ""
    images: list[str] = []
    for part in msg.walk() if msg.is_multipart() else [msg]:
        ctype = part.get_content_type()
        if ctype == "text/plain" and not body:
            try:
                body = part.get_content()
            except Exception:  # noqa: BLE001
                pass
        elif ctype.startswith("image/"):
            data = part.get_payload(decode=True)
            if data:
                images.append(base64.b64encode(data).decode())
    # TODO(Person 1): HTML fallback + href extraction
    raw_headers = "\n".join(f"{k}: {v}" for k, v in msg.items())
    return EmailInput(email_id=email_id, sender=str(msg.get("From", "")),
                      reply_to=str(msg.get("Reply-To")) if msg.get("Reply-To") else None,
                      subject=str(msg.get("Subject", "")), body_text=body,
                      raw_headers=raw_headers, links=extract_links(body),
                      qr_images_b64=images)
