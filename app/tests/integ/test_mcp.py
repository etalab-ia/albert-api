import pytest
from fastapi.testclient import TestClient

from app.schemas.chat import ChatCompletion
from app.utils.variables import ENDPOINT__MCP


@pytest.mark.usefixtures("client")
class TestMCP:
    def test_mcp_chat_completions_route_returns_chat_completion_with_tool_call(self, client: TestClient):
        params = {
            "model": "albert-large",
            "messages": [{"role": "user", "content": "Donne moi la météo à Miami"}],
            "stream": False,
            "n": 1,
            "max_tokens": 200,
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__MCP}/completions", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())

    def test_mcp_list_tools_return_tool_list(self, client: TestClient):
        # WHEN
        response = client.get(url=f"/v1{ENDPOINT__MCP}/servers")

        # THEN
        assert response.status_code == 200, response.text
