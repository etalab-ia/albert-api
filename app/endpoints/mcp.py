from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers import AccessController
from app.helpers._agentsmanager import AgentsManager
from app.schemas.mcp import McpChatCompletionRequest, McpChatCompletion
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__AGENTS_TOOLS, ENDPOINT__AGENTS_COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__AGENTS_COMPLETIONS, dependencies=[Security(dependency=AccessController())], response_model=McpChatCompletion)
async def mcp_completion(request: Request, body: McpChatCompletionRequest) -> JSONResponse:
    model = global_context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
    mcp = AgentsManager(global_context.mcp.mcp_bridge, client)
    response = await mcp.get_completion(body)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get(path=ENDPOINT__AGENTS_TOOLS, dependencies=[Security(dependency=AccessController())])
async def mcpn_tool_list():
    mcp = AgentsManager(global_context.mcp.mcp_bridge, None)
    response = await mcp.get_tools_from_bridge()
    return JSONResponse(status_code=200, content={"tools": response})
