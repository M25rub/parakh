"""
OWNER: Person 2. Shared scam memory (fingerprints only, NEVER student data).

MEMORY_BACKEND=local  -> memory.json file (default, for development)
MEMORY_BACKEND=firestore -> Firestore collection "fingerprints"
If Firestore fails for any reason, we fall back to the local file (never crash).
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOCAL_FILE = Path(os.getenv("MEMORY_FILE", "memory.json"))
COLLECTION = "fingerprints"
SAVEABLE_RISKS = {"likely_scam", "suspicious"}


def fingerprint(indicator: str) -> str:
    """Normalise an indicator (domain, final URL, sender address) and hash it."""
    return hashlib.sha256(indicator.strip().lower().encode()).hexdigest()[:32]


def _backend() -> str:
    return os.getenv("MEMORY_BACKEND", "local").strip().lower()


# ---------------- local JSON backend ----------------
def _load() -> dict:
    try:
        return json.loads(LOCAL_FILE.read_text()) if LOCAL_FILE.exists() else {}
    except Exception:
        return {}


def _lookup_local(indicators: list[str]) -> dict | None:
    db = _load()
    for ind in indicators:
        rec = db.get(fingerprint(ind))
        if rec:
            return rec
    return None


def _save_local(indicators, risk, summary, indicator_type, now) -> None:
    db = _load()
    for ind in indicators:
        key = fingerprint(ind)
        rec = db.get(key, {"indicator": ind, "type": indicator_type, "report_count": 0,
                           "first_seen": now})
        rec.update({"risk": risk, "summary": summary, "last_seen": now,
                    "report_count": rec["report_count"] + 1})
        db[key] = rec
    LOCAL_FILE.write_text(json.dumps(db, indent=2))


# ---------------- Firestore backend ----------------
def _firestore_client():
    from google.cloud import firestore  # imported here so local mode never needs it
    return firestore.Client()


def _lookup_firestore(indicators: list[str]) -> dict | None:
    client = _firestore_client()
    for ind in indicators:
        snap = client.collection(COLLECTION).document(fingerprint(ind)).get()
        if snap.exists:
            return snap.to_dict()
    return None


def _save_firestore(indicators, risk, summary, indicator_type, now) -> None:
    from google.cloud import firestore
    client = _firestore_client()
    for ind in indicators:
        ref = client.collection(COLLECTION).document(fingerprint(ind))
        # set(merge=True) creates the doc if missing, and Increment is safe
        # even when two students report at the same moment.
        ref.set({
            "indicator": ind, "type": indicator_type, "risk": risk,
            "summary": summary, "last_seen": now,
            "report_count": firestore.Increment(1),
        }, merge=True)
        # first_seen is only written once (when the doc has no first_seen yet).
        snap = ref.get()
        if snap.exists and not (snap.to_dict() or {}).get("first_seen"):
            ref.set({"first_seen": now}, merge=True)


# ---------------- public functions (same signatures as the contract) ----------------
def lookup(indicators: list[str]) -> dict | None:
    """
    Return the stored record for the first indicator already known, or None.
    Record: {"indicator", "type", "risk", "report_count", "first_seen", "last_seen", "summary"}
    """
    try:
        indicators = [i for i in (indicators or []) if i and i.strip()]
        if not indicators:
            return None
        if _backend() == "firestore":
            try:
                return _lookup_firestore(indicators)
            except Exception:
                pass  # fall back to local
        return _lookup_local(indicators)
    except Exception:
        return None


def save(indicators: list[str], risk: str, summary: str, indicator_type: str = "domain") -> None:
    """Save/increment fingerprints. Only saves "likely_scam" or "suspicious"."""
    try:
        if risk not in SAVEABLE_RISKS:
            return
        indicators = [i for i in (indicators or []) if i and i.strip()]
        if not indicators:
            return
        summary = (summary or "")[:200]
        now = datetime.now(timezone.utc).isoformat()
        if _backend() == "firestore":
            try:
                _save_firestore(indicators, risk, summary, indicator_type, now)
                return
            except Exception:
                pass  # fall back to local
        _save_local(indicators, risk, summary, indicator_type, now)
    except Exception:
        pass  # memory must never crash the agent