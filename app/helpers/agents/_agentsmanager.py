import json
import httpx

from app.clients.mcp import SecretShellMCPBridgeClient
from app.helpers.models import ModelRegistry
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS


class AgentsManager:
    def __init__(self, mcp_bridge: SecretShellMCPBridgeClient, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self.mcp_bridge = mcp_bridge

    async def get_tools_from_bridge(self):
        mcp_bridge_tools = await self.mcp_bridge.get_tool_list()
        all_tools = [section["tools"] for section in mcp_bridge_tools.values()]
        flat_tools = [tool for tools in all_tools for tool in tools]
        return flat_tools

    async def get_completion(self, body):
        tools = await self.get_tools_from_bridge()
        available_tools = [
            {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["inputSchema"]}}
            for tool in tools
        ]
        body.tools = available_tools
        body.tool_choice = "auto"
        http_llm_response = None
        number_of_iterations = 0
        max_iterations = getattr(body, "max_iterations", 10)
        while number_of_iterations < max_iterations:
            model = self.model_registry(model=body.model)
            client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
            http_llm_response = await client.forward_request(method="POST", json=body.model_dump())
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
