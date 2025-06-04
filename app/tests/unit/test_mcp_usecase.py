import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.helpers.agents import AgentsManager


class TestMcpBody(SimpleNamespace):
    def model_dump(self):
        return self.__dict__


class TestMCPLoop:
    @pytest.fixture
    def mock_mcp_bridge(self):
        return AsyncMock()

    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()

    @pytest.fixture
    def mock_llm_registry(self, mock_llm_client):
        mock_llm_registry = MagicMock()
        mock_llm_registry.return_value = SimpleNamespace(get_client=lambda endpoint: mock_llm_client)
        return mock_llm_registry

    @pytest.fixture
    def mcp_client(self, mock_mcp_bridge, mock_llm_registry):
        return AgentsManager(mock_mcp_bridge, mock_llm_registry)

    class TestGetToolsFromBridge:
        @pytest.mark.asyncio
        async def test_get_tools_from_bridge_returns_flat_tool_list(self, mcp_client, mock_mcp_bridge):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {
                    "tools": [
                        {"name": "tool 1", "description": "First tool description", "inputSchema": {}},
                        {"name": "tool 1", "description": "Second tool description", "inputSchema": {}},
                    ]
                },
                "mcp_server_2": {"tools": [{"name": "tool 3", "description": "Third tool description", "inputSchema": {}}]},
            }
            expected_tools = [
                {"name": "tool 1", "description": "First tool description", "inputSchema": {}},
                {"name": "tool 1", "description": "Second tool description", "inputSchema": {}},
                {"name": "tool 3", "description": "Third tool description", "inputSchema": {}},
            ]
            # WHEN
            actual_tools = await mcp_client.get_tools_from_bridge()
            # THEN
            assert actual_tools == expected_tools

        @pytest.mark.asyncio
        async def test_get_tools_from_bridge_with_empty_tools_returns_empty_list(self, mcp_client, mock_mcp_bridge):
            mock_mcp_bridge.get_tool_list.return_value = {"section1": {"tools": []}, "section2": {"tools": []}}
            assert await mcp_client.get_tools_from_bridge() == []

        @pytest.mark.asyncio
        async def test_get_tools_from_bridge_with_no_sections_returns_empty_list(self, mcp_client, mock_mcp_bridge):
            mock_mcp_bridge.get_tool_list.return_value = {}
            assert await mcp_client.get_tools_from_bridge() == []

    class TestGetCompletion:
        @pytest.mark.asyncio
        async def test_get_completion_loop_does_not_exceed_10_rounds_per_default(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {}
            raw_response_from_llm = {"choices": [{"finish_reason": "not stop nor tools_calls", "message": {"content": "message from llm"}}]}
            mock_llm_client.forward_request.return_value = SimpleNamespace(
                text=json.dumps(raw_response_from_llm), json=lambda: raw_response_from_llm, status_code=200, request="", headers={}
            )
            number_of_rounds = 10
            # WHEN
            actual_message = await mcp_client.get_completion(
                SimpleNamespace(messages=[{"content": "Salut", "role": "user"}], model_dump=lambda: None, model="")
            )

            # THEN
            assert actual_message.json()["choices"][0]["finish_reason"] == "max_iterations"
            assert actual_message.json()["choices"][0]["message"]["content"] == "message from llm"
            assert mock_llm_client.forward_request.call_count == number_of_rounds

        @pytest.mark.asyncio
        async def test_get_completion_should_return_message_from_llm_with_tool_call_result_when_tool_is_specified(
            self, mcp_client, mock_mcp_bridge, mock_llm_client
        ):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {
                    "tools": [
                        {"name": "tool 1", "description": "First tool description", "inputSchema": {}},
                        {"name": "tool 2", "description": "Second tool description", "inputSchema": {}},
                        {"name": "tool 3", "description": "Third tool description", "inputSchema": {}},
                    ]
                },
            }
            message_from_llm_after_tool_call = "message from llm"

            mock_llm_client.forward_request.side_effect = [
                SimpleNamespace(
                    text='{"choices": [{"finish_reason": "tool_calls","message": {"tool_calls": [{"function": {"name": "tool_1", "arguments": "arguments for tool call"}}]}}]}'
                ),
                SimpleNamespace(
                    status_code=200,
                    text=json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "message from llm"}}]}),
                    headers={},
                    request=None,
                ),
            ]
            number_of_rounds = 2
            mock_mcp_bridge.call_tool.return_value = {"content": [{"text": "tool call result"}]}
            body = TestMcpBody(
                messages=[{"content": "Je veux que tu fasses une action", "role": "user"}], model="albert-large", tools=["tool 1", "tool 2"]
            )

            # WHEN
            actual_message = await mcp_client.get_completion(body)

            # THEN
            second_call_llm_client_arguments = mock_llm_client.forward_request.call_args_list[1][1]
            assert json.loads(actual_message.text)["choices"][0]["message"]["content"] == message_from_llm_after_tool_call

            assert second_call_llm_client_arguments == {
                "json": {
                    "messages": [{"content": "Je veux que tu fasses une action", "role": "user"}, {"content": "tool call result", "role": "user"}],
                    "model": "albert-large",
                    "tool_choice": "auto",
                    "tools": [
                        {"function": {"description": "First tool description", "name": "tool 1", "parameters": {}}, "type": "function"},
                        {"function": {"description": "Second tool description", "name": "tool 2", "parameters": {}}, "type": "function"},
                    ],
                },
                "method": "POST",
            }
            assert mock_llm_client.forward_request.call_count == number_of_rounds

        @pytest.mark.asyncio
        async def test_get_completion_should_return_message_from_llm_using_all_tools_if_tools_field_is_all(
            self, mcp_client, mock_mcp_bridge, mock_llm_client
        ):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {
                    "tools": [
                        {"name": "tool 1", "description": "First tool description", "inputSchema": {}},
                        {"name": "tool 2", "description": "Second tool description", "inputSchema": {}},
                        {"name": "tool 3", "description": "Third tool description", "inputSchema": {}},
                    ]
                },
            }
            message_from_llm_after_tool_call = "message from llm"

            mock_llm_client.forward_request.side_effect = [
                SimpleNamespace(
                    text='{"choices": [{"finish_reason": "tool_calls","message": {"tool_calls": [{"function": {"name": "tool_1", "arguments": "arguments for tool call"}}]}}]}'
                ),
                SimpleNamespace(
                    status_code=200,
                    text=json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "message from llm"}}]}),
                    headers={},
                    request=None,
                ),
            ]
            number_of_rounds = 2
            mock_mcp_bridge.call_tool.return_value = {"content": [{"text": "tool call result"}]}
            body = TestMcpBody(messages=[{"content": "Je veux que tu fasses une action", "role": "user"}], model="albert-large", tools=["all"])

            # WHEN
            actual_message = await mcp_client.get_completion(body)

            # THEN
            second_call_llm_client_arguments = mock_llm_client.forward_request.call_args_list[1][1]
            assert json.loads(actual_message.text)["choices"][0]["message"]["content"] == message_from_llm_after_tool_call

            assert second_call_llm_client_arguments == {
                "json": {
                    "messages": [{"content": "Je veux que tu fasses une action", "role": "user"}, {"content": "tool call result", "role": "user"}],
                    "model": "albert-large",
                    "tool_choice": "auto",
                    "tools": [
                        {"function": {"description": "First tool description", "name": "tool 1", "parameters": {}}, "type": "function"},
                        {"function": {"description": "Second tool description", "name": "tool 2", "parameters": {}}, "type": "function"},
                        {"function": {"description": "Third tool description", "name": "tool 3", "parameters": {}}, "type": "function"},
                    ],
                },
                "method": "POST",
            }
            assert mock_llm_client.forward_request.call_count == number_of_rounds

        @pytest.mark.asyncio
        async def test_get_completion_should_not_use_any_tools_if_none_is_specified(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {"tools": [{"name": "tool 1", "description": "First tool description", "inputSchema": {}}]},
            }
            message_from_llm = "message from llm without tool call"

            mock_llm_client.forward_request.side_effect = [
                SimpleNamespace(
                    status_code=200,
                    text=json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": message_from_llm}}]}),
                    headers={},
                    request=None,
                ),
            ]
            number_of_rounds = 1
            body = TestMcpBody(messages=[{"content": "Je veux que tu fasses une action", "role": "user"}], model="albert-large")

            # WHEN
            actual_message = await mcp_client.get_completion(body)

            # THEN
            llm_client_arguments_called = mock_llm_client.forward_request.call_args_list[0][1]
            assert json.loads(actual_message.text)["choices"][0]["message"]["content"] == message_from_llm
            assert mock_llm_client.forward_request.call_count == number_of_rounds
            assert llm_client_arguments_called == {
                "json": {"messages": [{"content": "Je veux que tu fasses une action", "role": "user"}], "model": "albert-large"},
                "method": "POST",
            }
            assert mock_mcp_bridge.get_tool_list.call_count == 0

        @pytest.mark.asyncio
        async def test_get_completion_should_use_tool_choice_when_specified_in_body(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            agents_choice = "always"
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {
                    "tools": [
                        {"name": "tool 1", "description": "First tool description", "inputSchema": {}},
                        {"name": "tool 2", "description": "Second tool description", "inputSchema": {}},
                        {"name": "tool 3", "description": "Third tool description", "inputSchema": {}},
                    ]
                },
            }
            message_from_llm_after_tool_call = "message from llm"

            mock_llm_client.forward_request.side_effect = [
                SimpleNamespace(
                    text='{"choices": [{"finish_reason": "tool_calls","message": {"tool_calls": [{"function": {"name": "tool_1", "arguments": "arguments for tool call"}}]}}]}'
                ),
                SimpleNamespace(
                    status_code=200,
                    text=json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "message from llm"}}]}),
                    headers={},
                    request=None,
                ),
            ]
            number_of_rounds = 2
            mock_mcp_bridge.call_tool.return_value = {"content": [{"text": "tool call result"}]}
            body = TestMcpBody(
                messages=[{"content": "Je veux que tu fasses une action", "role": "user"}],
                model="albert-large",
                tools=["tool 1"],
                tool_choice=agents_choice,
            )

            # WHEN
            actual_message = await mcp_client.get_completion(body)

            # THEN
            second_call_llm_client_arguments = mock_llm_client.forward_request.call_args_list[1][1]
            assert json.loads(actual_message.text)["choices"][0]["message"]["content"] == message_from_llm_after_tool_call

            assert second_call_llm_client_arguments == {
                "json": {
                    "messages": [{"content": "Je veux que tu fasses une action", "role": "user"}, {"content": "tool call result", "role": "user"}],
                    "model": "albert-large",
                    "tools": [{"function": {"description": "First tool description", "name": "tool 1", "parameters": {}}, "type": "function"}],
                    "tool_choice": agents_choice,
                },
                "method": "POST",
            }
            assert mock_llm_client.forward_request.call_count == number_of_rounds
