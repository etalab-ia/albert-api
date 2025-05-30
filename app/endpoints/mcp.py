from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers.core import AccessController
from app.schemas.mcp import McpChatCompletionRequest, McpChatCompletion
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__AGENTS_TOOLS, ENDPOINT__AGENTS_COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__AGENTS_COMPLETIONS, dependencies=[Security(dependency=AccessController())], response_model=McpChatCompletion)
async def mcp_completion(request: Request, body: McpChatCompletionRequest) -> JSONResponse:
    agents_manager = global_context.mcp.agents_manager
    response = await agents_manager.get_completion(body)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get(path=ENDPOINT__AGENTS_TOOLS, dependencies=[Security(dependency=AccessController())])
async def mcpn_tool_list():
    agents_manager = global_context.mcp.agents_manager
    response = await agents_manager.get_tools_from_bridge()
    return JSONResponse(status_code=200, content={"tools": response})
