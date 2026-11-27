"""
OWNER: Person 1. Turns a raw email (.eml file, or Gmail "Show original" text) into EmailInput.
Used by "Check one email" mode, and available to the agent for any raw email.

- sender / reply_to / subject from headers; raw_headers = all header lines as text.
- body_text: text/plain if present, otherwise the HTML converted to readable text.
- links: links in the text PLUS hidden href="" targets from the HTML (scammers hide links there).
- qr_images_b64: every image attachment / inline image as base64 (for the QR decoder).
- Never crashes: on a broken email it returns whatever it could read.
"""
import base64
import html
import re
from email import policy
from email.parser import Parser

from .checks import extract_links
from .schemas import EmailInput

HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def html_to_text(raw_html: str) -> str:
    """Very small HTML -> text converter. Shows the real link target next to link text,
    e.g. 'Apply here [https://real-target.xyz]', so the agent sees where links truly go."""
    s = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", raw_html)
    s = re.sub(r"""(?is)<a\b[^>]*href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""",
               lambda m: f"{m.group(2)} [{m.group(1)}]", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def _content(part) -> str:
    try:
        return part.get_content()
    except Exception:  # noqa: BLE001  (bad charset etc.)
        data = part.get_payload(decode=True) or b""
        return data.decode("utf-8", errors="replace")


def parse_raw_email(raw: str, email_id: str = "pasted-1") -> EmailInput:
    try:
        msg = Parser(policy=policy.default).parsestr(raw or "")
    except Exception:  # noqa: BLE001
        return EmailInput(email_id=email_id, sender="", body_text=raw or "", links=extract_links(raw or ""))

    plain, html_body = "", ""
    images: list[str] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        try:
            if ctype == "text/plain" and not plain and part.get_content_disposition() != "attachment":
                plain = _content(part)
            elif ctype == "text/html" and not html_body:
                html_body = _content(part)
            elif ctype.startswith("image/"):
                data = part.get_payload(decode=True)
                if data:
                    images.append(base64.b64encode(data).decode())
        except Exception:  # noqa: BLE001  never crash on one bad part
            continue

    body = plain or (html_to_text(html_body) if html_body else "")
    links = extract_links(body)
    for href in HREF_RE.findall(html_body):
        href = html.unescape(href).strip()
        if href.lower().startswith(("http://", "https://")) and href not in links:
            links.append(href)

    def header(name: str) -> str:
        try:
            return str(msg.get(name, "") or "")
        except Exception:  # noqa: BLE001
            return ""

    raw_headers = "\n".join(f"{k}: {v}" for k, v in msg.items())
    return EmailInput(email_id=email_id, sender=header("From"),
                      reply_to=header("Reply-To") or None, subject=header("Subject"),
                      body_text=body, raw_headers=raw_headers, links=links, qr_images_b64=images)
