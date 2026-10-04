import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Absolute path to the server script
_SERVER_SCRIPT = str(Path(__file__).parent / "mcp_server.py")


async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Open a fresh MCP session, call one tool, return the text result.
    Uses stdio_client which handles subprocess lifecycle and protocol handshake.
    """
    params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else ""
