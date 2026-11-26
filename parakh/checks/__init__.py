"""Investigation checks (Person 2). Pure Python, no AI. Every check returns a CheckResult."""
from .content import check_fee_pressure
from .headers import check_headers
from .links import (check_domain_age, check_link_destination, check_lookalike,
                    check_safe_browsing, extract_links, get_domain)
from .privacy import redact
from .qr import decode_qr

__all__ = ["check_headers", "extract_links", "get_domain", "check_link_destination",
           "check_safe_browsing", "check_domain_age", "check_lookalike",
           "decode_qr", "check_fee_pressure", "redact"]
