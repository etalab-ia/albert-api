from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import AccessController
from app.schemas.search import Searches, SearchRequest
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import CollectionNotFoundException
from app.utils.variables import ENDPOINT__SEARCH

router = APIRouter()


@router.post(path=ENDPOINT__SEARCH, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Searches)
async def search(request: Request, body: SearchRequest, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """
    Get relevant chunks from the collections and a query.
    """

    if not global_context.documents:  # no vector store available
        raise CollectionNotFoundException()

    data = await global_context.documents.search(
        session=session,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        user_id=request_context.get().user_id,
        web_search=body.web_search,
    )
    usage = request_context.get().usage
    content = Searches(data=data, usage=usage)

    return JSONResponse(content=content.model_dump(), status_code=200)
