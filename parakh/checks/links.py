"""OWNER: Person 2. Link investigation. NEVER render or download page content."""
import ipaddress
import os
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

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


SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "ow.ly",
    "rb.gy", "shorturl.at", "tiny.cc", "buff.ly", "rebrand.ly",
}
MAX_HOPS = 5


def _is_private_host(host: str) -> bool:
    """True if this host is localhost / internal / unresolvable (unsafe to visit)."""
    try:
        if not host or host == "localhost":
            return True
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return True
        return False
    except Exception:
        return True  # cannot resolve -> treat as unsafe


def _fetch_headers(url: str):
    """Ask for ONE hop without downloading the page. Returns the response."""
    headers = {"User-Agent": "ParakhLinkChecker/1.0"}
    resp = requests.head(url, allow_redirects=False, timeout=5, headers=headers, stream=True)
    if resp.status_code in (403, 405, 501):
        resp.close()
        resp = requests.get(url, allow_redirects=False, timeout=5, headers=headers, stream=True)
    return resp


def check_link_destination(url: str) -> CheckResult:
    """Follow redirects (max 5 hops) without rendering or downloading the page."""
    try:
        if not url or not url.lower().startswith(("http://", "https://")):
            return CheckResult(check="link_destination", status=CheckStatus.UNVERIFIED,
                               summary="No valid link given.", evidence={"original": url})

        hops = [url]
        current = url
        too_many = False
        for _ in range(MAX_HOPS + 1):
            host = (urlparse(current).hostname or "").lower()
            if _is_private_host(host):
                return CheckResult(
                    check="link_destination", status=CheckStatus.UNVERIFIED,
                    summary="Blocked: this link points to an internal or unreachable address, so it was not opened.",
                    evidence={"original": url, "hops": hops, "blocked_host": host})
            resp = _fetch_headers(current)
            try:
                location = resp.headers.get("Location")
                is_redirect = resp.status_code in (301, 302, 303, 307, 308) and location
            finally:
                resp.close()
            if not is_redirect:
                break
            if len(hops) > MAX_HOPS:
                too_many = True
                break
            current = urljoin(current, location)
            hops.append(current)

        final_url = hops[-1]
        original_domain = get_domain(url)
        final_domain = get_domain(final_url)
        evidence = {"original": url, "final_url": final_url, "hops": hops,
                    "original_domain": original_domain, "final_domain": final_domain}

        if too_many:
            return CheckResult(check="link_destination", status=CheckStatus.WARN,
                               summary=f"The link jumps through more than {MAX_HOPS} redirects, which is suspicious.",
                               evidence=evidence)
        same_owner = (original_domain == final_domain
                      or original_domain.endswith("." + final_domain)
                      or final_domain.endswith("." + original_domain))
        if not same_owner:
            if original_domain in SHORTENERS:
                return CheckResult(check="link_destination", status=CheckStatus.WARN,
                                   summary=f"Shortened link hides its real destination: {final_domain}.",
                                   evidence=evidence)
            return CheckResult(check="link_destination", status=CheckStatus.WARN,
                               summary=f"The link redirects from {original_domain} to a different site: {final_domain}.",
                               evidence=evidence)
        return CheckResult(check="link_destination", status=CheckStatus.PASS,
                           summary="The link goes to the site it appears to go to.",
                           evidence=evidence)
    except Exception as exc:
        return CheckResult(check="link_destination", status=CheckStatus.UNVERIFIED,
                           summary=f"Could not follow the link ({type(exc).__name__}).",
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



SECOND_LEVEL = {"co", "com", "org", "net", "edu", "gov", "ac"}


def _registered_domain(name: str) -> str:
    """'careers.google.com' -> 'google.com'; 'portal.hec.gov.pk' -> 'hec.gov.pk'."""
    parts = name.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])

def check_domain_age(domain: str) -> CheckResult:
    """RDAP lookup: how old is this domain?"""
    name = _clean_domain(domain)
    try:
        if not name or "." not in name:
            return CheckResult(check="domain_age", status=CheckStatus.UNVERIFIED,
                               summary="No valid domain given.", evidence={"domain": domain})

        name = _registered_domain(name)
        resp = requests.get(f"https://rdap.org/domain/{name}", timeout=5,                            headers={"Accept": "application/rdap+json"})
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

