"""OWNER: Person 1. QR decoding: finds QR codes in email images and reads the hidden link."""
import base64
import re

import cv2
import numpy as np

from ..schemas import CheckResult, CheckStatus

PAYMENT_HINTS = re.compile(r"pay|wallet|jazzcash|easypaisa|sadapay|nayapay|upi:|bitcoin:|checkout|invoice", re.I)
URL_RE = re.compile(r"^(?:https?://|www\.)", re.I)


def _to_image(image_b64: str):
    """base64 text (optionally 'data:image/png;base64,...') -> OpenCV image, or None."""
    if "," in image_b64[:100]:
        image_b64 = image_b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(image_b64, validate=False)
    except Exception:
        return None
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    return img


def _decode(img) -> list[str]:
    detector = cv2.QRCodeDetector()
    found: list[str] = []
    # Try the image as-is, then bigger and greyscale/thresholded (helps with small or low-contrast QRs)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variants = [img, gray, cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC),
                cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]]
    for v in variants:
        try:
            ok, texts, _, _ = detector.detectAndDecodeMulti(v)
            if ok:
                found += [t for t in texts if t]
            if not found:
                text, _, _ = detector.detectAndDecode(v)
                if text:
                    found.append(text)
        except cv2.error:
            continue
        if found:
            break
    return list(dict.fromkeys(found))  # remove duplicates, keep order


def decode_qr(image_b64: str) -> CheckResult:
    """No QR -> SKIPPED. QR with a link or payment -> WARN (the agent then checks the link). Plain text -> PASS."""
    if not image_b64:
        return CheckResult(check="qr", status=CheckStatus.SKIPPED, summary="No image to scan")

    img = _to_image(image_b64)
    if img is None:
        return CheckResult(check="qr", status=CheckStatus.UNVERIFIED, summary="Could not read the image")

    decoded = _decode(img)
    if not decoded:
        return CheckResult(check="qr", status=CheckStatus.SKIPPED, summary="No QR code found in the image",
                           evidence={"decoded": []})

    urls = [d for d in decoded if URL_RE.match(d)]
    payment = any(PAYMENT_HINTS.search(d) for d in decoded)
    evidence = {"decoded": decoded, "urls": urls, "payment_link": payment}

    if payment:
        summary = "QR code hides a payment link: " + decoded[0][:80]
    elif urls:
        summary = "QR code hides a link: " + urls[0][:80] + " (checking where it goes)"
    else:
        return CheckResult(check="qr", status=CheckStatus.PASS,
                           summary="QR code contains text only, no link", evidence=evidence)
    return CheckResult(check="qr", status=CheckStatus.WARN, summary=summary, evidence=evidence)
