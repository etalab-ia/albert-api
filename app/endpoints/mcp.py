from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.mcp import MCPChatCompletion, MCPChatCompletionRequest, MCPTools
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__AGENTS_COMPLETIONS, ENDPOINT__AGENTS_TOOLS

router = APIRouter()


@router.post(path=ENDPOINT__AGENTS_COMPLETIONS, dependencies=[Security(dependency=AccessController())], response_model=MCPChatCompletion)
async def mcp_completions(request: Request, body: MCPChatCompletionRequest) -> JSONResponse:
    """
    Creates a model response for the given chat conversation with call to the MCP bridge.
    """

    agents_manager = global_context.mcp.agents_manager
    response = await agents_manager.get_completion(body)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get(path=ENDPOINT__AGENTS_TOOLS, dependencies=[Security(dependency=AccessController())])
async def mcp_tools(request: Request) -> JSONResponse:
    """
    Returns the list of tools available in the MCP bridge.
    """

    response = await global_context.mcp.agents_manager.get_tools_from_bridge()

    return JSONResponse(content=MCPTools(data=response).model_dump(), status_code=200)
