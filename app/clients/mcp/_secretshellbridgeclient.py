import json
from typing import List

from fastapi import HTTPException
import httpx

from app.schemas.mcp import MCPTool


class SecretShellMCPBridgeClient:
    def __init__(self, mcp_bridge_url: str):
        self.url = mcp_bridge_url
        self.timeout = 10

    async def get_tool_list(self) -> List[MCPTool]:
        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method="GET", url=self.url + "/mcp/tools", headers={})
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)

        response_json = response.json()
        data = []
        for section in response_json.keys():
            tools = response_json[section]["tools"]
            for tool in tools:
                data.append(
                    MCPTool(
                        name=tool["name"],
                        description=tool.get("description", ""),
                        inputSchema=tool.get("inputSchema", {}),
                        annotations=tool.get("annotations", None),
                    )
                )

        return data

    async def call_tool(self, tool_name: str, params: str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            return None
        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method="POST", json=params, url=self.url + f"/mcp/tools/{tool_name}/call", headers={})
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)

        return response.json()
