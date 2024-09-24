from fastapi import APIRouter, Security

from app.helpers import VectorStore, UseInternet
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

    use_internet = bool(request.collections.pop("internet"))

    vectorstore = VectorStore(clients=clients, user=user)
    data = vectorstore.search(
        prompt=request.prompt, model=request.model, collection_names=request.collections, k=request.k, score_threshold=request.score_threshold
    )

    if use_internet:
        search = UseInternet()
        data.extend(search.search_internet(prompt=request.prompt, n=4))

    data = sorted(data, key=lambda x: x.score, reverse=False)[: request.k]

    return Searches(data=data)
