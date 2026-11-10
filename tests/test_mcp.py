
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from tests.conftest import (
    register_and_login, auth_headers, create_trip, MOCK_AGENT_STATE_SUCCESS
)


class TestMCPClient:
    def test_returns_text_result(self):
        from app.agent.mcp_client import call_mcp_tool
        mock_content = MagicMock()
        mock_content.text = "Sunny, 22°C"
        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = False

        async def run():
            with patch("app.agent.mcp_client.stdio_client") as mock_stdio:
                mock_session = AsyncMock()
                mock_session.call_tool.return_value = mock_result
                mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
                with patch("app.agent.mcp_client.ClientSession") as mock_cs:
                    mock_cs.return_value.__aenter__.return_value = mock_session
                    return await call_mcp_tool("get_weather", {"destination": "Paris"})

        result = asyncio.run(run())
        assert result == "Sunny, 22°C"

    def test_propagates_is_error(self):
        from app.agent.mcp_client import call_mcp_tool
        mock_content = MagicMock()
        mock_content.text = "Geocoding failed"
        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = True

        async def run():
            with patch("app.agent.mcp_client.stdio_client") as mock_stdio:
                mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
                with patch("app.agent.mcp_client.ClientSession") as mock_cs:
                    mock_session = AsyncMock()
                    mock_session.call_tool.return_value = mock_result
                    mock_cs.return_value.__aenter__.return_value = mock_session
                    return await call_mcp_tool("get_weather", {"destination": "???"})

        result = asyncio.run(run())
        assert "Tool error" in result

    def test_empty_content_returns_message(self):
        from app.agent.mcp_client import call_mcp_tool
        mock_result = MagicMock()
        mock_result.content = []
        mock_result.isError = False

        async def run():
            with patch("app.agent.mcp_client.stdio_client") as mock_stdio:
                mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
                with patch("app.agent.mcp_client.ClientSession") as mock_cs:
                    mock_session = AsyncMock()
                    mock_session.call_tool.return_value = mock_result
                    mock_cs.return_value.__aenter__.return_value = mock_session
                    return await call_mcp_tool("get_weather", {"destination": "Paris"})

        result = asyncio.run(run())
        assert "no content" in result.lower()

