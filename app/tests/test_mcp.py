import logging
import os
from uuid import uuid4

import httpx
import pytest
import responses
import respx
from fastapi.testclient import TestClient

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
        params = {"model": "albert-large", "messages": [{"role": "user", "content": "Donne moi la météo à Miami"}],
                  "stream": False, "n": 1, "max_tokens": 1000}
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__MCP}", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())  # test output format

    @respx.mock
    @responses.activate
    def test_mcp_endpoint_returns_answer_with_tool_call(self, client: TestClient, setup):
        params = {"model": "albert-large", "messages": [{"role": "user", "content": "Donne moi la météo à Miami"}],
                  "stream": False, "n": 1, "max_tokens": 1000}
        tools_response = {
            "weather": {
                "_meta": None,
                "nextCursor": None,
                "tools": [{
                    "name": "get_alerts",
                    "description": "Get weather alerts for a US state.\n\n    Args:\n        state: Two-letter US state code (e.g. CA, NY)\n    ",
                    "inputSchema": {
                        "properties": {
                            "state": {
                                "title": "State",
                                "type": "string"
                            }
                        },
                        "required": ["state"],
                        "title": "get_alertsArguments",
                        "type": "object"
                    },
                    "annotations": None
                }, {
                    "name": "get_forecast",
                    "description": "Get weather forecast for a location.\n\n    Args:\n        latitude: Latitude of the location\n        longitude: Longitude of the location\n    ",
                    "inputSchema": {
                        "properties": {
                            "latitude": {
                                "title": "Latitude",
                                "type": "number"
                            },
                            "longitude": {
                                "title": "Longitude",
                                "type": "number"
                            }
                        },
                        "required": ["latitude", "longitude"],
                        "title": "get_forecastArguments",
                        "type": "object"
                    },
                    "annotations": None
                }]
            }
        }

        tool_call_response = {
            "_meta": None,
            "content": [{
                "type": "text",
                "text": "\nToday:\nTemperature: 85°F\nWind: 3 to 8 mph SE\nForecast: Sunny, with a high near 85. Southeast wind 3 to 8 mph.\n\n---\n\nTonight:\nTemperature: 79°F\nWind: 8 mph SE\nForecast: Mostly clear, with a low around 79. Southeast wind around 8 mph.\n\n---\n\nSaturday:\nTemperature: 86°F\nWind: 6 to 9 mph S\nForecast: Mostly sunny, with a high near 86. South wind 6 to 9 mph.\n\n---\n\nSaturday Night:\nTemperature: 79°F\nWind: 6 to 10 mph SE\nForecast: Mostly clear, with a low around 79. Southeast wind 6 to 10 mph.\n\n---\n\nSunday:\nTemperature: 86°F\nWind: 6 to 9 mph SE\nForecast: Sunny, with a high near 86. Southeast wind 6 to 9 mph.\n",
                "annotations": None
            }],
            "isError": False
        }
        expected_body = {"id": "chatcmpl-9361ad51d8f04a46a6bb83ea54d2f25c", "choices": [
            {"finish_reason": "tool_calls", "index": 0, "logprobs": None,
             "message": {"content": None, "refusal": None, "role": "assistant", "audio": None, "function_call": None,
                         "tool_calls": [{"id": "CIn3wUdeC",
                                         "function": {"arguments": "{\"latitude\": 25.7617, \"longitude\": -80.1918}",
                                                      "name": "get_forecast"}, "type": "function"}],
                         "reasoning_content": None}, "stop_reason": None}]}
        expected_body_2 = {
            "id": "chatcmpl-20c6921dee434f7d8dacff216adbe52e",
            "choices": [{
                "finish_reason": "stop",
                "index": 0,
                "logprobs": None,
                "message": {
                    "content": "Message après tool call",
                    "refusal": None,
                    "role": "assistant",
                    "audio": None,
                    "function_call": None,
                    "tool_calls": [],
                    "reasoning_content": None
                },
                "stop_reason": None
            }],
            "created": 1747410275,
            "model": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
            "object": "chat.completion",
            "service_tier": None,
            "system_fingerprint": None,
            "usage": {
                "completion_tokens": 36,
                "prompt_tokens": 241,
                "total_tokens": 277,
                "completion_tokens_details": None,
                "prompt_tokens_details": None
            },
            "search_results": [],
            "prompt_logprobs": None
        }
        route = respx.post('https://albert.api.staging.etalab.gouv.fr/v1/chat/completions')

        route.side_effect = [
            httpx.Response(status_code=200, json=expected_body),
            httpx.Response(status_code=200, json=expected_body_2),
        ]
        responses.add(
            responses.GET,
            "http://localhost:9000/mcp/tools",
            json=tools_response,
            status=200
        )

        responses.add(
            responses.POST,
            "http://localhost:9000/mcp/tools/get_forecast/call",
            json=tool_call_response,
            status=200
        )

        # WHEN
        response = client.post_without_permissions(url=f"/v1{ENDPOINT__MCP}", json=params)

        # THEN
        assert response.status_code == 200, response.text
        assert route.call_count == 2
        responses.assert_call_count("http://localhost:9000/mcp/tools", 1)
        responses.assert_call_count("http://localhost:9000/mcp/tools/get_forecast/call", 1)
        ChatCompletion(**response.json())


    @respx.mock
    @responses.activate
    def test_mcp_list_tools_return_tool_list(self, client: TestClient, setup):
        tools_response = {
            "weather": {
                "_meta": None,
                "nextCursor": None,
                "tools": [{
                    "name": "get_alerts",
                    "description": "Get weather alerts for a US state.\n\n    Args:\n        state: Two-letter US state code (e.g. CA, NY)\n    ",
                    "inputSchema": {
                        "properties": {
                            "state": {
                                "title": "State",
                                "type": "string"
                            }
                        },
                        "required": ["state"],
                        "title": "get_alertsArguments",
                        "type": "object"
                    },
                    "annotations": None
                }, {
                    "name": "get_forecast",
                    "description": "Get weather forecast for a location.\n\n    Args:\n        latitude: Latitude of the location\n        longitude: Longitude of the location\n    ",
                    "inputSchema": {
                        "properties": {
                            "latitude": {
                                "title": "Latitude",
                                "type": "number"
                            },
                            "longitude": {
                                "title": "Longitude",
                                "type": "number"
                            }
                        },
                        "required": ["latitude", "longitude"],
                        "title": "get_forecastArguments",
                        "type": "object"
                    },
                    "annotations": None
                }]
            }
        }

        responses.add(
            responses.GET,
            "http://localhost:9000/mcp/tools",
            json=tools_response,
            status=200
        )


        # WHEN
        response = client.get(url=f"/v1{ENDPOINT__MCP}/tool_list")

        # THEN
        assert response.status_code == 200, response.text
        responses.assert_call_count("http://localhost:9000/mcp/tools", 1)

