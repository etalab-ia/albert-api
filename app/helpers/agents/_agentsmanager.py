import json
from typing import List

import httpx

from app.clients.mcp import SecretShellMCPBridgeClient
from app.helpers.models import ModelRegistry
from app.schemas.mcp import MCPTool
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS


class AgentsManager:
    MAX_ITERATIONS = 2

    def __init__(self, mcp_bridge: SecretShellMCPBridgeClient, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self.mcp_bridge = mcp_bridge

    async def get_completion(self, body: dict):
        body = await self.set_tools_for_llm_request(body)
        http_llm_response = None
        number_of_iterations = 0
        while number_of_iterations < self.MAX_ITERATIONS:
            http_llm_response = await self.get_llm_http_response(body)
            llm_response = json.loads(http_llm_response.text)
            finish_reason = llm_response["choices"][0]["finish_reason"]
            number_of_iterations = number_of_iterations + 1
            if finish_reason in ["stop", "length"]:
                return http_llm_response
            elif finish_reason == "tool_calls":
                tool_config = llm_response["choices"][0]["message"]["tool_calls"][0]["function"]
                tool_name = tool_config["name"]
                tool_args = tool_config["arguments"]

                tool_call_result = await self.mcp_bridge.call_tool(tool_name, tool_args)
                body.messages.append({"role": "user", "content": tool_call_result["content"][0]["text"]})
        last_llm_response = http_llm_response.json()
        last_llm_response["choices"][0]["finish_reason"] = "max_iterations"
        llm_response_with_new_finish_reason = httpx.Response(
            status_code=http_llm_response.status_code,
            content=json.dumps(last_llm_response),
            headers=http_llm_response.headers,
            request=http_llm_response.request,
        )
        return llm_response_with_new_finish_reason

    async def get_llm_http_response(self, body):
        model = self.model_registry(model=body.model)
        client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        http_llm_response = await client.forward_request(method="POST", json=body.model_dump())

        return http_llm_response

    async def set_tools_for_llm_request(self, body: dict) -> dict:
        if hasattr(body, "tools") and body.tools is not None:
            tools = await self.get_tools_from_bridge()

            available_tools = [
                {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}}
                for tool in tools
            ]
            requested_tools = [tool.get("type") for tool in body.tools if tool.get("type") != "function" and tool.get("type") is not None]
            if "all" in requested_tools:
                body.tools = available_tools
            else:
                # TODO: handle error if tool is not available
                available_tool_names = [tool["function"]["name"] for tool in available_tools]
                selected_available_tool_names = list(set(requested_tools) & set(available_tool_names))
                used_tools = [
                    available_tool
                    for available_tool in available_tools
                    if available_tool.get("function").get("name") in selected_available_tool_names
                ]
                body.tools = used_tools
            body.tool_choice = getattr(body, "tool_choice", "auto")

        return body

    async def get_tools_from_bridge(self) -> List[MCPTool]:
        tools = await self.mcp_bridge.get_tool_list()

        return tools
