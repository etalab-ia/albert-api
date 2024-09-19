from fastapi import APIRouter, Security

from app.helpers import VectorStore
from app.schemas.search import SearchRequest, Searches
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/search")
async def search(request: SearchRequest, user: str = Security(check_api_key)) -> Searches:
    """
    Similarity search for chunks in the vector store.

    Parameters:
        request (SearchRequest): The search request.
        user (str): The user.

    Returns:
        Chunks: The chunks.
    """

    vectorstore = VectorStore(clients=clients, user=user)
    data = vectorstore.search(
        prompt=request.prompt, model=request.model, collection_names=request.collections, k=request.k, score_threshold=request.score_threshold
    )

    return Searches(data=data)
