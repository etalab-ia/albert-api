from dotenv import load_dotenv

from app.mcp.llm_client import LLMClient
from app.mcp.mcp_bridge_client import MCPBridgeClient

load_dotenv()

class MCPLoop:
    def __init__(self, mcp_bridge: MCPBridgeClient, llm_client: LLMClient):
        self.llm_client = llm_client
        self.mcp_bridge = mcp_bridge

    def get_tools_from_bridge(self):
        mcp_bridge_tools = self.mcp_bridge.get_tool_list()
        all_tools = [section["tools"] for section in mcp_bridge_tools.values()]
        flat_tools = [tool for tools in all_tools for tool in tools]
        return flat_tools


    async def process_query(self, body) -> str:
        tools = self.get_tools_from_bridge()
        available_tools = [{
            "type": "function",
            "function":
                {"name": tool['name'],
                 "description": tool['description'],
                 "parameters": tool['inputSchema']}
        } for tool in tools]
        final_text = []
        max_iterations = 10
        body.tools = available_tools
        body.tool_choice = "auto"
        for _ in range(max_iterations):
            llm_response = await self.llm_client.post_on_llm_model(body)
            finish_reason = llm_response.choices[0].finish_reason
            if finish_reason in ['stop', 'length'] :
                return llm_response
            elif finish_reason == 'tool_calls':
                tool_config = llm_response.choices[0].message.tool_calls[0].function
                tool_name = tool_config.name
                tool_args = tool_config.arguments

                tool_call_result = self.mcp_bridge.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                body.messages.append({
                    "role": "user",
                    "content": tool_call_result['content'][0]['text']
                })

        return "Maximum number of steps exceeded without resolving the query."