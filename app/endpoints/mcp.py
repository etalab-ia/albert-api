import json

from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.schemas.chat import ChatCompletion, McpChatCompletionRequest
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__MCP

router = APIRouter()


@router.post(path=ENDPOINT__MCP + "/completions", dependencies=[Security(dependency=Authorization())])
async def mcp_completion(request: Request, body: McpChatCompletionRequest) -> ChatCompletion:
    response = await context.mcp.process_query(body)
    json_str = json.dumps(response, default=lambda o: o.__dict__)
    params = json.loads(json_str)
    return ChatCompletion(**params)


@router.get(path=ENDPOINT__MCP + "/servers", dependencies=[Security(dependency=Authorization())])
async def mcpn_tool_list():
    response = await context.mcp.get_tools_from_bridge()
    json_str = json.dumps({"mcp_servers": response}, default=lambda o: o.__dict__)
    params = json.loads(json_str)
    return params
