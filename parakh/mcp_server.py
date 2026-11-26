"""
OWNER: Person 2.
The "parakh-checks" MCP server. It exposes every investigation check as an MCP tool,
so the agent (Person 3) calls them through MCP. This guarantees at least one MCP server
works everywhere, including the deployed app, even if Gmail login has problems.

Run standalone to test:  python -m parakh.mcp_server
Every tool returns CheckResult.model_dump(mode="json") so the shape never changes.
"""
from mcp.server.fastmcp import FastMCP

from . import checks

mcp = FastMCP("parakh-checks")


@mcp.tool()
def check_headers(raw_headers: str, claimed_sender: str) -> dict:
    """Check SPF/DKIM/DMARC results, From vs Reply-To mismatch and free-mail senders."""
    return checks.check_headers(raw_headers, claimed_sender).model_dump(mode="json")


@mcp.tool()
def extract_links(text: str) -> list[str]:
    """Return every http(s) link in the email text."""
    return checks.extract_links(text)


@mcp.tool()
def check_link_destination(url: str) -> dict:
    """Follow redirects safely (without opening the page) and return the final destination."""
    return checks.check_link_destination(url).model_dump(mode="json")


@mcp.tool()
def check_safe_browsing(url: str) -> dict:
    """Ask Google Safe Browsing whether the URL is known to be unsafe."""
    return checks.check_safe_browsing(url).model_dump(mode="json")


@mcp.tool()
def check_domain_age(domain: str) -> dict:
    """Find when the domain was registered. Very new domains are a red flag."""
    return checks.check_domain_age(domain).model_dump(mode="json")


@mcp.tool()
def check_lookalike(domain: str, claimed_org: str = "") -> dict:
    """Detect domains that imitate a real organisation (e.g. hec-gov-pk.com)."""
    return checks.check_lookalike(domain, claimed_org or None).model_dump(mode="json")


@mcp.tool()
def decode_qr(image_b64: str) -> dict:
    """Decode a QR code image (base64) and return the hidden link(s)."""
    return checks.decode_qr(image_b64).model_dump(mode="json")


@mcp.tool()
def check_fee_pressure(text: str) -> dict:
    """Detect fee requests, deadline pressure and payments to personal wallets."""
    return checks.check_fee_pressure(text).model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()  # stdio transport (what the ADK agent uses)
