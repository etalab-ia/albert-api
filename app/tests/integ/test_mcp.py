import pytest
import respx
import httpx
from fastapi.testclient import TestClient

from app.schemas.chat import ChatCompletion
from app.tests.integ.fixtures.fixtures import generate_mocked_mcp_bridge_tools, generate_mocked_llm_response
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__AGENTS_TOOLS, ENDPOINT__AGENTS_COMPLETIONS


@pytest.mark.usefixtures("client")
class TestMCP:
    def test_mcp_chat_completions_route_returns_chat_completion_with_tool_call(self, client: TestClient):
        params = {
            "model": "albert-large",
            "messages": [{"role": "user", "content": "Quelles sont les données sur les accidents de la route ?"}],
            "tools": ["search_datasets", "get_dataset_details"],
            "tool_choice": "auto",
            "stream": False,
            "n": 1,
            "max_tokens": 2000,
        }
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__AGENTS_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())

    def test_mcp_list_tools_return_tool_list(self, client: TestClient):
        # WHEN
        response = client.get(url=f"/v1{ENDPOINT__AGENTS_TOOLS}")

        # THEN
        assert response.status_code == 200, response.text


class TestIntegrationMCP:
    @respx.mock
    def test_mcp_endpoint_returns_answer_with_tool_call(self, client: TestClient):
        params = {
            "model": "albert-large",
            "messages": [{"role": "user", "content": "Donne moi la météo à Miami"}],
            "stream": False,
            "tools": ["get_forecast"],
            "n": 1,
            "max_tokens": 1000,
        }
        tools_response = {}
        llm_response_after_tool_call = generate_mocked_llm_response(
            choices=[
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": "Message après tool call",
                        "role": "assistant",
                        "function_call": None,
                        "tool_calls": [],
                    },
                }
            ]
        )

        llm_response_triggering_tool_call = generate_mocked_llm_response(
            choices=[
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "function_call": None,
                        "tool_calls": [
                            {
                                "id": "CIn3wUdeC",
                                "function": {"arguments": '{"latitude": 25.79, "longitude": -80.13}', "name": "get_forecast"},
                                "type": "function",
                            }
                        ],
                    },
                }
            ]
        )
        tool_call_response = {"_meta": None, "content": [{"type": "text", "text": "tool call response", "annotations": None}], "isError": False}
        route = respx.post("https://albert.api.etalab.gouv.fr/v1/chat/completions")

        route.side_effect = [
            httpx.Response(status_code=200, json=llm_response_triggering_tool_call),
            httpx.Response(status_code=200, json=llm_response_after_tool_call),
        ]

        mcp_tools_route = respx.get(url=settings.mcp.mcp_bridge_url + "/mcp/tools").mock(
            return_value=httpx.Response(status_code=200, json=tools_response)
        )

        mcp_call_route = respx.post(url=settings.mcp.mcp_bridge_url + "/mcp/tools/get_forecast/call").mock(
            return_value=httpx.Response(status_code=200, json=tool_call_response)
        )

        # WHEN
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__AGENTS_COMPLETIONS}", json=params)

        # THEN
        assert response.status_code == 200, response.text
        assert route.call_count == 2
        mcp_tools_route.calls.assert_called_once()
        mcp_call_route.calls.assert_called_once()
        assert mcp_call_route.calls[0].request.content == b'{"latitude":25.79,"longitude":-80.13}'
        ChatCompletion(**response.json())

    @respx.mock
    def test_mcp_list_tools_return_tool_list(self, client: TestClient):
        # GIVEN
        tools_response = generate_mocked_mcp_bridge_tools()
        mcp_tools_route = respx.get(url=settings.mcp.mcp_bridge_url + "/mcp/tools").mock(
            return_value=httpx.Response(status_code=200, json=tools_response)
        )

        # WHEN
        response = client.get(url=f"/v1{ENDPOINT__AGENTS_TOOLS}")

        # THEN
        assert response.status_code == 200, response.text
        mcp_tools_route.calls.assert_called_once()
