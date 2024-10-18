from fastapi import APIRouter, Security

from app.helpers import SearchOnInternet
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import INTERNET_COLLECTION_ID

router = APIRouter()


@router.post("/search")
async def search(body: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Similarity search for chunks in the vector store or on the internet.
    """

    data = []
    if INTERNET_COLLECTION_ID in body.collections:
        body.collections.remove(INTERNET_COLLECTION_ID)
        internet = SearchOnInternet(models=clients.models)
        if len(body.collections) > 0:
            collection_model = clients.vectors.get_collections(collection_ids=body.collections, user=user)[0].model
        else:
            collection_model = None
        data.extend(internet.search(prompt=body.prompt, n=4, model_id=collection_model, score_threshold=body.score_threshold))

    if len(body.collections) > 0:
        data.extend(
            clients.vectors.search(prompt=body.prompt, collection_ids=body.collections, k=body.k, score_threshold=body.score_threshold, user=user)
        )

    data = sorted(data, key=lambda x: x.score, reverse=False)[: body.k]

    return Searches(data=data)