# Known official domains: a short list we can extend. Key = brand name, value = real domains.
OFFICIAL_DOMAINS = {
    "hec": ["hec.gov.pk"],
    "nu": ["nu.edu.pk"],
    "fast": ["nu.edu.pk"],
    "nust": ["nust.edu.pk"],
    "comsats": ["comsats.edu.pk"],
    "lums": ["lums.edu.pk"],
    "giki": ["giki.edu.pk"],
    "pieas": ["pieas.edu.pk"],
    "iba": ["iba.edu.pk"],
    "punjab": ["punjab.gov.pk"],
    "ehsaas": ["ehsaas.gov.pk"],
    "chevening": ["chevening.org"],
    "fulbright": ["fulbright.org.pk", "fulbrightprogram.org"],
    "daad": ["daad.de"],
    "google": ["google.com"],
    "microsoft": ["microsoft.com"],
}

# Letter tricks scammers use: "rn" looks like "m", 0 looks like o, 1 looks like l.
CONFUSABLES = [("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("5", "s")]


def _squash(text: str) -> str:
    """'hec-gov-pk.com' -> 'hecgovpkcom' (only letters and digits)."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _undisguise(text: str) -> str:
    """Turn disguised letters back: 'rnicrosoft' -> 'microsoft'."""
    out = text.lower()
    for fake, real in CONFUSABLES:
        out = out.replace(fake, real)
    return out


def _is_official(domain: str, official: str) -> bool:
    """True if domain is the official one or a real subdomain of it."""
    return domain == official or domain.endswith("." + official)


def check_lookalike(domain: str, claimed_org: str | None = None) -> CheckResult:
    """Detect copycat domains of known organisations."""
    try:
        name = _clean_domain(domain)
        evidence = {"domain": name, "claimed_org": claimed_org}
        if not name or "." not in name:
            return CheckResult(check="lookalike", status=CheckStatus.UNVERIFIED,
                               summary="No valid domain given.", evidence=evidence)

        # 1. Punycode: disguised special characters.
        if "xn--" in name:
            evidence["reason"] = "punycode"
            return CheckResult(check="lookalike", status=CheckStatus.FAIL,
                               summary=f"{name} uses disguised special characters (punycode), a common copycat trick.",
                               evidence=evidence)

        # 2. Which brands could this domain be imitating?
        claimed = (claimed_org or "").lower()
        squashed = _squash(name)
        undisguised = _squash(_undisguise(name))
        suspects = []  # (brand, official_domain, reason)
        for brand, officials in OFFICIAL_DOMAINS.items():
            # Skip brands that are not relevant to this email.
            if claimed and brand not in claimed and not any(_squash(o) in squashed for o in officials):
                # still check below if brand word appears in the domain
                if brand not in name:
                    continue
            for official in officials:
                if _is_official(name, official):
                    return CheckResult(check="lookalike", status=CheckStatus.PASS,
                                       summary=f"{name} is an official domain of {brand.upper()}.",
                                       evidence={**evidence, "official_domain": official})
                if _squash(official) in squashed:
                    suspects.append((brand, official, "official name hidden inside another domain"))
                elif _squash(official) in undisguised:
                    suspects.append((brand, official, "letters swapped to look like the official name"))
                elif len(brand) >= 3 and brand in re.split(r"[^a-z0-9]+", name):
                    suspects.append((brand, official, "brand name inside an unrelated domain"))

        if suspects:
            brand, official, reason = suspects[0]
            evidence.update({"imitates": official, "reason": reason})
            strong = reason != "brand name inside an unrelated domain"
            return CheckResult(
                check="lookalike",
                status=CheckStatus.FAIL if strong else CheckStatus.WARN,
                summary=f"{name} may be imitating {official} ({reason}).",
                evidence=evidence)

        return CheckResult(check="lookalike", status=CheckStatus.PASS,
                           summary="No known lookalike pattern found (this does not prove it is official).",
                           evidence=evidence)
    except Exception as exc:
        return CheckResult(check="lookalike", status=CheckStatus.UNVERIFIED,
                           summary=f"Lookalike check failed ({type(exc).__name__}).",
                           evidence={"domain": domain, "claimed_org": claimed_org})