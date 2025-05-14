import json
import requests

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