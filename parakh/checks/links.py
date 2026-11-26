"""OWNER: Person 2. Link investigation. NEVER render or download page content."""
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
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
    """Ask Google Safe Browsing if this URL is on the unsafe list."""
    try:
        key = os.environ.get("SAFE_BROWSING_API_KEY", "").strip()
        if not key:
            return CheckResult(check="safe_browsing", status=CheckStatus.UNVERIFIED,
                               summary="Safe Browsing key not set, so this link was not checked.",
                               evidence={"url": url})
        if not url or not url.lower().startswith(("http://", "https://")):
            return CheckResult(check="safe_browsing", status=CheckStatus.UNVERIFIED,
                               summary="No valid link given.", evidence={"url": url})

        body = {
            "client": {"clientId": "parakh", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING",
                                "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }
        resp = requests.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find",
            params={"key": key}, json=body, timeout=5)
        if resp.status_code != 200:
            return CheckResult(check="safe_browsing", status=CheckStatus.UNVERIFIED,
                               summary="Safe Browsing could not be reached.",
                               evidence={"url": url, "http_status": resp.status_code})

        matches = resp.json().get("matches", [])
        if matches:
            kinds = sorted({m.get("threatType", "UNKNOWN") for m in matches})
            return CheckResult(check="safe_browsing", status=CheckStatus.FAIL,
                               summary="Google lists this link as unsafe: " + ", ".join(kinds) + ".",
                               evidence={"url": url, "threats": kinds})
        return CheckResult(check="safe_browsing", status=CheckStatus.PASS,
                           summary="Not on Google's unsafe list.", evidence={"url": url})
    except Exception as exc:
        return CheckResult(check="safe_browsing", status=CheckStatus.UNVERIFIED,
                           summary=f"Safe Browsing check failed ({type(exc).__name__}).",
                           evidence={"url": url})

def _clean_domain(value: str) -> str:
    """'https://www.Site.com/x' or 'Site.com' -> 'site.com'."""
    value = (value or "").strip().lower()
    if "://" in value:
        value = urlparse(value).hostname or ""
    return value.split("/")[0].split(":")[0].removeprefix("www.")


def check_domain_age(domain: str) -> CheckResult:
    """RDAP lookup: how old is this domain?"""
    name = _clean_domain(domain)
    try:
        if not name or "." not in name:
            return CheckResult(check="domain_age", status=CheckStatus.UNVERIFIED,
                               summary="No valid domain given.", evidence={"domain": domain})

        resp = requests.get(f"https://rdap.org/domain/{name}", timeout=5,
                            headers={"Accept": "application/rdap+json"})
        if resp.status_code != 200:
            return CheckResult(check="domain_age", status=CheckStatus.UNVERIFIED,
                               summary=f"Domain age is not available for {name}.",
                               evidence={"domain": name, "http_status": resp.status_code})

        registered = None
        for event in resp.json().get("events", []):
            if event.get("eventAction") == "registration":
                registered = event.get("eventDate")
                break
        if not registered:
            return CheckResult(check="domain_age", status=CheckStatus.UNVERIFIED,
                               summary=f"No registration date found for {name}.",
                               evidence={"domain": name})

        reg_date = datetime.fromisoformat(registered.replace("Z", "+00:00"))
        if reg_date.tzinfo is None:
            reg_date = reg_date.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - reg_date).days
        evidence = {"domain": name, "registered": reg_date.date().isoformat(), "age_days": age_days}

        if age_days < 90:
            return CheckResult(check="domain_age", status=CheckStatus.FAIL,
                               summary=f"{name} was registered only {age_days} days ago (brand new).",
                               evidence=evidence)
        if age_days < 365:
            return CheckResult(check="domain_age", status=CheckStatus.WARN,
                               summary=f"{name} is less than a year old ({age_days} days).",
                               evidence=evidence)
        return CheckResult(check="domain_age", status=CheckStatus.PASS,
                           summary=f"{name} has existed for {age_days // 365} year(s).",
                           evidence=evidence)
    except Exception as exc:  # timeout, no internet, bad JSON...
        return CheckResult(check="domain_age", status=CheckStatus.UNVERIFIED,
                           summary=f"Could not look up the domain age ({type(exc).__name__}).",
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
