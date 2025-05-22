from dotenv import load_dotenv

from app.clients.mcp.mcp_bridge_client import MCPBridgeClient
from app.clients.mcp.mcp_llm_client import McpLlmClient

load_dotenv()


class McpUsecase:
    def __init__(self, mcp_bridge: MCPBridgeClient, llm_client: McpLlmClient):
        self.llm_client = llm_client
        self.mcp_bridge = mcp_bridge

    async def get_tools_from_bridge(self):
        mcp_bridge_tools = await self.mcp_bridge.get_tool_list()
        all_tools = [section["tools"] for section in mcp_bridge_tools.values()]
        flat_tools = [tool for tools in all_tools for tool in tools]
        return flat_tools

    async def process_query(self, body) -> str:
        tools = await self.get_tools_from_bridge()
        available_tools = [
            {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["inputSchema"]}}
            for tool in tools
        ]
        body.tools = available_tools
        body.tool_choice = "auto"
        llm_response = None
        number_of_iterations = 0
        max_iterations = getattr(body, "max_iterations", 10)
        while number_of_iterations < max_iterations:
            llm_response = await self.llm_client.post_on_llm_model(body)
            finish_reason = llm_response["choices"][0]["finish_reason"]
            number_of_iterations = number_of_iterations + 1
            if finish_reason in ["stop", "length"]:
                return llm_response
            elif finish_reason == "tool_calls":
                tool_config = llm_response["choices"][0]["message"]["tool_calls"][0]["function"]
                tool_name = tool_config["name"]
                tool_args = tool_config["arguments"]

                tool_call_result = await self.mcp_bridge.call_tool(tool_name, tool_args)

                body.messages.append({"role": "user", "content": tool_call_result["content"][0]["text"]})
        llm_response["choices"][0]["finish_reason"] = "max_iterations"
        return llm_response
