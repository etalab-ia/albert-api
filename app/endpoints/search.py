from fastapi import APIRouter, HTTPException, Security

from app.helpers import VectorStore, SearchOnInternet
from app.schemas.search import Searches, SearchRequest
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/search")
async def search(request: SearchRequest, user: str = Security(check_api_key)) -> Searches:
    """
    Similarity search for chunks in the vector store.

    Args:
        request (SearchRequest): The search request.
        user (str): The user.

    Returns:
        Chunks: The chunks.
    """

    search_on_internet = bool(request.collections.pop("internet"))

    vectorstore = VectorStore(clients=clients, user=user)
    try:
        data = vectorstore.search(
            prompt=request.prompt, model=request.model, collection_names=request.collections, k=request.k, score_threshold=request.score_threshold
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if search_on_internet:
        internet = SearchOnInternet()
        try:
            data.extend(internet.search(prompt=request.prompt, n=4))
        except AssertionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        data = sorted(data, key=lambda x: x.score, reverse=False)[: request.k]

    return Searches(data=data)
