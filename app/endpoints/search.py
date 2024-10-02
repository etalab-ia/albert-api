from fastapi import APIRouter, HTTPException, Security

from app.helpers import SearchOnInternet, VectorStore
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

    vectorstore = VectorStore(clients=clients, user=user)

    data = []
    if INTERNET_COLLECTION_ID in request.collections:
        request.collections.remove(INTERNET_COLLECTION_ID)
        internet = SearchOnInternet(clients=clients)
        if len(request.collections) > 0:
            collection_model = vectorstore.get_collection_metadata(collection_ids=request.collections)[0].model
        else:
            collection_model = None
        data.extend(internet.search(prompt=request.prompt, n=4, model_id=collection_model, score_threshold=request.score_threshold))

    if len(request.collections) > 0:
        try:
            data.extend(
                vectorstore.search(prompt=request.prompt, collection_ids=request.collections, k=request.k, score_threshold=request.score_threshold)
            )
        except AssertionError as e:
            raise HTTPException(status_code=400, detail=str(e))

    data = sorted(data, key=lambda x: x.score, reverse=False)[: request.k]

    return Searches(data=data)
