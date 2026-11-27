"""OWNER: Person 1. QR decoding."""
from ..schemas import CheckResult, CheckStatus


def decode_qr(image_b64: str) -> CheckResult:
    """
    TODO(Person 1): decode with OpenCV (opencv-python-headless, no system libs needed):
        cv2.QRCodeDetector().detectAndDecodeMulti(img)
    Base64 -> numpy array -> cv2.imdecode.
    QR found -> status WARN if it contains a payment link or a URL, else PASS.
    evidence: {"decoded": ["https://..."]}. No QR found -> SKIPPED.
    The agent then sends each decoded URL through the link checks.
    """
    return CheckResult(check="qr", status=CheckStatus.UNVERIFIED,
                       summary="QR decoding not implemented yet")
