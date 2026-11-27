"""Prints the tool names that workspace-mcp (Gmail + Calendar) gives the agent.
Run from the repo root:  python list_tools.py
Needs GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, USER_GOOGLE_EMAIL in .env"""
import asyncio

from dotenv import load_dotenv

load_dotenv()

from parakh.agent import workspace_mcp  # noqa: E402


async def main() -> None:
    toolset = workspace_mcp()
    try:
        tools = await toolset.get_tools()
        for t in sorted(tools, key=lambda x: x.name):
            print(t.name)
        print(f"\n{len(tools)} tools found")
    finally:
        await toolset.close()


asyncio.run(asyncio.wait_for(main(), timeout=120))