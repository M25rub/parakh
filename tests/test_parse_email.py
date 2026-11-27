from pathlib import Path

from parakh.parse_email import html_to_text, parse_raw_email

DEMO = Path(__file__).resolve().parents[1] / "demo_emails"


def test_hidden_html_link_is_found():
    raw = ("From: a@b.com\nSubject: Hi\nContent-Type: text/html\n\n"
           "<p>Apply at <a href='https://evil-site.xyz/pay'>www.hec.gov.pk</a></p>")
    e = parse_raw_email(raw)
    assert "https://evil-site.xyz/pay" in e.links
    assert "www.hec.gov.pk [https://evil-site.xyz/pay]" in e.body_text


def test_demo_email_with_qr_image():
    e = parse_raw_email((DEMO / "2_qr_poster.eml").read_text())
    assert len(e.qr_images_b64) == 1 and "gmail.com" in e.sender


def test_broken_email_never_crashes():
    e = parse_raw_email("this is not an email \x00 at all")
    assert e.email_id == "pasted-1"


def test_html_to_text():
    assert html_to_text("<p>A&amp;B</p><br><b>C</b>").split() == ["A&B", "C"]
