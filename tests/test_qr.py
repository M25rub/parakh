import base64

import cv2
import numpy as np

from parakh.checks.qr import decode_qr


def _qr_b64(text: str) -> str:
    """Make a QR image in memory (OpenCV can create QR codes too), return it as base64 PNG."""
    img = cv2.QRCodeEncoder.create().encode(text)
    img = cv2.resize(img, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
    img = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    return base64.b64encode(cv2.imencode(".png", img)[1].tobytes()).decode()


def test_qr_with_link():
    r = decode_qr(_qr_b64("https://hec-scholarships.co/pay"))
    assert r.status == "warn"
    assert "https://hec-scholarships.co/pay" in r.evidence["decoded"]


def test_qr_text_only():
    assert decode_qr(_qr_b64("Hello students")).status == "pass"


def test_no_qr():
    blank = np.full((200, 200, 3), 255, np.uint8)
    b64 = base64.b64encode(cv2.imencode(".png", blank)[1].tobytes()).decode()
    assert decode_qr(b64).status == "skipped"


def test_not_an_image():
    assert decode_qr("bm90IGFuIGltYWdl").status == "unverified"
