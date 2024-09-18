from fastapi import APIRouter, Security

from app.helpers import VectorStore
from app.schemas.chunks import Chunks
from app.schemas.search import SearchRequest
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/search")
async def search(request: SearchRequest, user: str = Security(check_api_key)) -> Chunks:
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

    return Chunks(data=data)
