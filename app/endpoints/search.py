from fastapi import APIRouter, HTTPException, Security

from app.helpers import SearchOnInternet
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import INTERNET_COLLECTION_ID

router = APIRouter()


@router.post("/search")
async def search(request: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Similarity search for chunks in the vector store or on the internet.
    """

    data = []
    if INTERNET_COLLECTION_ID in request.collections:
        request.collections.remove(INTERNET_COLLECTION_ID)
        internet = SearchOnInternet(models=clients.models)
        if len(request.collections) > 0:
            collection_model = clients.vectorstore.get_collections(collection_ids=request.collections, user=user)[0].model
        else:
            collection_model = None
        data.extend(internet.search(prompt=request.prompt, n=4, model_id=collection_model, score_threshold=request.score_threshold))

    if len(request.collections) > 0:
        try:
            data.extend(
                clients.vectorstore.search(
                    prompt=request.prompt, collection_ids=request.collections, k=request.k, score_threshold=request.score_threshold, user=user
                )
            )
        except AssertionError as e:
            raise HTTPException(status_code=400, detail=str(e))

    data = sorted(data, key=lambda x: x.score, reverse=False)[: request.k]

    return Searches(data=data)
