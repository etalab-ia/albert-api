from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.rerank import RerankRequest, Reranks
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__RERANK

router = APIRouter()


@router.post(path=ENDPOINT__RERANK, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Reranks)
async def rerank(request: Request, body: RerankRequest) -> JSONResponse:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """
    async def handler(client):
        response = await client.forward_request(method="POST", json=body.model_dump())
        return JSONResponse(content=Reranks(**response.json()).model_dump(), status_code=response.status_code)

    return await global_context.models(model=body.model).safe_client_access(
        endpoint=ENDPOINT__RERANK,
        handler=handler
    )
