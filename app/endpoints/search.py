from fastapi import APIRouter, Depends, Request, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import Authorization
from app.schemas.search import Searches, SearchRequest
from app.sql.session import get_db as get_session
from app.utils.exceptions import CollectionNotFoundException
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__SEARCH

router = APIRouter()


@router.post(path=ENDPOINT__SEARCH, dependencies=[Security(dependency=Authorization())])
async def search(request: Request, body: SearchRequest, session: AsyncSession = Depends(get_session)) -> Searches:
    """
    Get relevant chunks from the collections and a query.
    """

    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    data = await context.documents.search(
        session=session,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        user_id=request.app.state.user.id,
        web_search=body.web_search,
    )

    return Searches(data=data)
