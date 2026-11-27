"""
OWNER: Person 2. Shared scam memory (fingerprints only, NEVER student data).

MEMORY_BACKEND=local  -> memory.json file (default, for development)
MEMORY_BACKEND=firestore -> Firestore collection "fingerprints"
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOCAL_FILE = Path(os.getenv("MEMORY_FILE", "memory.json"))


def fingerprint(indicator: str) -> str:
    """Normalise an indicator (domain, final URL, sender address) and hash it."""
    return hashlib.sha256(indicator.strip().lower().encode()).hexdigest()[:32]


def _load() -> dict:
    return json.loads(LOCAL_FILE.read_text()) if LOCAL_FILE.exists() else {}


def lookup(indicators: list[str]) -> dict | None:
    """
    Return the stored record for the first indicator already known, or None.
    Record: {"indicator", "type", "risk", "report_count", "first_seen", "last_seen", "summary"}
    TODO(Person 2): Firestore branch.
    """
    db = _load()
    for ind in indicators:
        rec = db.get(fingerprint(ind))
        if rec:
            return rec
    return None


def save(indicators: list[str], risk: str, summary: str, indicator_type: str = "domain") -> None:
    """
    Save/increment fingerprints. Only save when risk is "likely_scam" or "suspicious".
    TODO(Person 2): Firestore branch (doc id = fingerprint, increment report_count).
    """
    now = datetime.now(timezone.utc).isoformat()
    db = _load()
    for ind in indicators:
        key = fingerprint(ind)
        rec = db.get(key, {"indicator": ind, "type": indicator_type, "report_count": 0,
                           "first_seen": now})
        rec.update({"risk": risk, "summary": summary, "last_seen": now,
                    "report_count": rec["report_count"] + 1})
        db[key] = rec
    LOCAL_FILE.write_text(json.dumps(db, indent=2))
