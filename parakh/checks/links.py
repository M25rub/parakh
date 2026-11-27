"""OWNER: Person 2. Link investigation. NEVER render or download page content."""
import re
from urllib.parse import urlparse

from ..schemas import CheckResult, CheckStatus

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)


def extract_links(text: str) -> list[str]:
    """Return unique http(s) links found in text, in order."""
    seen, out = set(), []
    for u in URL_RE.findall(text or ""):
        u = u.rstrip(".,;")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def get_domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def check_link_destination(url: str) -> CheckResult:
    """
    Follow redirects (max 5 hops, timeout 5s) WITHOUT rendering the page.
    TODO(Person 2): use requests with allow_redirects, stream=True, close the response.
    Block private/internal IPs (localhost, 10.x, 192.168.x) for safety.
    evidence: {"original": url, "final_url": "...", "hops": [...]}
    Shortened link that ends on a different domain -> WARN.
    """
    return CheckResult(check="link_destination", status=CheckStatus.UNVERIFIED,
                       summary="Link destination check not implemented yet",
                       evidence={"original": url})


def check_safe_browsing(url: str) -> CheckResult:
    """
    TODO(Person 2): Google Safe Browsing v4 Lookup API.
    POST https://safebrowsing.googleapis.com/v4/threatMatches:find?key=SAFE_BROWSING_API_KEY
    Match found -> FAIL. No match -> PASS (summary: "Not on Google's unsafe list").
    API error / no key -> UNVERIFIED.
    """
    return CheckResult(check="safe_browsing", status=CheckStatus.UNVERIFIED,
                       summary="Safe Browsing check not implemented yet")


def check_domain_age(domain: str) -> CheckResult:
    """
    TODO(Person 2): RDAP lookup, GET https://rdap.org/domain/<domain>
    Find events[] with eventAction == "registration".
    < 90 days old -> FAIL, < 1 year -> WARN, older -> PASS.
    Some country domains (e.g. .pk) may not support RDAP -> UNVERIFIED, do not guess.
    evidence: {"domain": ..., "registered": "2026-11-17", "age_days": 9}
    """
    return CheckResult(check="domain_age", status=CheckStatus.UNVERIFIED,
                       summary="Domain age check not implemented yet",
                       evidence={"domain": domain})


def check_lookalike(domain: str, claimed_org: str | None = None) -> CheckResult:
    """
    TODO(Person 2): detect lookalike domains: punycode (xn--), digit/letter swaps
    (0/o, 1/l, rn/m), extra words ("hec-gov-pk.com"), brand name inside an unrelated domain.
    Keep a small dict of known official domains (hec.gov.pk, nu.edu.pk, ...).
    """
    return CheckResult(check="lookalike", status=CheckStatus.UNVERIFIED,
                       summary="Lookalike check not implemented yet",
                       evidence={"domain": domain, "claimed_org": claimed_org})
