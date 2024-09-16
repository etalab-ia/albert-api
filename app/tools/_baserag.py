from app.helpers import VectorStore
from app.schemas.tools import ToolOutput
from app.helpers import UseInternet
from fastapi import HTTPException
from qdrant_client.http.models import FieldCondition, Filter, MatchAny
from typing import List, Optional


class BaseRAG:
    """
    Base RAG, basic retrival augmented generation.

    Args:
        embeddings_model (str): OpenAI embeddings model
        collection (List[str], optional): List of collections to search in. Defaults to None (all collections).
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
        collections: List[str] = [],
        file_ids: Optional[List[str]] = None,
        k: Optional[int] = 4,
        prompt_template: Optional[str] = DEFAULT_PROMPT_TEMPLATE,
        **request,
    ) -> ToolOutput:
        if "{prompt}" not in prompt_template or "{documents}" not in prompt_template:
            raise HTTPException(status_code=400, detail="Prompt template must contain '{prompt}' and '{documents}' placeholders.")

        vectorstore = VectorStore(clients=self.clients, user=request["user"])
        prompt = request["messages"][-1]["content"]

        # file ids filter
        filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=file_ids))]) if file_ids else None

        use_internet = False

        if collections and "internet" in collections:
            use_internet = True
            collections.remove("internet")

        documents = vectorstore.search(model=embeddings_model, prompt=prompt, collection_names=collections, k=k, filter=filter)

        if use_internet:
            search = UseInternet()
            documents.extend(search.search_internet(prompt, n=k))

        metadata = {"chunks": [document.metadata for document in documents]}
        documents = "\n\n".join([document.page_content for document in documents])
        prompt = prompt_template.format(documents=documents, prompt=prompt)

        return ToolOutput(prompt=prompt, metadata=metadata)
