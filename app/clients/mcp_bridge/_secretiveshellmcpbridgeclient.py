import json
from typing import Dict, List

from fastapi import HTTPException
import httpx

from app.clients.mcp_bridge._basemcpbridgeclient import BaseMCPBridgeClient
from app.schemas.agents import AgentsTool


class SecretiveshellMCPBridgeClient(BaseMCPBridgeClient):
    def __init__(self, url: str, headers: Dict[str, str], timeout: int, *args, **kwargs):
        super().__init__(url=url, headers=headers, timeout=timeout)

        # Keep health check synchronous in __init__
        try:
            response = httpx.get(f"{self.url}/health", headers=self.headers, timeout=self.timeout)
            assert response.status_code == 200, f"Secretiveshell API is not reachable: {response.text} {response.status_code}"
        except Exception as e:
            raise Exception(f"Secretiveshell API is not reachable: {e}") from e

    async def get_tool_list(self) -> List[AgentsTool]:
        async with httpx.AsyncClient(timeout=self.timeout) as async_client:
            try:
                response = await async_client.request(method="GET", url=self.url + "/mcp/tools", headers=self.headers)
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)

        response_json = response.json()
        data = []
        for mcp_server in response_json.keys():
            tools = response_json[mcp_server]["tools"]
            for tool in tools:
                data.append(
                    AgentsTool(
                        server=mcp_server,
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {}),
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
                response = await async_client.request(method="POST", json=params, url=self.url + f"/mcp/tools/{tool_name}/call", headers=self.headers)
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                raise HTTPException(status_code=504, detail="Request timed out")
            except Exception as e:
                raise HTTPException(status_code=500, detail=type(e).__name__)

        return response.json()
