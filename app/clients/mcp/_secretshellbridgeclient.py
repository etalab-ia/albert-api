import json

import httpx
from fastapi import HTTPException


class SecretShellMCPBridgeClient:
    def __init__(self, mcp_bridge_url: str):
        self.url = mcp_bridge_url
        self.timeout = 10

    async def get_tool_list(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method="GET", url=self.url + "/mcp/tools", headers={})
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)
        return response.json()

    async def call_tool(self, tool_name: str, params: str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            print(f"failed to decode json for {tool_name}")
            return None
        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method="POST", json=params, url=self.url + f"/mcp/tools/{tool_name}/call", headers={})
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)
        return response.json()
