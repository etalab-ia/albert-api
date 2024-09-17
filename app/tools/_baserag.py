from typing import List, Optional

from fastapi import HTTPException

from app.helpers import VectorStore
from app.schemas.tools import ToolOutput


class BaseRAG:
    """
    Base RAG, basic retrival augmented generation.

    Args:
        embeddings_model (str): OpenAI embeddings model
        collection (List[str], optional): List of collections to search in. Defaults to None (all collections).
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
        k: Optional[int] = 4,
        prompt_template: Optional[str] = DEFAULT_PROMPT_TEMPLATE,
        **request,
    ) -> ToolOutput:
        if "{prompt}" not in prompt_template or "{documents}" not in prompt_template:
            raise HTTPException(status_code=400, detail="Prompt template must contain '{prompt}' and '{documents}' placeholders.")

        vectorstore = VectorStore(clients=self.clients, user=request["user"])
        prompt = request["messages"][-1]["content"]

        documents = vectorstore.search(model=embeddings_model, prompt=prompt, collection_names=collections, k=k)

        metadata = {"chunks": [document.metadata for document in documents]}
        documents = "\n\n".join([document.page_content for document in documents])
        prompt = prompt_template.format(documents=documents, prompt=prompt)

        return ToolOutput(prompt=prompt, metadata=metadata)
