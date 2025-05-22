from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.usecase.mcp_usecase import McpUsecase


class TestMCPLoop:
    @pytest.fixture
    def mock_mcp_bridge(self):
        return AsyncMock()

    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()

    @pytest.fixture
    def mcp_client(self, mock_mcp_bridge, mock_llm_client):
        return McpUsecase(mock_mcp_bridge, mock_llm_client)

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

    class TestProcessQuery:
        @pytest.mark.asyncio
        async def test_process_query_loop_does_excess_10_rounds_per_default(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {}
            expected_response = {"choices": [{"finish_reason": "max_iterations", "message": {"content": "message from llm"}}]}
            mock_llm_client.post_on_llm_model.return_value = {
                "choices": [{"finish_reason": "not stop nor tools_calls", "message": {"content": "message from llm"}}]
            }
            number_of_rounds = 10
            # WHEN
            actual_message = await mcp_client.process_query(SimpleNamespace(messages=[{"content": "Salut", "role": "user"}]))

            # THEN
            assert actual_message == expected_response
            assert mock_llm_client.post_on_llm_model.call_count == number_of_rounds

        @pytest.mark.asyncio
        async def test_process_query_loop_maximum_iterations_can_be_changed(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {}
            expected_response = {"choices": [{"finish_reason": "max_iterations", "message": {"content": "message from llm"}}]}
            mock_llm_client.post_on_llm_model.return_value = {
                "choices": [{"finish_reason": "not stop nor tools_calls", "message": {"content": "message from llm"}}]
            }
            number_of_rounds = 15
            # WHEN
            actual_message = await mcp_client.process_query(
                SimpleNamespace(messages=[{"content": "Salut", "role": "user"}], max_iterations=number_of_rounds)
            )

            # THEN
            assert actual_message == expected_response
            assert mock_llm_client.post_on_llm_model.call_count == number_of_rounds

        @pytest.mark.asyncio
        async def test_process_query_should__return_message_from_llm_without_tool_call_result(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {"tools": [{"name": "tool 1", "description": "First tool description", "inputSchema": {}}]},
            }
            message_from_llm_after_tool_call = "message from llm"

            mock_llm_client.post_on_llm_model.side_effect = [
                {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {"tool_calls": [{"function": {"name": "tool_1", "arguments": "arguments for tool call"}}]},
                        }
                    ]
                },
                {"choices": [{"finish_reason": "stop", "message": {"content": "message from llm"}}]},
            ]
            number_of_rounds = 2
            mock_mcp_bridge.call_tool.return_value = {"content": [{"text": "tool call result"}]}
            # WHEN
            actual_message = await mcp_client.process_query(
                SimpleNamespace(messages=[{"content": "Je veux que tu fasses une action", "role": "user"}])
            )

            # THEN
            assert actual_message["choices"][0]["message"]["content"] == message_from_llm_after_tool_call
            assert mock_llm_client.post_on_llm_model.call_count == number_of_rounds
