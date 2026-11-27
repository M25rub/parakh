"""
SHARED DATA CONTRACT. Everyone imports from here.
DO NOT change field names or types without telling all three teammates first.
If you need a new field, ADD it with a default value; never rename or delete.
"""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    PASS = "pass"              # evidence says this looks fine
    WARN = "warn"              # mildly suspicious
    FAIL = "fail"              # strong red flag
    UNVERIFIED = "unverified"  # the check could not run (API down, missing data). Never guess.
    SKIPPED = "skipped"        # the agent decided this check was not needed


class CheckResult(BaseModel):
    """Returned by EVERY investigation check (Person 2)."""
    check: str                 # "headers" | "link_destination" | "safe_browsing" | "domain_age" |
                               # "lookalike" | "qr" | "fee_pressure" | "official_source" | "memory"
    status: CheckStatus
    summary: str               # ONE plain-English sentence shown in the UI
    evidence: dict = Field(default_factory=dict)  # raw facts, e.g. {"dmarc": "fail"}


class Risk(str, Enum):
    VERIFIED = "verified"
    SUSPICIOUS = "suspicious"
    LIKELY_SCAM = "likely_scam"
    NOT_OPPORTUNITY = "not_opportunity"


# Gmail labels the agent applies (Person 3 uses these exact strings)
GMAIL_LABELS = {
    Risk.VERIFIED: "Parakh/Verified",
    Risk.SUSPICIOUS: "Parakh/Suspicious",
    Risk.LIKELY_SCAM: "Parakh/Likely scam",
}


class EmailInput(BaseModel):
    """One email, as the agent sees it (after privacy redaction)."""
    email_id: str
    sender: str
    reply_to: Optional[str] = None
    subject: str = ""
    body_text: str = ""
    raw_headers: str = ""
    links: list[str] = Field(default_factory=list)
    qr_images_b64: list[str] = Field(default_factory=list)  # base64 PNG/JPG
    received_at: Optional[datetime] = None


class Deadline(BaseModel):
    title: str
    date: str                          # ISO format YYYY-MM-DD
    calendar_event_created: bool = False


class Verdict(BaseModel):
    """The agent's final answer for ONE email (Person 3 produces, Person 1 displays)."""
    email_id: str
    subject: str
    sender: str
    risk: Risk
    confidence: float = Field(ge=0.0, le=1.0)
    checks: list[CheckResult] = Field(default_factory=list)
    explanation: str                   # 1-3 sentences for the student
    deadline: Optional[Deadline] = None
    gmail_label_applied: Optional[str] = None
    memory_hit: bool = False


class TraceEvent(BaseModel):
    """One line of the live 'agent trace' shown in the UI."""
    kind: Literal["thinking", "tool_call", "tool_result", "mcp_call", "decision", "error", "info"]
    message: str
    tool: Optional[str] = None
    via_mcp: Optional[str] = None      # "gmail" | "calendar" | "parakh-checks" | None
    timestamp: datetime = Field(default_factory=datetime.now)


class ScanResult(BaseModel):
    verdicts: list[Verdict]
    trace: list[TraceEvent]
    emails_scanned: int
    mock: bool = False                 # True = fake demo data. The UI MUST show a "mock data" badge.
