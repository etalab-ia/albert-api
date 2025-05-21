import logging
import os
from uuid import uuid4

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.mcp.fixtures import generate_mocked_llm_response, generate_mocked_mcp_bridge_tools
from app.schemas.chat import ChatCompletion
from app.schemas.models import ModelType
from app.utils.variables import ENDPOINT__COLLECTIONS, ENDPOINT__DOCUMENTS, ENDPOINT__FILES, \
    ENDPOINT__MODELS, ENDPOINT__MCP


@pytest.fixture(scope="module")
def setup(client: TestClient):
    # Get a language model
    response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}")
    assert response.status_code == 200, response.text
    response_json = response.json()

    model = [model for model in response_json["data"] if model["type"] == ModelType.TEXT_GENERATION][0]
    MODEL_ID = model["id"]

    logging.info(msg=f"test model ID: {MODEL_ID}")

    # Create a collection
    response = client.post_without_permissions(url=f"/v1{ENDPOINT__COLLECTIONS}",
                                               json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    file_path = "app/tests/assets/json.json"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/json")}
        data = {"request": '{"collection": "%s", "chunker": {"args": {"chunk_size": 1000}}}' % COLLECTION_ID}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__FILES}", data=data, files=files)
        file.close()
    assert response.status_code == 201, response.text

    # Get document IDS
    response = client.get_without_permissions(url=f"/v1{ENDPOINT__DOCUMENTS}", params={"collection": COLLECTION_ID})
    DOCUMENT_IDS = [row["id"] for row in response.json()["data"]]

    yield MODEL_ID, DOCUMENT_IDS, COLLECTION_ID


@pytest.mark.usefixtures("client", "setup")
class TestMCP:
    def test_mcp_endpoint_returns_chat_completion_answer_when_no_tool_is_needed(self, client: TestClient, setup):
        MODEL_ID, DOCUMENT_IDS, COLLECTION_ID = setup
        params = {"model": MODEL_ID, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": False,
                  "n": 1, "max_tokens": 10}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__MCP}", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())  # test output format

    def test_end_to_end(self, client: TestClient, setup):
        MODEL_ID, _, _ = setup

        params = {"model": "albert-large", "messages": [{"role": "user", "content": "Donne moi la météo à Miami"}],
                  "stream": False, "n": 1, "max_tokens": 200}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__MCP}", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())  # test output format

    @respx.mock
    def test_mcp_endpoint_returns_answer_with_tool_call(self, client: TestClient, setup):
        params = {"model": "albert-large", "messages": [{"role": "user", "content": "Donne moi la météo à Miami"}],
                  "stream": False, "n": 1, "max_tokens": 1000}
        tools_response = {}
        llm_response_after_tool_call = generate_mocked_llm_response(choices=[{
                "finish_reason": "stop",
                "message": {
                    "content": "Message après tool call",
                    "role": "assistant",
                    "function_call": None,
                    "tool_calls": [],
                }
            }])

        llm_response_triggering_tool_call = generate_mocked_llm_response(choices=[{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "function_call": None,
                "tool_calls": [{"id": "CIn3wUdeC",
                             "function": {"arguments": '{"latitude": 25.79, "longitude": -80.13}',
                                          "name": "get_forecast"},
                             "type": "function"}]}}])
        tool_call_response = {
            "_meta": None,
            "content": [{
                "type": "text",
                "text": "tool call response",
                "annotations": None
            }],
            "isError": False
        }
        route = respx.post('https://albert.api.staging.etalab.gouv.fr/v1/chat/completions')

        route.side_effect = [
            httpx.Response(status_code=200, json=llm_response_triggering_tool_call),
            httpx.Response(status_code=200, json=llm_response_after_tool_call),
        ]

        mcp_tools_route = respx.get(url="http://localhost:9000/mcp/tools").mock(
        return_value=httpx.Response(status_code=200, json=tools_response))

        mcp_call_route = respx.post(url="http://localhost:9000/mcp/tools/get_forecast/call").mock(return_value=httpx.Response(status_code=200, json=tool_call_response))

        # WHEN
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__MCP}", json=params)

        # THEN
        assert response.status_code == 200, response.text
        assert route.call_count == 2
        mcp_tools_route.calls.assert_called_once()
        mcp_call_route.calls.assert_called_once()
        assert mcp_call_route.calls[0].request.content == b'{"latitude":25.79,"longitude":-80.13}'
        ChatCompletion(**response.json())


    @respx.mock
    def test_mcp_list_tools_return_tool_list(self, client: TestClient, setup):
        # GIVEN
        tools_response = generate_mocked_mcp_bridge_tools()
        mcp_tools_route = respx.get(url="http://localhost:9000/mcp/tools").mock(
            return_value=httpx.Response(status_code=200, json=tools_response)
        )

        # WHEN
        response = client.get(url=f"/v1{ENDPOINT__MCP}/tool_list")

        # THEN
        assert response.status_code == 200, response.text
        mcp_tools_route.calls.assert_called_once()

