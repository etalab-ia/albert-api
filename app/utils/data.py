from uuid import UUID
from typing import List, Dict

from qdrant_client.http import models as rest


def file_to_chunk(client, collection: str, file_ids=List[str]) -> List[Dict]:
    """
    Get chunk from file IDs.

    Args:
        client: vectors database client
        collection (str): name of vector collection.
        file_ids (List[UUID]): list of file ID.

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
