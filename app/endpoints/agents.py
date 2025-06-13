from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.agents import AgentsChatCompletion, AgentsChatCompletionRequest, AgentsTools
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__AGENTS_COMPLETIONS, ENDPOINT__AGENTS_TOOLS

router = APIRouter()


@router.post(path=ENDPOINT__AGENTS_COMPLETIONS, dependencies=[Security(dependency=AccessController())], response_model=AgentsChatCompletion)
async def agents_completions(request: Request, body: AgentsChatCompletionRequest) -> JSONResponse:
    """
    Creates a model response for the given chat conversation with call to the MCP bridge.
    """

    response = await global_context.mcp.agents_manager.get_completion(body)

    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get(path=ENDPOINT__AGENTS_TOOLS, dependencies=[Security(dependency=AccessController())], response_model=AgentsTools)
async def agents_tools(request: Request) -> JSONResponse:
    """
    Returns the list of tools available in the MCP bridge.
    """

    response = await global_context.mcp.agents_manager.get_tools_from_bridge()

    return JSONResponse(content=AgentsTools(data=response).model_dump(), status_code=200)
