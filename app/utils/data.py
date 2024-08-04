from typing import List, Dict, Optional

from fastapi import HTTPException
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter
from langchain_community.vectorstores import Qdrant
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.schemas.chunks import Chunk


def get_chunks(
    vectorstore: QdrantClient,
    collection: str,
    filter: Optional[Filter] = None,
) -> List[Chunk]:
    try:
        chunks = vectorstore.scroll(
            collection_name=collection,
            with_payload=True,
            with_vectors=False,
            scroll_filter=filter,
            limit=100,  # @TDOO: add paginatio
        )[0]
    except Exception:
        raise HTTPException(status_code=404, detail="chunk not found.")

    data = list()
    for chunk in chunks:
        data.append(
            Chunk(
                collection=collection,
                id=chunk.id,
                metadata=chunk.payload["metadata"],
                content=chunk.payload["page_content"],
            )
        )

    return data


def get_all_collections(vectorstore: QdrantClient, api_key: str):
    """
    Get all collections from a vectorstore.

    Parameters:
        vectorstore (Qdrant): The vectorstore to get the collections from.
    """
    collections = [
        collection.name
        for collection in vectorstore.get_collections().collections
        if collection.name.startswith(f"{api_key}-") or collection.name.startswith("public-")
    ]

    return collections


def search_multiple_collections(
    vectorstore: QdrantClient,
    embeddings: HuggingFaceEndpointEmbeddings,
    prompt: str,
    collections: list,
    k: Optional[int] = 4,
    filter: Optional[dict] = None,
):
    docs = []
    for collection in collections:
        lanchain_qdrant = Qdrant(
            client=vectorstore,
            embeddings=embeddings,
            collection_name=collection,
        )
        docs.extend(lanchain_qdrant.similarity_search_with_score(prompt, k=k, filter=filter))

    # sort by similarity score and get top k
    docs = sorted(docs, key=lambda x: x[1], reverse=True)[:k]
    docs = [doc[0] for doc in docs]

    return docs
