from typing import List, Optional

from fastapi import HTTPException
from qdrant_client.http import models as rest

from app.utils.data import (
    search_multiple_collections,
    get_collection_metadata,
    get_collections_metadata,
)
from app.schemas.tools import ToolOutput


class BaseRAG:
    """
    Base RAG, basic retrival augmented generation.

    Args:
        embeddings_model (str): OpenAI embeddings model
        collection (Optional[List[str]], optional): List of collections to search in. Defaults to None (all collections).
        file_ids (Optional[List[str]], optional): List of file IDs in the selected collections (after upload files). Defaults to None (all files are selected).
        k (int, optional): Top K per collection. Defaults to 4.
        prompt_template (Optional[str], optional): Prompt template. Defaults to DEFAULT_PROMPT_TEMPLATE.

    DEFAULT_PROMPT_TEMPLATE:
        "Réponds à la question suivante en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n\n{documents}"
    """

    DEFAULT_PROMPT_TEMPLATE = "Réponds à la question suivante en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n\n{documents}"

    def __init__(self, clients: dict):
        self.clients = clients

    async def get_prompt(
        self,
        embeddings_model: str,
        collections: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
        k: Optional[int] = 4,
        prompt_template: Optional[str] = DEFAULT_PROMPT_TEMPLATE,
        **request,
    ) -> ToolOutput:
        if "{prompt}" not in prompt_template or "{documents}" not in prompt_template:
            raise HTTPException(
                status_code=400,
                detail="Prompt template must contain '{prompt}' and '{documents}' placeholders.",
            )

        if collections:
            collections = [get_collection_metadata(vectorstore=self.clients["vectors"], user=request["user"], collection=collection) for collection in collections]  # fmt: off
        else:
            collections = get_collections_metadata(
                vectorstore=self.clients["vectors"], user=request["user"]
            )

        for collection in collections:
            if collection.model != embeddings_model:
                raise HTTPException(
                    status_code=400,
                    detail=f"{collection.id} collection is set for {embeddings_model} model.",
                )

        filter = rest.Filter(must=[rest.FieldCondition(key="metadata.file_id", match=rest.MatchAny(any=file_ids))]) if file_ids else None  # fmt: off
        prompt = request["messages"][-1]["content"]

        documents = search_multiple_collections(
            vectorstore=self.clients["vectors"],
            embedding=self.clients["models"][embeddings_model].embedding,
            prompt=prompt,
            collections=[collections.id for collections in collections],
            user=request["user"],
            k=k,
            filter=filter,
        )

        metadata = {"chunks": [document.metadata for document in documents]}
        documents = "\n\n".join([document.page_content for document in documents])
        prompt = prompt_template.format(documents=documents, prompt=prompt)

        return ToolOutput(prompt=prompt, metadata=metadata)
