import uuid

from fastapi import APIRouter, Request, Security

from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import INTERNET_COLLECTION_DISPLAY_ID

router = APIRouter()


@router.post(path="/search")
@limiter.limit(limit_value=settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(dependency=check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our engine client
    """

    # Internet search
    need_internet_search = not body.collections or INTERNET_COLLECTION_DISPLAY_ID in body.collections
    internet_chunks = []
    if need_internet_search:
        # get internet results chunks
        internet_collection_id = str(uuid.uuid4())
        internet_chunks = clients.internet.get_chunks(prompt=body.prompt, collection_id=internet_collection_id)

        if internet_chunks:
            internet_embeddings_model_id = (
                clients.internet.default_embeddings_model_id
                if body.collections == [INTERNET_COLLECTION_DISPLAY_ID]
                else clients.search.get_collections(collection_ids=body.collections, user=user)[0].model
            )

            clients.search.create_collection(
                collection_id=internet_collection_id,
                collection_name=internet_collection_id,
                collection_model=internet_embeddings_model_id,
                user=user,
            )
            clients.search.upsert(chunks=internet_chunks, collection_id=internet_collection_id, user=user)

        # case: no other collections, only internet, and no internet results
        elif body.collections == [INTERNET_COLLECTION_DISPLAY_ID]:
            return Searches(data=[])

        # case: other collections or only internet and internet results
        if INTERNET_COLLECTION_DISPLAY_ID in body.collections:
            body.collections.remove(INTERNET_COLLECTION_DISPLAY_ID)
            body.collections.append(internet_collection_id)

    searches = clients.search.query(
        prompt=body.prompt,
        collection_ids=body.collections,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        user=user,
    )

    if internet_chunks:
        clients.search.delete_collection(collection_id=internet_collection_id, user=user)

    if body.score_threshold:
        searches = [search for search in searches if search.score >= body.score_threshold]

    return Searches(data=searches)
