from typing import List, Dict

from qdrant_client.http import models as rest
from nltk.corpus import stopwords
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.vectorstores import Qdrant
from fastapi import HTTPException


def file_to_chunk(client, collection: str, file_ids=List[str]) -> List[Dict]:
    """
    Get chunk from file IDs.

    Args:
        client: vectors database client
        collection (str): name of vector collection.
        file_ids (List[str]): list of file ID.

    Return:
        List[Dict]
    """

    filter = rest.Filter(
        must=[rest.FieldCondition(key="metadata.file_id", match=rest.MatchAny(any=file_ids))]
    )
    records = client.scroll(
        collection_name=collection, with_payload=True, with_vectors=False, scroll_filter=filter
    )

    data = [
        {
            "file_id": record.payload["metadata"]["file_id"],
            "vector_id": record.id,
            "chunk": record.payload["page_content"],
        }
        for record in records[0]
    ]

    return data


def get_all_collections(vectorstore, api_key: str):
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
    vectorstore,
    emmbeddings,
    prompt: str,
    collections: list,
    k: int = 4,
    filter: dict = None,
):
    docs = []
    for collection in collections:
        vectorstore = Qdrant(
            client=vectorstore,
            embeddings=emmbeddings,
            collection_name=collection,
        )

        docs.extend(vectorstore.similarity_search(prompt, k=k, filter=filter))

    return docs
