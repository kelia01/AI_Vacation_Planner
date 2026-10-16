import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_SCRIPT = str(Path(__file__).parent / "mcp_server.py")


async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            if not result.content:
                return f"Tool '{tool_name}' returned no content."

            text = result.content[0].text

            if result.isError:
                return f"Tool error: {text}"

            return text
