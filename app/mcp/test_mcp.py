from unittest.mock import MagicMock, AsyncMock

import pytest

from app.mcp.mcp_tool import MCPClient


class TestMCPBridgeClient:
    @pytest.fixture
    def mock_mcp_bridge(self):
        return MagicMock()

    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()

    @pytest.fixture
    def mcp_client(self, mock_mcp_bridge, mock_llm_client):
        return MCPClient(mock_mcp_bridge, mock_llm_client)

    def test_get_tools_from_bridge_returns_flat_tool_list(self, mcp_client, mock_mcp_bridge):
        pass

    class TestGetToolsFromBridge:
        def test_get_tools_from_bridge_returns_flat_tool_list(self, mcp_client, mock_mcp_bridge):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {"tools": [{'name': 'tool 1',
                                            'description': 'First tool description',
                                            'inputSchema': {}
                                            },
                                           {'name': 'tool 1',
                                            'description': 'Second tool description',
                                            'inputSchema': {}
                                            }]},
                "mcp_server_2": {"tools": [{'name': 'tool 3',
                                            'description': 'Third tool description',
                                            'inputSchema': {}
                                            }]}
            }
            expected_tools = [{'name': 'tool 1',
                               'description': 'First tool description',
                               'inputSchema': {}
                               },
                              {'name': 'tool 1',
                               'description': 'Second tool description',
                               'inputSchema': {}
                               },
                              {'name': 'tool 3',
                               'description': 'Third tool description',
                               'inputSchema': {}
                               }]
            # WHEN
            actual_tools = mcp_client.get_tools_from_bridge()
            # THEN
            assert actual_tools == expected_tools

        def test_get_tools_from_bridge_with_empty_tools_returns_empty_list(self, mcp_client, mock_mcp_bridge):
            mock_mcp_bridge.get_tool_list.return_value = {
                "section1": {"tools": []},
                "section2": {"tools": []}
            }
            assert mcp_client.get_tools_from_bridge() == []

        def test_get_tools_from_bridge_with_no_sections_returns_empty_list(self, mcp_client, mock_mcp_bridge):
            mock_mcp_bridge.get_tool_list.return_value = {}
            assert mcp_client.get_tools_from_bridge() == []

    class TestProcessQuery:
        @pytest.mark.asyncio
        async def test_process_query_loop_does_excess_10_rounds(self, mcp_client, mock_mcp_bridge, mock_llm_client):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {}
            mock_llm_client.post_on_llm_model.return_value = {'finish_reason': 'not stop nor tools_calls'}
            expected_message = 'Maximum number of steps exceeded without resolving the query.'
            number_of_rounds = 10
            # WHEN
            actual_message = await mcp_client.process_query(['salut'])

            # THEN
            assert actual_message == expected_message
            assert mock_llm_client.post_on_llm_model.call_count == number_of_rounds

        @pytest.mark.asyncio
        async def test_process_query_should__return_messages_with_tool_call_results(self, mcp_client, mock_mcp_bridge: MagicMock,
                                                       mock_llm_client: MagicMock):
            # GIVEN
            mock_mcp_bridge.get_tool_list.return_value = {
                "mcp_server_1": {"tools": [{'name': 'tool 1',
                                            'description': 'First tool description',
                                            'inputSchema': {}
                                            }]},

            }
            message_from_llm_after_tool_call = "message from llm"
            mock_llm_client.post_on_llm_model.side_effect = [{'finish_reason': 'tool_calls',
                                                              'message': {
                                                                  'tool_calls': [
                                                                      {'name': 'tool_1',
                                                                       'arguments': 'arguments for tool call'}
                                                                  ]
                                                              }},
                                                             {'finish_reason': 'stop',
                                                              'message': {
                                                                  'content': "message from llm"
                                                              }}]
            expected_message = '[Calling tool tool_1 with args arguments for tool call]\n' + message_from_llm_after_tool_call
            number_of_rounds = 2
            mock_mcp_bridge.call_tool.return_value = {'content': [{'text': "tool call result"}]}
            # WHEN
            actual_message = await mcp_client.process_query(['je veux que tu fasses une action'])

            # THEN
            assert actual_message == expected_message
            assert mock_llm_client.post_on_llm_model.call_count == number_of_rounds
