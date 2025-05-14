import json

from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.mcp.mcp_loop import MCPBridgeClient, MCPLoop, LLMClient
from app.schemas.chat import ChatCompletion, ChatCompletionRequest
from app.utils.variables import ENDPOINT__MCP

router = APIRouter()


@router.post(path=ENDPOINT__MCP, dependencies=[Security(dependency=Authorization())])
async def mcp_completion(request: Request, body: ChatCompletionRequest) -> ChatCompletion:
    mcp_bridge = MCPBridgeClient('http://localhost:9000')
    llm_client = LLMClient()
    mcp = MCPLoop(mcp_bridge, llm_client)
    response = await mcp.process_query(body)
    json_str = json.dumps(response, default=lambda o: o.__dict__)
    params = json.loads(json_str)
    return ChatCompletion(**params)


@router.get(path=ENDPOINT__MCP + "/tool_list", dependencies=[Security(dependency=Authorization())])
def mcpn_tool_list():
    mcp_bridge = MCPBridgeClient('http://localhost:9000')
    llm_client = LLMClient()
    mcp = MCPLoop(mcp_bridge, llm_client)
    response = mcp.get_tools_from_bridge()
    json_str = json.dumps({'tools': response}, default=lambda o: o.__dict__)
    params = json.loads(json_str)
    return params
