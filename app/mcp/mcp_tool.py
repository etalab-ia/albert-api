import json
from types import SimpleNamespace

import requests
from dotenv import load_dotenv
from openai import OpenAI


from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

load_dotenv()

class MCPBridgeClient:
    def __init__(self, mcp_bridge_url: str):
        self.url = mcp_bridge_url

    def get_tool_list(self) -> dict:
        tools = requests.get(
            self.url + "/mcp/tools",
            headers={},
            timeout=10,
        )
        return tools.json()

    def call_tool(self, tool_name: str, params: str):
        path = f"/mcp/tools/{tool_name}/call"
        headers = {}
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            print(f"failed to decode json for {tool_name}")
            return None
        tool_call_response = requests.post(self.url + path, headers=headers, json=params)
        return tool_call_response.json()


class LLMClient:
    def __init__(self):
        pass
    async def post_on_llm_model(self, body):
        from app.utils.lifespan import context
        model = context.models(model=body.model)
        client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        http_llm_response = await client.forward_request(method="POST", json=body.model_dump())
        return json.loads(http_llm_response.text, object_hook=lambda d: SimpleNamespace(**d))


class MCPClient:
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