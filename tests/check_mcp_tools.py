"""Manual check: does the parakh-checks MCP server expose all 8 tools?
Run:  python tests\\check_mcp_tools.py
"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED = {
    "check_headers", "extract_links", "check_link_destination", "check_safe_browsing",
    "check_domain_age", "check_lookalike", "decode_qr", "check_fee_pressure",
}


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "parakh.mcp_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            print("Tools the agent sees:", sorted(names))
            print("Missing:", sorted(EXPECTED - names) or "none")

            result = await session.call_tool(
                "check_lookalike", {"domain": "hec-gov-pk.com", "claimed_org": "HEC"})
            print("Test call check_lookalike ->", result.content[0].text)


asyncio.run(main())