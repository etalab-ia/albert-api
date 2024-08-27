from typing import List, Optional

from fastapi import HTTPException
from qdrant_client.http.models import Filter, FieldCondition, MatchAny

from app.utils.data import get_chunks, get_collection
from app.schemas.tools import ToolOutput


class UseFiles:
    """
    Fill your prompt with file contents. Your prompt must contain "{files}" placeholder.

    Args:
        collection (str): Collection name.
        file_ids (List[str]): List of file ids in the selected collection.
    """

    DEFAULT_PROMPT_TEMPLATE = "Réponds à la question suivante en te basant sur les documents ci-dessous : %(prompt)s\n\nDocuments :\n\n%(docs)s"

    def __init__(self, clients: dict):
        self.clients = clients

    async def get_prompt(
        self,
        collection: str,
        file_ids: Optional[List[str]] = None,
        **request,
    ) -> ToolOutput:
        prompt = request["messages"][-1]["content"]
        if "{files}" not in prompt:
            raise HTTPException(
                status_code=400, detail='User message must contain "{files}" with UseFiles tool.'
            )

        collection = get_collection(vectorstore=self.clients["vectors"], collection=collection, user=request["user"])
        filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=file_ids))])
        chunks = get_chunks(
            vectorstore=self.clients["vectors"], collection=collection.id, filter=filter
        )
        
        metadata = {"chunks": chunk.metadata for chunk in chunks}
        files = "\n\n".join([chunk.content for chunk in chunks])
        prompt = prompt.replace("{files}", files)

        return ToolOutput(prompt=prompt, metadata=metadata)
